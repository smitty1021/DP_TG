import os
import uuid
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app, session, abort)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image

from app.extensions import db
from app.models import User, Activity, Settings
from app.forms import (LoginForm, RegistrationForm, RequestPasswordResetForm,
                       ResetPasswordForm, ResendVerificationForm,
                       ProfileForm, ChangePasswordForm)

from app.utils import (generate_token, verify_token, send_email, record_activity, allowed_file)

import asyncio
import secrets
import aiohttp
from urllib.parse import urlencode
from datetime import datetime, timedelta
from app.models import User, DiscordRolePermission, UserSession
from app.services.discord_service import discord_service

auth_bp = Blueprint('auth', __name__,
                    template_folder='../templates/auth',
                    url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.find_by_username(form.username.data)
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account is inactive. Please contact support.', 'warning')
                return redirect(url_for('auth.login'))
            if not user.is_email_verified:
                # FIXED: Use custom notification instead of flash message with HTML
                # This will trigger the custom verification notification with resend button
                session['show_verification_required'] = True
                session['verification_email'] = user.email
                return redirect(url_for('auth.login'))

            # ENHANCED: Check Discord role validity if user has Discord linked
            if user.discord_linked and user.discord_id:
                # Sync Discord roles
                try:
                    current_roles = discord_service.get_user_roles_sync(user.discord_id)
                    user.sync_discord_roles(current_roles)

                    # Check if user still has valid roles (unless admin)
                    if not user.is_admin() and not has_valid_discord_roles(current_roles):
                        flash('Access denied: Your Discord roles no longer permit access to this application.',
                              'danger')
                        return redirect(url_for('auth.login'))
                except Exception as e:
                    current_app.logger.error(f"Discord role sync error for user {user.username}: {e}")
                    # Continue with login - don't block due to Discord API issues

            login_user(user, remember=form.remember.data)
            user.last_login = datetime.utcnow()
            record_activity('login', user_id_for_activity=user.id)
            db.session.commit()

            # ENHANCED: Create user session record
            try:
                session_id = str(uuid.uuid4())
                session['user_session_id'] = session_id

                user_session = UserSession(
                    user_id=user.id,
                    session_id=session_id,
                    ip_address=request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
                    user_agent=request.user_agent.string[:500],
                    login_time=datetime.utcnow()
                )
                db.session.add(user_session)
                db.session.commit()
            except Exception as e:
                current_app.logger.error(f"Session creation error for user {user.username}: {e}")
                # Don't block login for session creation failure

            flash('Authentication successful. Welcome to Pack Trade Group!', 'success')
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('main.index')
            return redirect(next_page)
        else:
            flash('Invalid credentials. Please verify your username and password.', 'danger')
    return render_template('login.html', title='Authentication Portal', form=form)

# Add this route to your auth_bp.py file to clear the session flag

@auth_bp.route('/clear_verification_flag', methods=['POST'])
def clear_verification_flag():
    """Clear the verification required session flag"""
    session.pop('show_verification_required', None)
    session.pop('verification_email', None)
    return '', 204

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        if User.find_by_username(form.username.data):
            flash('Username already taken.', 'danger')
        elif User.find_by_email(form.email.data):
            flash('Email already registered.', 'danger')
        else:
            try:
                new_user = User(username=form.username.data, email=form.email.data.lower(), is_active=True)
                new_user.set_password(form.password.data)
                db.session.add(new_user)
                db.session.commit()

                try:
                    copied_tags = Tag.copy_defaults_to_user(new_user.id)
                    current_app.logger.info(f"Copied {copied_tags} default tags to new user {new_user.username}")
                except Exception as e:
                    current_app.logger.error(f"Failed to copy default tags to user {new_user.username}: {e}")
                    # Don't fail registration if tag copying fails


                token = generate_token(new_user.email, salt='email-verification-salt')
                verification_url = url_for('auth.verify_email', token=token, _external=True)
                send_email(to=new_user.email, subject="Verify Your Email - Trading Journal",
                           template_name="verify_email.html", username=new_user.username,
                           verification_url=verification_url)
                flash(f'Account created! Please check {new_user.email} to verify your account.', 'success')
                record_activity('register', f"New account: {new_user.username}", user_id_for_activity=new_user.id)
                return redirect(url_for('auth.login'))
            except Exception as e:
                db.session.rollback()
                flash('Registration error. Please try again.', 'danger')
                current_app.logger.error(f"Registration error for {form.username.data}: {e}", exc_info=True)
    return render_template('register.html', title='Register', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    user_id_before_logout = current_user.id
    user_name_before_logout = current_user.username
    logout_user()
    record_activity('logout', f"User {user_name_before_logout} logged out.", user_id_for_activity=user_id_before_logout)
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/verify_email/<token>')
def verify_email(token):
    # ... (verify_email logic as before) ...
    if current_user.is_authenticated and current_user.is_email_verified:
        flash('Email already verified.', 'info')
        return redirect(url_for('main.index'))
    email = verify_token(token, salt='email-verification-salt', max_age_seconds=86400)
    if email:
        user = User.find_by_email(email)
        if user:
            if user.is_email_verified:
                flash('Email already verified.', 'info')
            else:
                user.is_email_verified = True
                user.is_active = True
                db.session.commit()
                record_activity('email_verified', user_id_for_activity=user.id)
                flash('Email verified! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid verification link (user not found).', 'danger')
    else:
        flash('Verification link invalid or expired.', 'danger')
    return redirect(url_for('auth.login'))


@auth_bp.route('/resend_verification', methods=['GET', 'POST'])
def resend_verification_request():
    # ... (resend_verification_request logic as before) ...
    if current_user.is_authenticated and current_user.is_email_verified:
        flash('Email already verified.', 'info')
        return redirect(url_for('main.index'))
    form = ResendVerificationForm()
    if form.validate_on_submit():
        user = User.find_by_email(form.email.data)
        if user:
            if user.is_email_verified:
                flash('Email already verified.', 'info')
            else:
                token = generate_token(user.email, salt='email-verification-salt')
                verification_url = url_for('auth.verify_email', token=token, _external=True)
                send_email(to=user.email, subject="Verify Email (Resend) - Trading Journal",
                           template_name="verify_email.html", username=user.username, verification_url=verification_url)
                flash('New verification email sent.', 'success')
        else:
            flash('If account exists, verification email sent.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('resend_verification_request.html', title='Resend Verification', form=form)


@auth_bp.route('/request_password_reset', methods=['GET', 'POST'])
def request_password_reset():
    # ... (request_password_reset logic as before) ...
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    form = RequestPasswordResetForm()
    if form.validate_on_submit():
        user = User.find_by_email(form.email.data)
        if user:
            token = generate_token(user.id, salt='password-reset-salt')
            reset_url = url_for('auth.reset_password_with_token', token=token, _external=True)
            send_email(to=user.email, subject="Pack Trade Group - Trading Journal Password Reset Request",
                       template_name="reset_password_email.html", username=user.username, reset_url=reset_url)
            flash('Password reset email sent.', 'info')
        else:
            flash('If account exists, password reset email sent.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('request_password_reset.html', title='Reset Password Request', form=form)


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password_with_token(token):
    # ... (reset_password_with_token logic as before) ...
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    user_id = verify_token(token, salt='password-reset-salt', max_age_seconds=1800)
    if not user_id:
        flash('Password reset link invalid or expired.', 'danger')
        return redirect(url_for('auth.request_password_reset'))
    user = User.query.get(user_id)
    if not user:
        flash('Invalid user for password reset.', 'danger')
        return redirect(url_for('auth.request_password_reset'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        try:
            user.set_password(form.password.data)
            if not user.is_email_verified: user.is_email_verified = True
            if not user.is_active: user.is_active = True
            db.session.commit()
            record_activity('password_reset_completed', user_id_for_activity=user.id)
            flash('Password reset. You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('Error resetting password.', 'danger')
            current_app.logger.error(f"Error resetting password for {user.username}: {e}", exc_info=True)
    return render_template('reset_password_with_token.html', title='Reset Password', form=form, token=token)


@auth_bp.route('/discord/login')
def discord_login():
    """Initiate Discord OAuth2 login."""
    # Check if this is a linking operation for an authenticated user
    linking_mode = session.get('discord_linking_mode', False)

    if current_user.is_authenticated and not linking_mode:
        return redirect(url_for('main.index'))

    # Generate state parameter for CSRF protection
    state = secrets.token_urlsafe(32)
    session['discord_oauth_state'] = state

    # Discord OAuth2 authorization URL
    discord_oauth_url = "https://discord.com/api/oauth2/authorize"

    params = {
        'client_id': current_app.config.get('DISCORD_CLIENT_ID', os.getenv('DISCORD_CLIENT_ID')),
        'redirect_uri': url_for('auth.discord_callback', _external=True),
        'response_type': 'code',
        'scope': 'identify guilds.members.read',
        'state': state
    }

    authorization_url = f"{discord_oauth_url}?{urlencode(params)}"
    return redirect(authorization_url)


@auth_bp.route('/discord/sync-roles', methods=['POST'])
@login_required
def sync_discord_roles():
    """Manually sync Discord roles for the current user."""
    if not current_user.discord_linked:
        return {'success': False, 'message': 'Discord account not linked'}, 400

    if not current_user.discord_id:
        return {'success': False, 'message': 'Discord ID not found'}, 400

    try:
        # Get fresh Discord roles
        current_roles = discord_service.get_user_roles_sync(current_user.discord_id)

        if current_roles is None:
            return {'success': False, 'message': 'Discord service unavailable'}, 503

        # Update user's roles
        current_user.sync_discord_roles(current_roles)

        # Log the activity
        record_activity('discord_role_sync', f'Discord roles manually synced. Found {len(current_roles)} roles.')

        return {
            'success': True,
            'message': f'Successfully synced {len(current_roles)} Discord roles',
            'role_count': len(current_roles),
            'sync_time': current_user.last_discord_sync.isoformat() if current_user.last_discord_sync else None
        }

    except Exception as e:
        current_app.logger.error(f"Error syncing Discord roles for {current_user.username}: {e}", exc_info=True)
        return {'success': False, 'message': 'Internal server error during sync'}, 500

@auth_bp.route('/discord/callback')
def discord_callback():
    """Handle Discord OAuth2 callback."""
    try:
        # Verify state parameter
        state = request.args.get('state')
        if not state or state != session.pop('discord_oauth_state', None):
            flash('Invalid authentication request. Please try again.', 'danger')
            return redirect(url_for('auth.login'))

        # Check for authorization code
        code = request.args.get('code')
        if not code:
            error = request.args.get('error', 'Unknown error')
            flash(f'Discord authorization failed: {error}', 'danger')
            return redirect(url_for('auth.login'))

        # Exchange code for access token
        token_data = asyncio.run(discord_service.exchange_code_for_token(
            code,
            url_for('auth.discord_callback', _external=True)
        ))

        if not token_data:
            flash('Failed to authenticate with Discord. Please try again.', 'danger')
            return redirect(url_for('auth.login'))

        # Get user information from Discord
        user_info = asyncio.run(discord_service.get_user_info(token_data['access_token']))

        if not user_info:
            flash('Failed to retrieve user information from Discord.', 'danger')
            return redirect(url_for('auth.login'))

        # Check if this is a linking operation
        linking_mode = session.pop('discord_linking_mode', False)
        linking_user_id = session.pop('linking_user_id', None)

        if linking_mode and linking_user_id and current_user.is_authenticated:
            # This is a linking operation for an existing user
            try:
                discord_id = user_info['id']
                discord_username = user_info['username']
                discord_discriminator = user_info.get('discriminator', '0')
                discord_avatar = user_info.get('avatar')

                # Check if Discord account is already linked to another user
                existing_discord_user = User.query.filter_by(discord_id=discord_id).first()
                if existing_discord_user:
                    flash('This Discord account is already linked to another user.', 'danger')
                    return redirect(url_for('auth.user_profile'))

                # Get Discord roles
                discord_roles = discord_service.get_user_roles_sync(discord_id)

                # Link Discord to current user
                current_user.discord_id = discord_id
                current_user.discord_username = discord_username
                current_user.discord_discriminator = discord_discriminator
                current_user.discord_avatar = discord_avatar
                current_user.discord_linked = True
                current_user.sync_discord_roles(discord_roles)

                db.session.commit()
                record_activity('discord_link', f'Discord account linked: {discord_username}')
                flash('Discord account successfully linked!', 'success')
                return redirect(url_for('auth.user_profile'))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error linking Discord for {current_user.username}: {e}", exc_info=True)
                flash('Failed to link Discord account. Please try again.', 'danger')
                return redirect(url_for('auth.user_profile'))

        else:
            # This is a regular Discord login for new users or existing Discord users
            # Process Discord authentication
            discord_user = process_discord_authentication(user_info)

            if not discord_user:
                flash('Authentication failed. You may not have the required Discord roles.', 'danger')
                return redirect(url_for('auth.login'))

            # Log the user in
            login_user(discord_user, remember=True)
            discord_user.last_login = datetime.utcnow()

            # Set theme from user settings
            if discord_user.settings and discord_user.settings.theme:
                session['theme'] = discord_user.settings.theme
            else:
                session['theme'] = 'dark'

            try:
                db.session.commit()
                record_activity('discord_login', f'Discord login: {discord_user.discord_username}')
                flash('Successfully logged in with Discord!', 'success')

                # Redirect based on user permissions
                permissions = discord_user.get_discord_permissions()
                next_page = request.args.get('next')

                if next_page:
                    return redirect(next_page)
                elif permissions.get('can_access_portfolio'):
                    return redirect(url_for('main.portfolio_analytics'))
                else:
                    return redirect(url_for('main.index'))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error during Discord login for {discord_user.username}: {e}", exc_info=True)
                flash("An error occurred during login. Please try again.", "danger")
                return redirect(url_for('auth.login'))

    except Exception as e:
        current_app.logger.error(f"Discord callback error: {e}", exc_info=True)
        flash('Authentication failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

def process_discord_authentication(discord_user_info):
    """Process Discord user authentication and role checking."""
    try:
        discord_id = discord_user_info['id']
        discord_username = discord_user_info['username']
        discord_discriminator = discord_user_info.get('discriminator', '0')
        discord_avatar = discord_user_info.get('avatar')

        # Get user's Discord roles
        discord_roles = discord_service.get_user_roles_sync(discord_id)

        # Check if user has valid roles (unless they're an admin)
        existing_user = User.query.filter_by(discord_id=discord_id).first()
        if existing_user and existing_user.is_admin():
            # Admin can always log in
            pass
        elif not has_valid_discord_roles(discord_roles):
            current_app.logger.warning(f"User {discord_username} attempted login without valid Discord roles")
            return None

        # Check if user exists by Discord ID
        user = User.query.filter_by(discord_id=discord_id).first()

        if user:
            # Update existing user's Discord info
            user.discord_username = discord_username
            user.discord_discriminator = discord_discriminator
            user.discord_avatar = discord_avatar
            user.sync_discord_roles(discord_roles)

            # Ensure user is active
            if not user.is_active:
                current_app.logger.warning(f"Inactive user attempted Discord login: {user.username}")
                return None

            return user

        else:
            # Check if there's an existing user by email that can be linked
            discord_email = discord_user_info.get('email')
            if discord_email:
                existing_email_user = User.query.filter_by(email=discord_email.lower()).first()
                if existing_email_user:
                    # Link Discord to existing email account
                    existing_email_user.discord_id = discord_id
                    existing_email_user.discord_username = discord_username
                    existing_email_user.discord_discriminator = discord_discriminator
                    existing_email_user.discord_avatar = discord_avatar
                    existing_email_user.discord_linked = True
                    existing_email_user.sync_discord_roles(discord_roles)
                    existing_email_user.is_active = True
                    existing_email_user.is_email_verified = True

                    current_app.logger.info(f"Linked Discord account to existing user: {existing_email_user.username}")
                    return existing_email_user

            # Create new Discord-only user
            new_user = User(
                username=f"discord_{discord_username}_{discord_id[-4:]}",  # Ensure unique username
                email=discord_email.lower() if discord_email else f"{discord_id}@discord.local",
                discord_id=discord_id,
                discord_username=discord_username,
                discord_discriminator=discord_discriminator,
                discord_avatar=discord_avatar,
                discord_linked=True,
                name=discord_user_info.get('global_name') or discord_username,
                is_active=True,
                is_email_verified=True  # Discord accounts are considered verified
            )

            # Set a random password (won't be used for Discord users)
            new_user.set_password(secrets.token_urlsafe(32))
            new_user.sync_discord_roles(discord_roles)

            db.session.add(new_user)
            db.session.flush()  # Get the user ID

            # Copy default tags for new user
            try:
                from app.models import Tag
                copied_tags = Tag.copy_defaults_to_user(new_user.id)
                current_app.logger.info(f"Copied {copied_tags} default tags to new Discord user {new_user.username}")
            except Exception as e:
                current_app.logger.error(f"Failed to copy default tags to Discord user {new_user.username}: {e}")

            current_app.logger.info(f"Created new Discord user: {new_user.username}")
            return new_user

    except Exception as e:
        current_app.logger.error(f"Error processing Discord authentication: {e}", exc_info=True)
        return None


def has_valid_discord_roles(discord_roles):
    """Check if user has any valid Discord roles for access."""
    if not discord_roles:
        return False

    # Get all configured Discord role IDs
    configured_roles = db.session.query(DiscordRolePermission.discord_role_id).all()
    configured_role_ids = {role[0] for role in configured_roles}

    # Check if user has any configured role
    user_role_ids = {role['id'] for role in discord_roles}

    return bool(configured_role_ids.intersection(user_role_ids))


@auth_bp.route('/discord/link', methods=['GET', 'POST'])
@login_required
def link_discord():
    """Allow existing users to link their Discord account."""
    if current_user.discord_linked:
        flash('Your account is already linked to Discord.', 'info')
        return redirect(url_for('auth.user_profile'))

    if request.method == 'POST':
        # Set session flag to indicate this is a linking operation
        session['discord_linking_mode'] = True
        session['linking_user_id'] = current_user.id
        # Start Discord linking process
        return redirect(url_for('auth.discord_login'))

    return render_template('auth/link_discord.html', title='Link Discord Account')


@auth_bp.route('/discord/unlink', methods=['POST'])
@login_required
def unlink_discord():
    """Allow users to unlink their Discord account."""
    if not current_user.discord_linked:
        flash('Your account is not linked to Discord.', 'info')
        return redirect(url_for('auth.user_profile'))

    # Don't allow unlinking if this is a Discord-only account
    if not current_user.email or current_user.email.endswith('@discord.local'):
        flash('Cannot unlink Discord from a Discord-only account.', 'danger')
        return redirect(url_for('auth.user_profile'))

    try:
        current_user.discord_id = None
        current_user.discord_username = None
        current_user.discord_discriminator = None
        current_user.discord_avatar = None
        current_user.discord_linked = False
        current_user.discord_roles = None
        current_user.last_discord_sync = None

        db.session.commit()
        record_activity('discord_unlink', 'Discord account unlinked')
        flash('Discord account successfully unlinked.', 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error unlinking Discord for {current_user.username}: {e}", exc_info=True)
        flash('Failed to unlink Discord account. Please try again.', 'danger')

    return redirect(url_for('auth.user_profile'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    profile_form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()

    if 'submit_profile' in request.form and profile_form.validate_on_submit():
        original_email = current_user.email
        form_email = profile_form.email.data.lower()
        email_changed = (form_email != original_email.lower())

        if email_changed:
            existing_user_with_email = User.find_by_email(form_email)
            if existing_user_with_email and existing_user_with_email.id != current_user.id:
                flash('That email address is already in use by another account.', 'danger')
            else:  # Email is new and available or is the same but case changed
                current_user.is_email_verified = False  # Require re-verification for new email
                token = generate_token(form_email, salt='email-verification-salt')
                verification_url = url_for('auth.verify_email', token=token, _external=True)
                send_email(
                    to=form_email, subject="Verify Your New Email Address - Trading Journal",
                    template_name="verify_email.html", username=current_user.username, verification_url=verification_url
                )
                flash('Your email has been updated. Please check your new email address for a verification link.',
                      'info')

        current_user.name = profile_form.name.data
        current_user.email = form_email
        if hasattr(current_user, 'bio'):
            current_user.bio = profile_form.bio.data

        try:
            db.session.commit()
            record_activity('profile_update', 'User profile information updated.')
            flash('Your profile has been updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update profile. Error: {str(e)}', 'danger')
        return redirect(url_for('auth.user_profile'))

    if 'submit_password' in request.form and password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash('Current password is incorrect.', 'danger')
        else:
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            record_activity('password_change', 'User changed their password.')
            flash('Your password has been updated successfully.', 'success')
        return redirect(url_for('auth.user_profile'))

    return render_template('profile.html', title='Your Profile', profile_form=profile_form, password_form=password_form)