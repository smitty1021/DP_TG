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
# Import allowed_file from utils
from app.utils import (generate_token, verify_token, send_email, record_activity, allowed_file)

auth_bp = Blueprint('auth', __name__,
                    template_folder='../templates/auth',
                    url_prefix='/auth')


# ... (login, register, logout, verify_email, resend_verification_request,
#      request_password_reset, reset_password_with_token routes remain the same as before) ...

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
                flash_message = (
                    'Please verify your email address before logging in. '
                    'Check your inbox for a verification link, or '
                    '<a href="{}" class="alert-link">request a new one</a>.'
                ).format(url_for('auth.resend_verification_request'))
                flash(flash_message, 'warning')
                return redirect(url_for('auth.login'))

            login_user(user, remember=form.remember.data)
            user.last_login = db.func.now()
            if user.settings and user.settings.theme:
                session['theme'] = user.settings.theme
            else:
                session['theme'] = 'dark'
            try:
                db.session.commit()
                record_activity('login')
                next_page = request.args.get('next')
                flash('Logged in successfully!', 'success')
                return redirect(next_page or url_for('main.index'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error during login for {user.username}: {e}", exc_info=True)
                flash("An error occurred during login. Please try again.", "danger")
        else:
            flash('Login failed. Check username/password.', 'danger')
    return render_template('login.html', title='Login', form=form)


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
            send_email(to=user.email, subject="Password Reset Request - Trading Journal",
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

        if profile_form.profile_picture.data:
            picture_file = profile_form.profile_picture.data
            # Use the specific allowed extensions for images from app config
            if picture_file and allowed_file(picture_file.filename, current_app.config['ALLOWED_IMAGE_EXTENSIONS']):
                original_filename = secure_filename(picture_file.filename)
                file_ext = os.path.splitext(original_filename)[1].lower()

                if current_user.profile_picture and current_user.profile_picture != 'default.jpg':
                    old_picture_path = os.path.join(current_app.config['PROFILE_PICS_SAVE_PATH'],
                                                    current_user.profile_picture)
                    if os.path.exists(old_picture_path):
                        try:
                            os.remove(old_picture_path)
                        except Exception as e_del:
                            current_app.logger.error(f"Error deleting old profile pic: {e_del}")

                picture_fn = uuid.uuid4().hex + file_ext
                picture_save_path = os.path.join(current_app.config['PROFILE_PICS_SAVE_PATH'], picture_fn)

                try:
                    i = Image.open(picture_file)
                    i.thumbnail((150, 150))  # Resize to 150x150
                    i.save(picture_save_path)
                    current_user.profile_picture = picture_fn
                except Exception as e_save:
                    flash('Error saving profile picture.', 'danger')
                    current_app.logger.error(f"Profile pic save error: {e_save}", exc_info=True)
            elif picture_file:  # File was provided but type not allowed
                allowed_types_str = ', '.join(current_app.config['ALLOWED_IMAGE_EXTENSIONS'])
                flash(
                    f"Invalid image file type: '{picture_file.filename.rsplit('.', 1)[1].lower()}'. Allowed: {allowed_types_str}.",
                    'warning')
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