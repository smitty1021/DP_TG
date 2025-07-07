from flask import (Blueprint, render_template, current_app, request,
                   redirect, url_for, flash, abort, jsonify)  # Added abort
from flask_login import login_required, current_user

from app.extensions import db
from app.utils import admin_required, record_activity, generate_token, send_email, smart_flash  # Added generate_token, send_email
from app.models import User, UserRole, Activity, Instrument, Tag, TagCategory  # Add TagCategory here
from datetime import datetime

from app.forms import AdminCreateUserForm, AdminEditUserForm, InstrumentForm, InstrumentFilterForm  # Add Instrument forms
from app.models import Tag, TagCategory  # Add to existing imports
from app.forms import AdminDefaultTagForm
from app.models import Instrument  # Add to existing imports
from app.forms import InstrumentForm, InstrumentFilterForm  # Add to existing imports
from app.models import TradingModel
from app.forms import TradingModelForm
admin_bp = Blueprint('admin', __name__,
                     template_folder='../templates/admin',
                     url_prefix='/admin')

# Add these imports at the top if not already present

from app.forms import TradingModelForm
from app.models import User, UserRole, Activity, Instrument, Tag, TagCategory, TradingModel


@admin_bp.route('/default-trading-models')
@login_required
@admin_required
def manage_default_trading_models():
    """Admin page to manage default trading models"""
    models = TradingModel.query.filter_by(is_default=True).order_by(TradingModel.name).all()
    return render_template('admin/default_trading_models.html',
                           title='Manage Default Trading Models',
                           models=models)


@admin_bp.route('/default-trading-models/<int:model_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_default_trading_model(model_id):
    """Edit a default trading model"""
    model = TradingModel.query.get_or_404(model_id)
    if not model.is_default:
        flash('This is not a default model.', 'warning')
        return redirect(url_for('admin.manage_default_trading_models'))

    form = TradingModelForm(obj=model)

    if form.validate_on_submit():
        form.populate_obj(model)
        model.created_by_admin_user_id = current_user.id
        try:
            db.session.commit()
            flash(f'Default model "{model.name}" updated successfully!', 'success')
            return redirect(url_for('admin.manage_default_trading_models'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating model: {str(e)}', 'danger')

    return render_template('admin/edit_default_trading_model.html',
                           title=f'Edit Default Model: {model.name}',
                           form=form, model=model)


@admin_bp.route('/default-trading-models/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_default_trading_model():
    """Create a new default trading model"""
    form = TradingModelForm()

    if form.validate_on_submit():
        model = TradingModel()
        form.populate_obj(model)
        model.is_default = True
        model.user_id = current_user.id  # Still needs a user_id for FK constraint
        model.created_by_admin_user_id = current_user.id
        try:
            db.session.add(model)
            db.session.commit()
            flash(f'Default model "{model.name}" created successfully!', 'success')
            return redirect(url_for('admin.manage_default_trading_models'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating model: {str(e)}', 'danger')

    return render_template('admin/create_default_trading_model.html',
                           title='Create Default Trading Model',
                           form=form)

@admin_bp.route('/default-tags/create', methods=['POST'])
@login_required
@admin_required
def create_default_tag():
    """Create a new default tag from a standard form submission."""
    try:
        # --- MODIFICATION START ---
        # Read from the submitted form data instead of JSON
        name = request.form.get('name', '').strip()
        category_name = request.form.get('category', '')
        color_category = request.form.get('color_category', 'neutral')
        # Convert the form's string 'true'/'false' to a Python boolean
        is_active = request.form.get('is_active') == 'true'
        # --- MODIFICATION END ---

        if not name or not category_name:
            flash('Name and category are required.', 'danger')
            return redirect(url_for('admin.manage_default_tags'))

        # Validate category
        try:
            category = TagCategory[category_name]
        except KeyError:
            flash('Invalid category specified.', 'danger')
            return redirect(url_for('admin.manage_default_tags'))

        # Check for duplicates
        existing = Tag.query.filter_by(name=name, is_default=True).first()
        if existing:
            flash(f"A default tag named '{name}' already exists.", 'warning')
            return redirect(url_for('admin.manage_default_tags'))

        # Create new default tag
        new_tag = Tag(
            name=name,
            category=category,
            color_category=color_category,
            is_default=True,
            is_active=is_active
        )

        db.session.add(new_tag)
        db.session.commit()

        # Flash a success message and redirect back to the tags page
        flash(f"Tag '{new_tag.name}' was created successfully.", 'success')
        return redirect(url_for('admin.manage_default_tags'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating default tag: {e}", exc_info=True)
        flash(f'An unexpected error occurred while creating the tag.', 'danger')
        return redirect(url_for('admin.manage_default_tags'))


@admin_bp.route('/default-tags/<int:tag_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_default_tag(tag_id):
    """Edit a default tag via AJAX"""
    try:
        tag = Tag.query.get_or_404(tag_id)

        if not tag.is_default:
            return jsonify({'success': False, 'message': 'Can only edit default tags'})

        data = request.get_json()
        name = data.get('name', '').strip()
        category_name = data.get('category', '')
        is_active = data.get('is_active', True)
        color_category = data.get('color_category', 'neutral')  # Get color category

        if not name or not category_name:
            return jsonify({'success': False, 'message': 'Name and category are required'})

        # Validate category
        try:
            category = TagCategory[category_name]
        except KeyError:
            return jsonify({'success': False, 'message': 'Invalid category'})

        # Check for duplicates (excluding current tag)
        existing = Tag.query.filter_by(name=name, is_default=True).filter(Tag.id != tag_id).first()
        if existing:
            return jsonify({'success': False, 'message': 'Another default tag with this name already exists'})

        # Update tag
        tag.name = name
        tag.category = category
        tag.is_active = is_active
        tag.color_category = color_category  # Update color category

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Tag updated successfully',
            'tag': {
                'id': tag.id,
                'name': tag.name,
                'category': tag.category.name,
                'is_active': tag.is_active,
                'color_category': tag.color_category  # Return color category
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating tag: {str(e)}'})


@admin_bp.route('/default-tags/<int:tag_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_default_tag(tag_id):
    """Delete a default tag via AJAX"""
    try:
        tag = Tag.query.get_or_404(tag_id)

        if not tag.is_default:
            return jsonify({'success': False, 'message': 'Can only delete default tags'})

        tag_name = tag.name

        # Note: This will also remove the tag from any user's collection who had it
        db.session.delete(tag)
        db.session.commit()

        current_app.logger.info(f"Admin {current_user.username} deleted default tag: {tag_name}")

        return jsonify({
            'success': True,
            'message': f'Default tag "{tag_name}" deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting default tag {tag_id}: {e}")
        return jsonify({'success': False, 'message': 'Error deleting default tag'})


@admin_bp.route('/default-tags/bulk-actions', methods=['POST'])
@login_required
@admin_required
def bulk_default_tags_actions():
    """Handle bulk actions on default tags from a standard form submission."""
    # Read from the submitted form data instead of JSON
    action = request.form.get('action')
    # Use getlist to receive multiple inputs with the same name ('tag_ids')
    tag_ids = request.form.getlist('tag_ids')

    if not tag_ids:
        flash('No tags were selected for the bulk action.', 'warning')
        return redirect(url_for('admin.manage_default_tags'))

    if action == 'delete_selected':
        deleted_count = 0
        for tag_id in tag_ids:
            tag = Tag.query.get(tag_id)
            if tag and tag.is_default:
                db.session.delete(tag)
                deleted_count += 1
        db.session.commit()
        flash(f'Successfully deleted {deleted_count} tags.', 'success')

    elif action == 'toggle_status':
        updated_count = 0
        for tag_id in tag_ids:
            tag = Tag.query.get(tag_id)
            if tag and tag.is_default:
                tag.is_active = not tag.is_active
                updated_count += 1
        db.session.commit()
        flash(f'Successfully updated the status for {updated_count} tags.', 'success')

    else:
        flash('An invalid bulk action was specified.', 'danger')

    # Redirect back to the tags page, where the flashed message will be displayed
    return redirect(url_for('admin.manage_default_tags'))


@admin_bp.route('/default-tags/seed', methods=['POST'])
@login_required
@admin_required
def seed_default_tags():
    """Seed Random's trading methodology default tags"""
    try:
        # Clear existing default tags
        Tag.query.filter_by(is_default=True).delete()

        # Create Random's tag system
        created_count = Tag.create_default_tags()

        db.session.commit()
        flash(f'Successfully created {created_count} Random trading system tags!', 'success')
        current_app.logger.info(f"Admin {current_user.username} seeded Random's default tags")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error seeding default tags: {e}")
        flash('Error creating default tags. Please try again.', 'danger')

    return redirect(url_for('admin.manage_default_tags'))


@admin_bp.route('/dashboard')
@login_required
@admin_required
def show_admin_dashboard():
    total_users = "N/A"
    try:
        total_users = User.query.count()
        current_app.logger.info(f"Admin {current_user.username} accessed admin dashboard.")
    except Exception as e:
        current_app.logger.error(f"Error fetching admin dashboard stats: {e}", exc_info=True)
        flash("Could not load all dashboard statistics.", "warning")
    return render_template('dashboard.html', title='Admin Dashboard', total_users=total_users)


@admin_bp.route('/users')
@login_required
@admin_required
def admin_users_list():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 10)
    users_on_page, users_pagination, total_users_count, active_users_count, admin_users_count = [], None, 0, 0, 0
    try:
        users_pagination = User.query.order_by(User.username.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        users_on_page = users_pagination.items
        total_users_count = users_pagination.total
        active_users_count = User.query.filter_by(is_active=True).count()
        admin_users_count = User.query.filter_by(role=UserRole.ADMIN).count()
        current_app.logger.info(f"Admin {current_user.username} accessed user list page {page}.")
    except Exception as e:
        current_app.logger.error(f"Error fetching user list for admin: {e}", exc_info=True)
        flash("Could not load user list.", "danger")
        total_users_count = active_users_count = admin_users_count = "Error"
    return render_template('users.html', title='User Management',
                           users=users_on_page, pagination=users_pagination,
                           total_users_count=total_users_count,
                           active_users_count=active_users_count,
                           admin_users_count=admin_users_count,
                           UserRole=UserRole)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_user():
    form = AdminCreateUserForm()
    if form.validate_on_submit():
        if User.find_by_username(form.username.data):
            flash('Username already exists.', 'danger')
        elif User.find_by_email(form.email.data):
            flash('Email address is already registered.', 'danger')
        else:
            try:
                new_user = User(
                    username=form.username.data,
                    email=form.email.data.lower(),
                    name=form.name.data if form.name.data else None,
                    role=UserRole(form.role.data),
                    is_active=form.is_active.data,
                    is_email_verified=form.is_email_verified.data
                )
                new_user.set_password(form.password.data)
                db.session.add(new_user)
                db.session.commit()
                flash_message = f'User "{new_user.username}" created successfully'
                flash_category = 'success'
                if not new_user.is_email_verified:
                    token = generate_token(new_user.email, salt='email-verification-salt')
                    verification_url = url_for('auth.verify_email', token=token, _external=True)
                    email_sent = send_email(
                        to=new_user.email,
                        subject="Your Account Was Created - Verify Your Email",
                        template_name="verify_email.html",
                        username=new_user.username,
                        verification_url=verification_url
                    )
                    if email_sent:
                        flash_message += ". A verification email has been sent."
                    else:
                        flash_message += ". Verification email could not be sent."
                        flash_category = 'warning'
                record_activity('admin_user_create', f"Admin {current_user.username} created user: {new_user.username}",
                                user_id_for_activity=current_user.id)
                flash(flash_message, flash_category)
                return redirect(url_for('admin.admin_users_list'))
            except ValueError:
                flash('Invalid role selected.', 'danger')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error creating user by admin {current_user.username}: {e}", exc_info=True)
                flash(f'An error occurred: {str(e)}', 'danger')
    elif request.method == 'POST':
        flash('Please correct form errors.', 'warning')
    return render_template('create_user.html', title='Create New User', form=form)


@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    user_to_edit = User.query.get_or_404(user_id)
    form = AdminEditUserForm(obj=user_to_edit)
    if request.method == 'GET':  # Pre-populate role correctly for GET
        form.role.data = user_to_edit.role.value if user_to_edit.role else None

    if form.validate_on_submit():
        if form.username.data != user_to_edit.username and User.query.filter(User.username == form.username.data,
                                                                             User.id != user_id).first():
            flash('That username is already taken.', 'danger')
        elif form.email.data.lower() != user_to_edit.email and User.query.filter(User.email == form.email.data.lower(),
                                                                                 User.id != user_id).first():
            flash('That email address is already registered.', 'danger')
        else:
            try:
                user_to_edit.username = form.username.data
                if user_to_edit.email != form.email.data.lower():  # If email changed
                    user_to_edit.email = form.email.data.lower()
                    user_to_edit.is_email_verified = False  # Require re-verification if admin doesn't check the box
                    # Or send new verification email
                user_to_edit.name = form.name.data if form.name.data else None
                user_to_edit.role = UserRole(form.role.data)
                user_to_edit.is_active = form.is_active.data
                user_to_edit.is_email_verified = form.is_email_verified.data  # Allow admin to set this

                if form.new_password.data:
                    user_to_edit.set_password(form.new_password.data)
                    flash('User password has been updated.', 'info')

                db.session.commit()
                record_activity('admin_user_edit',
                                f"Admin {current_user.username} edited user: {user_to_edit.username}",
                                user_id_for_activity=current_user.id)
                flash(f'User "{user_to_edit.username}" updated.', 'success')
                return redirect(url_for('admin.admin_users_list'))
            except ValueError:
                flash('Invalid role selected.', 'danger')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error editing user {user_id} by admin {current_user.username}: {e}",
                                         exc_info=True)
                flash(f'An error occurred: {str(e)}', 'danger')
    elif request.method == 'POST':
        flash('Please correct form errors.', 'warning')
    return render_template('edit_user.html', title='Edit User', form=form, user_id=user_id,
                           username=user_to_edit.username)


@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)
    if user_to_delete.id == current_user.id:
        flash("You cannot delete your own account.", 'danger')
        return redirect(url_for('admin.admin_users_list'))
    if user_to_delete.is_admin() and User.query.filter_by(role=UserRole.ADMIN).count() <= 1:
        flash("Cannot delete the last admin account.", 'warning')
        return redirect(url_for('admin.admin_users_list'))

    try:
        username_for_log = user_to_delete.username
        # Handle related data (e.g., reassign or delete user's files, models, trades, journals)
        # This example only deletes activities. Ensure cascade settings or manual deletion for other models.
        Activity.query.filter_by(user_id=user_id).delete()
        # If File model has user_id and cascade is not set to delete orphans, you might need:
        # File.query.filter_by(user_id=user_id).delete() (after deleting actual files from disk)
        # Similar logic for TradingModel, Trade, DailyJournal etc. if not cascaded from User model.

        db.session.delete(user_to_delete)
        db.session.commit()
        record_activity('admin_user_delete', f"Admin {current_user.username} deleted user: {username_for_log}",
                        user_id_for_activity=current_user.id)
        flash(f'User "{username_for_log}" has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user {user_id} by admin {current_user.username}: {e}", exc_info=True)
        flash(f'Error deleting user: {str(e)}', 'danger')
    return redirect(url_for('admin.admin_users_list'))

# ... (after admin_delete_user route) ...

@admin_bp.route('/users/bulk_delete', methods=['POST'])
@login_required
@admin_required
def admin_bulk_delete_users():
    """Handles bulk deletion of users by an admin."""
    data = request.get_json()
    if not data or 'user_ids' not in data:
        return jsonify({'status': 'error', 'message': 'Missing user_ids parameter.'}), 400

    user_ids_to_delete_str = data['user_ids']
    if not isinstance(user_ids_to_delete_str, list):
        return jsonify({'status': 'error', 'message': 'user_ids must be a list.'}), 400

    deleted_count = 0
    skipped_count = 0
    skipped_users_info = [] # To store reasons for skipping

    # Convert string IDs to integers and filter out invalid ones
    user_ids_to_delete = []
    for user_id_str_item in user_ids_to_delete_str:
        try:
            user_ids_to_delete.append(int(user_id_str_item))
        except ValueError:
            skipped_count += 1
            skipped_users_info.append(f"Invalid User ID format: {user_id_str_item}")
            current_app.logger.warning(f"Admin bulk delete: Invalid user ID format {user_id_str_item}.")

    if not user_ids_to_delete: # If all provided IDs were invalid or list was empty
         if skipped_count > 0: # Only invalid IDs were provided
             return jsonify({'status': 'error', 'message': 'No valid user IDs provided for deletion.', 'skipped_info': skipped_users_info}), 400
         else: # Empty list of IDs was provided
             return jsonify({'status': 'info', 'message': 'No users selected for deletion.'}), 200


    # It's safer to commit changes for each user individually or collect all operations
    # and do one commit, but individual commits with try/except give more granular feedback.
    # However, for bulk operations, a single transaction might be preferred.
    # The v3 app did a final commit. Let's try to delete valid users.

    admin_users_total_in_db = User.query.filter_by(role=UserRole.ADMIN).count()

    for user_id in user_ids_to_delete:
        if user_id == current_user.id:
            skipped_count += 1
            skipped_users_info.append(f"User ID {user_id} (cannot delete self)")
            current_app.logger.warning(f"Admin bulk delete: Skipped deleting current user (ID: {user_id}).")
            continue

        user_to_delete = User.query.get(user_id)
        if not user_to_delete:
            skipped_count += 1
            skipped_users_info.append(f"User ID {user_id} (not found)")
            current_app.logger.warning(f"Admin bulk delete: User ID {user_id} not found.")
            continue

        # Prevent deleting the last admin if this user is an admin and is part of the current deletion batch
        is_last_admin_check = False
        if user_to_delete.is_admin():
            # This check needs to be careful if multiple admins are in the deletion list
            # A simpler check: if this user is admin AND after this deletion admin_users_total_in_db would be 0
            # This needs refinement if deleting multiple admins at once.
            # For simplicity, if only one admin exists, don't delete them.
            if admin_users_total_in_db <= 1:
                skipped_count += 1
                skipped_users_info.append(f"{user_to_delete.username} (cannot delete last admin)")
                current_app.logger.warning(f"Admin bulk delete: Skipped deleting last admin {user_to_delete.username}.")
                continue

        username_for_log = user_to_delete.username
        try:
            # Handle related data (cascade settings in models.py are preferred)
            # Explicitly delete activities if not cascaded properly or for logging
            Activity.query.filter_by(user_id=user_id).delete()
            # Add deletion for Files on disk if File model doesn't handle it via events/cascade
            # user_files = File.query.filter_by(user_id=user_id).all()
            # for file_record in user_files:
            #     file_disk_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_record.filepath)
            #     if os.path.exists(file_disk_path): os.remove(file_disk_path)
            #     db.session.delete(file_record) # If cascade delete not set on User.files

            db.session.delete(user_to_delete)
            # If an admin was successfully marked for deletion, decrement count for subsequent checks in this batch
            if user_to_delete.is_admin():
                admin_users_total_in_db -=1

            record_activity('admin_bulk_user_delete',
                            f"Admin {current_user.username} bulk deleted user: {username_for_log} (ID: {user_id})",
                            user_id_for_activity=current_user.id) # Log against the admin performing action
            deleted_count += 1
            current_app.logger.info(f"Admin bulk delete: Marked user {username_for_log} (ID: {user_id}) for deletion.")
        except Exception as e:
            # db.session.rollback() # Rollback for this specific user might be complex if batching
            skipped_count += 1
            skipped_users_info.append(f"{username_for_log} (error: {str(e)})")
            current_app.logger.error(f"Admin bulk delete: Error marking user ID {user_id} for deletion: {e}", exc_info=True)

    try:
        db.session.commit() # Commit all successful deletions (and activity logs if not auto-committed)
        message = f"Bulk delete completed. Successfully deleted: {deleted_count} user(s)."
        status = 'success'
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Admin bulk delete: Error during final commit: {e}", exc_info=True)
        message = f'An error occurred during the final commit of deletions: {str(e)}'
        status = 'error'
        # Reset counts if commit failed
        deleted_count = 0
        # skipped_count might need re-evaluation if we don't know which ones failed to commit

    if skipped_count > 0:
        message += f" Skipped: {skipped_count} user(s)."
        if skipped_users_info:
             message += f" Details: {'; '.join(skipped_users_info)}."

    flash(message, status if status == 'success' and deleted_count > 0 else ('warning' if skipped_count > 0 else 'danger'))
    return jsonify({'status': status, 'message': message, 'deleted_count': deleted_count, 'skipped_count': skipped_count, 'skipped_info': skipped_users_info})


# Add this to your admin_bp.py route for system_config

@admin_bp.route('/system-config')
@login_required
@admin_required
def system_config():
    """Admin system configuration dashboard"""
    try:
        # Existing instrument statistics
        total_instruments = Instrument.query.count()
        active_instruments = Instrument.query.filter_by(is_active=True).count()
        inactive_instruments = total_instruments - active_instruments
        default_models_count = TradingModel.query.filter_by(is_default=True).count()

        # Get instruments by asset class (active only)
        instruments_by_class = db.session.query(
            Instrument.asset_class,
            db.func.count(Instrument.id)
        ).filter_by(is_active=True).group_by(Instrument.asset_class).all()

        # NEW: Tag statistics
        total_tags = Tag.query.filter_by(is_default=True).count()
        active_tags = Tag.query.filter_by(is_default=True, is_active=True).count()
        inactive_tags = total_tags - active_tags

        # Get tags by category (active default tags only)
        from app.models import TagCategory
        tags_by_category = []
        for category in TagCategory:
            count = Tag.query.filter_by(
                is_default=True,
                is_active=True,
                category=category
            ).count()
            if count > 0:  # Only include categories with tags
                # Convert enum to display name
                category_name = category.value.replace(' & ', ' ').replace(' Factors', '')
                if len(category_name) > 15:  # Shorten long category names
                    category_name = category_name.replace('Psychological Emotional', 'Psychology')
                    category_name = category_name.replace('Execution Management', 'Execution')
                    category_name = category_name.replace('Market Conditions', 'Market')
                tags_by_category.append((category_name, count))

        current_app.logger.info(f"Admin {current_user.username} accessed system configuration")

        return render_template('admin/system_config.html',
                               title='System Configuration',
                               total_instruments=total_instruments,
                               active_instruments=active_instruments,
                               inactive_instruments=inactive_instruments,
                               instruments_by_class=instruments_by_class,
                               total_tags=total_tags,
                               active_tags=active_tags,
                               inactive_tags=inactive_tags,
                               tags_by_category=tags_by_category,
                               default_models_count=default_models_count)

    except Exception as e:
        current_app.logger.error(f"Error loading system configuration: {e}", exc_info=True)
        flash("Could not load system configuration data.", "danger")
        return redirect(url_for('admin.show_admin_dashboard'))


@admin_bp.route('/instruments')
@login_required
@admin_required
def instruments_list():
    """List all instruments with filtering"""
    try:
        from app.models import Instrument
        from app.forms import InstrumentFilterForm

        filter_form = InstrumentFilterForm(request.args, meta={'csrf': False})

        # Build query with filters
        query = Instrument.query

        # Search filter
        if filter_form.search.data:
            search_term = f"%{filter_form.search.data}%"
            query = query.filter(
                db.or_(
                    Instrument.symbol.ilike(search_term),
                    Instrument.name.ilike(search_term)
                )
            )

        # Exchange filter
        if filter_form.exchange.data:
            query = query.filter(Instrument.exchange == filter_form.exchange.data)

        # Asset class filter
        if filter_form.asset_class.data:
            query = query.filter(Instrument.asset_class == filter_form.asset_class.data)

        # Status filter
        if filter_form.status.data == 'active':
            query = query.filter(Instrument.is_active == True)
        elif filter_form.status.data == 'inactive':
            query = query.filter(Instrument.is_active == False)

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config.get('ITEMS_PER_PAGE', 25)

        instruments_pagination = query.order_by(
            Instrument.is_active.desc(),  # Active instruments first
            Instrument.symbol.asc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        current_app.logger.info(f"Admin {current_user.username} accessed instruments list.")

        return render_template('instruments_list.html',
                               title='Instrument Management',
                               instruments=instruments_pagination.items,
                               pagination=instruments_pagination,
                               filter_form=filter_form,
                               total_count=instruments_pagination.total)

    except Exception as e:
        current_app.logger.error(f"Error loading instruments list: {e}", exc_info=True)
        flash("Could not load instruments list.", "danger")
        return redirect(url_for('admin.system_config'))


@admin_bp.route('/instruments/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_instrument():
    """Create a new instrument"""
    try:
        from app.models import Instrument
        from app.forms import InstrumentForm

        form = InstrumentForm()

        if form.validate_on_submit():
            # Check if symbol already exists
            existing_instrument = Instrument.query.filter_by(symbol=form.symbol.data.upper()).first()
            if existing_instrument:
                flash(f'Instrument with symbol "{form.symbol.data.upper()}" already exists.', 'danger')
                return render_template('create_instrument.html', title='Create Instrument', form=form)

            # Create new instrument
            instrument = Instrument(
                symbol=form.symbol.data.upper(),
                name=form.name.data,
                exchange=form.exchange.data,
                asset_class=form.asset_class.data,
                product_group=form.product_group.data,
                point_value=form.point_value.data,
                tick_size=form.tick_size.data,
                currency=form.currency.data,
                is_active=form.is_active.data
            )

            db.session.add(instrument)
            db.session.commit()

            flash(f'Instrument "{instrument.symbol}" created successfully!', 'success')
            current_app.logger.info(f"Admin {current_user.username} created instrument {instrument.symbol}.")

            return redirect(url_for('admin.instruments_list'))

        return render_template('create_instrument.html', title='Create Instrument', form=form)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in create_instrument: {e}", exc_info=True)
        flash('An error occurred while creating the instrument.', 'danger')
        return redirect(url_for('admin.instruments_list'))


@admin_bp.route('/instruments/<int:instrument_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_instrument(instrument_id):
    """Edit an existing instrument"""
    try:
        from app.models import Instrument
        from app.forms import InstrumentForm

        instrument = Instrument.query.get_or_404(instrument_id)
        form = InstrumentForm(obj=instrument)

        if form.validate_on_submit():
            # Check if changing symbol to an existing one
            if form.symbol.data.upper() != instrument.symbol:
                existing_instrument = Instrument.query.filter_by(symbol=form.symbol.data.upper()).first()
                if existing_instrument:
                    flash(f'Instrument with symbol "{form.symbol.data.upper()}" already exists.', 'danger')
                    return render_template('edit_instrument.html',
                                           title=f'Edit Instrument - {instrument.symbol}',
                                           form=form, instrument=instrument)

            # Update instrument
            instrument.symbol = form.symbol.data.upper()
            instrument.name = form.name.data
            instrument.exchange = form.exchange.data
            instrument.asset_class = form.asset_class.data
            instrument.product_group = form.product_group.data
            instrument.point_value = form.point_value.data
            instrument.tick_size = form.tick_size.data
            instrument.currency = form.currency.data
            instrument.is_active = form.is_active.data

            from datetime import datetime
            instrument.updated_at = datetime.utcnow()

            db.session.commit()

            flash(f'Instrument "{instrument.symbol}" updated successfully!', 'success')
            current_app.logger.info(f"Admin {current_user.username} updated instrument {instrument.symbol}.")

            return redirect(url_for('admin.instruments_list'))

        return render_template('edit_instrument.html',
                               title=f'Edit Instrument - {instrument.symbol}',
                               form=form, instrument=instrument)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error editing instrument {instrument_id}: {e}", exc_info=True)
        flash('An error occurred while updating the instrument.', 'danger')
        return redirect(url_for('admin.instruments_list'))


@admin_bp.route('/instruments/<int:instrument_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_instrument_status(instrument_id):
    """Toggle instrument active/inactive status"""
    try:
        from app.models import Instrument
        from datetime import datetime

        instrument = Instrument.query.get_or_404(instrument_id)
        old_status = "active" if instrument.is_active else "inactive"
        instrument.is_active = not instrument.is_active
        instrument.updated_at = datetime.utcnow()

        db.session.commit()

        new_status = "active" if instrument.is_active else "inactive"
        flash(f'Instrument "{instrument.symbol}" changed from {old_status} to {new_status}!', 'success')
        current_app.logger.info(
            f"Admin {current_user.username} toggled instrument {instrument.symbol} status to {new_status}.")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling instrument status {instrument_id}: {e}", exc_info=True)
        flash('An error occurred while updating the instrument status.', 'danger')

    return redirect(url_for('admin.instruments_list'))


@admin_bp.route('/instruments/<int:instrument_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_instrument(instrument_id):
    """Delete an instrument (only if no trades exist)"""
    try:
        from app.models import Instrument

        instrument = Instrument.query.get_or_404(instrument_id)

        # Check if any trades exist for this instrument
        trades_count = instrument.trades.count()
        if trades_count > 0:
            flash(f'Cannot delete instrument "{instrument.symbol}". It has {trades_count} associated trades. '
                  f'Deactivate it instead if you want to stop using it.', 'warning')
            return redirect(url_for('admin.instruments_list'))

        symbol = instrument.symbol
        db.session.delete(instrument)
        db.session.commit()

        flash(f'Instrument "{symbol}" deleted successfully!', 'success')
        current_app.logger.info(f"Admin {current_user.username} deleted instrument {symbol}.")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting instrument {instrument_id}: {e}", exc_info=True)
        flash('An error occurred while deleting the instrument.', 'danger')

    return redirect(url_for('admin.instruments_list'))


@admin_bp.route('/default-tags')
@login_required
@admin_required
def manage_default_tags():
    """Admin page to manage default tags"""
    # Get ALL default tags (both active and inactive) for admin management
    tags = Tag.query.filter_by(is_default=True).order_by(Tag.category, Tag.name).all()

    # Organize by category manually since we're not using the model method
    from app.models import TagCategory
    tags_by_category = {}
    for category in TagCategory:
        tags_by_category[category.value] = [tag for tag in tags if tag.category == category]

    return render_template('admin/default_tags.html',
                           title='Manage Default Tags',
                           tags_by_category=tags_by_category,
                           TagCategory=TagCategory)


@admin_bp.route('/default-tags/add-category', methods=['POST'])
@login_required
@admin_required
def add_tag_category():
    """Add a new tag category (this would require enum modification)"""
    # For now, return a message that this requires code changes
    return jsonify({
        'success': False,
        'message': 'Adding new categories requires code deployment. Current categories are fixed in the TagCategory enum.'
    })


