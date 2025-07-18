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

from flask import (Blueprint, render_template, current_app, request,
                   redirect, url_for, flash, abort, jsonify)
from flask_login import login_required, current_user
from app.extensions import db
from app.utils import admin_required, record_activity, generate_token, send_email, smart_flash
from datetime import datetime
from app.forms import TradingModelForm
from app.models import User, UserRole, Activity, Instrument, Tag, TagCategory, TradingModel, P12Scenario
admin_bp = Blueprint('admin', __name__,
                     template_folder='../templates/admin',
                     url_prefix='/admin')

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


@admin_bp.route('/default-trading-models/<int:model_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_default_trading_model(model_id):
    """Delete a default trading model."""
    model = TradingModel.query.get_or_404(model_id)

    # Verify it's actually a default model
    if not model.is_default:
        flash('This is not a default model and cannot be deleted through this interface.', 'warning')
        return redirect(url_for('admin.manage_default_trading_models'))

    try:
        model_name = model.name
        db.session.delete(model)
        db.session.commit()

        # Log the deletion
        record_activity(f'Deleted default trading model: {model_name}')
        current_app.logger.info(f"Admin {current_user.username} deleted default trading model {model_name}.")

        flash(f'Strategic framework "{model_name}" has been removed successfully.', 'success')

        # Check if request wants JSON response (for AJAX calls)
        if request.headers.get('Content-Type') == 'application/json' or request.is_json:
            return jsonify({
                'success': True,
                'message': f'Strategic framework "{model_name}" has been removed successfully.'
            })

    except Exception as e:
        db.session.rollback()
        error_msg = f'Error removing configuration: {str(e)}'
        current_app.logger.error(f"Error deleting default trading model {model_id}: {e}", exc_info=True)
        flash(error_msg, 'danger')

        # Check if request wants JSON response (for AJAX calls)
        if request.headers.get('Content-Type') == 'application/json' or request.is_json:
            return jsonify({
                'success': False,
                'message': error_msg
            }), 500

    return redirect(url_for('admin.manage_default_trading_models'))


@admin_bp.route('/default-trading-models/<int:model_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_default_trading_model_status(model_id):
    """Toggle the active status of a default trading model."""
    model = TradingModel.query.get_or_404(model_id)

    if not model.is_default:
        flash('This is not a default model.', 'warning')
        return redirect(url_for('admin.manage_default_trading_models'))

    try:
        model.is_active = not model.is_active
        status_text = "activated" if model.is_active else "deactivated"

        db.session.commit()
        flash(f'Strategic framework "{model.name}" has been {status_text} successfully.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating status: {str(e)}', 'danger')

    return redirect(url_for('admin.manage_default_trading_models'))

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
        flash(f'Successfully created {created_count} trading tags!', 'success')
        current_app.logger.info(f"Admin {current_user.username} seeded default tags")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error seeding default tags: {e}")
        flash('Error creating default tags. Please try again.', 'danger')

    return redirect(url_for('admin.manage_default_tags'))


@admin_bp.route('/dashboard')
@login_required
@admin_required
def show_admin_dashboard():
    """Admin comprehensive dashboard with all system statistics and real-time health monitoring"""
    from datetime import datetime, timedelta
    import pytz

    def get_est_timestamp():
        """Get current time in EST/EDT timezone."""
        try:
            utc_now = datetime.utcnow()
            utc = pytz.utc
            est = pytz.timezone('US/Eastern')

            # Convert UTC to EST/EDT
            utc_now = utc.localize(utc_now)
            est_now = utc_now.astimezone(est)

            return est_now
        except:
            # Fallback if pytz not available
            utc_now = datetime.utcnow()
            est_offset = timedelta(hours=-5)  # Approximate EST
            return utc_now + est_offset

    def format_est_timestamp(dt=None):
        """Format timestamp as 24-hour EST/EDT time string."""
        if dt is None:
            dt = get_est_timestamp()

        try:
            return dt.strftime('%H:%M:%S EST')
        except:
            return datetime.now().strftime('%H:%M:%S EST')

    # Initialize default values
    total_users = "N/A"
    active_users_count = "N/A"
    admin_users_count = "N/A"
    total_instruments = 0
    active_instruments = 0
    inactive_instruments = 0
    instruments_by_class = []
    total_tags = 0
    active_tags = 0
    inactive_tags = 0
    tags_by_category = []
    default_models_count = 0
    current_timestamp = datetime.now()

    # Default system health data (fallback)
    system_health = {
        'overall_status': 'unknown',
        'components': {},
        'resources': {
            'instruments': {'active': 0, 'total': 0, 'percentage': 0},
            'tags': {'active': 0, 'total': 0, 'percentage': 0},
            'users': {'current': 0, 'capacity': 100, 'percentage': 0}
        },
        'last_updated_est': format_est_timestamp()
    }
    formatted_health = {}
    system_info = {
        'version': 'v2.1.0',
        'environment': 'Production',
        'last_updated': 'Today',
        'uptime_hours': 'N/A'
    }
    p12_active_count = p12_total_count = 0

    try:
        # Try to import system health monitoring
        try:
            from app.utils.system_health import get_system_health, format_status_display
            system_health_available = True
        except ImportError as e:
            current_app.logger.warning(f"System health monitoring not available: {e}")
            system_health_available = False

        # User statistics
        total_users = User.query.count()
        active_users_count = User.query.filter_by(is_active=True).count()
        admin_users_count = User.query.filter_by(role=UserRole.ADMIN).count()

        # Instrument statistics
        total_instruments = Instrument.query.count()
        active_instruments = Instrument.query.filter_by(is_active=True).count()
        inactive_instruments = total_instruments - active_instruments

        # Get instruments by asset class (active only)
        instruments_by_class = db.session.query(
            Instrument.asset_class,
            db.func.count(Instrument.id)
        ).filter_by(is_active=True).group_by(Instrument.asset_class).all()

        # Tag statistics
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

        # Trading Models count
        default_models_count = TradingModel.query.filter_by(is_default=True).count()

        # P12 scenario count
        p12_active_count = P12Scenario.query.filter_by(is_active=True).count()
        p12_total_count = P12Scenario.query.count()

        # ===== SYSTEM HEALTH MONITORING (with fallback) =====
        if system_health_available:
            try:
                # Get comprehensive system health status
                system_health = get_system_health()

                # Add EST timestamp
                system_health['last_updated_est'] = format_est_timestamp()

                # Format system health for template display
                formatted_health = {}
                for component_name, component_data in system_health.get('components', {}).items():
                    formatted_health[component_name] = {
                        'data': component_data,
                        'display': format_status_display(component_name, component_data)
                    }

                # System version info
                system_info = {
                    'version': 'v2.1.0',
                    'environment': current_app.config.get('ENVIRONMENT', 'Production'),
                    'last_updated': current_timestamp.strftime('%b %d, %Y'),
                    'uptime_hours': system_health.get('components', {}).get('application', {}).get('uptime_hours',
                                                                                                   'N/A')
                }

            except Exception as health_error:
                current_app.logger.warning(f"System health check failed: {health_error}")
                # Use fallback system health data (already initialized above)
                system_health['last_updated_est'] = format_est_timestamp()
        else:
            # Create basic system health data without advanced monitoring
            system_health = {
                'overall_status': 'operational',
                'components': {
                    'application': {'status': 'operational', 'details': 'Application running'},
                    'database': {'status': 'operational', 'details': 'Connected'},
                    'p12_engine': {'status': 'operational', 'details': f'{p12_active_count} Scenarios Active'},
                    'analytics_engine': {'status': 'maintenance', 'details': 'Scheduled Deployment'}
                },
                'resources': {
                    'instruments': {
                        'active': active_instruments,
                        'total': total_instruments,
                        'percentage': round((active_instruments / max(total_instruments, 1)) * 100, 1)
                    },
                    'tags': {
                        'active': active_tags,
                        'total': total_tags,
                        'percentage': round((active_tags / max(total_tags, 1)) * 100, 1)
                    },
                    'users': {
                        'current': total_users,
                        'capacity': 100,
                        'percentage': round((total_users / 100) * 100, 1) if isinstance(total_users, int) else 0
                    }
                },
                'last_updated_est': format_est_timestamp()
            }

            # Create basic formatted health data
            status_mapping = {
                'operational': {'class': 'status-operational', 'label': 'Operational'},
                'maintenance': {'class': 'status-maintenance', 'label': 'Maintenance'},
                'error': {'class': 'status-error', 'label': 'Error'}
            }

            formatted_health = {}
            for component_name, component_data in system_health['components'].items():
                status = component_data.get('status', 'operational')
                formatted_health[component_name] = {
                    'data': component_data,
                    'display': status_mapping.get(status, status_mapping['operational'])
                }

        current_app.logger.info(f"Admin {current_user.username} accessed comprehensive admin dashboard.")

    except Exception as e:
        current_app.logger.error(f"Error fetching admin dashboard stats: {e}", exc_info=True)
        flash("Could not load all dashboard statistics.", "warning")

        # Keep existing fallback values (already initialized above)
        system_health['last_updated_est'] = format_est_timestamp()

    # Get resource data from system_health
    resources = system_health.get('resources', {})

    return render_template('admin/dashboard.html',
                           title='Administration Center',
                           # Existing stats
                           total_users=total_users,
                           active_users_count=active_users_count,
                           admin_users_count=admin_users_count,
                           total_instruments=total_instruments,
                           active_instruments=active_instruments,
                           inactive_instruments=inactive_instruments,
                           instruments_by_class=instruments_by_class,
                           total_tags=total_tags,
                           active_tags=active_tags,
                           inactive_tags=inactive_tags,
                           tags_by_category=tags_by_category,
                           default_models_count=default_models_count,
                           current_timestamp=current_timestamp,
                           # New system health data
                           system_health=system_health,
                           formatted_health=formatted_health,
                           system_info=system_info,
                           resources=resources,
                           p12_active_count=p12_active_count,
                           p12_total_count=p12_total_count)


@admin_bp.route('/users')
@login_required
@admin_required
def admin_users_list():
    """Enhanced user list with search, filters, and sorting"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    # Get search and filter parameters
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '').strip()
    status_filter = request.args.get('status', '').strip()
    verified_filter = request.args.get('verified', '').strip()

    # Get sorting parameters
    sort_field = request.args.get('sort', 'username')  # Default sort by username
    sort_order = request.args.get('order', 'asc')  # Default ascending

    users_on_page, users_pagination, total_users_count, active_users_count, admin_users_count = [], None, 0, 0, 0

    try:
        # Start building the query
        query = User.query

        # Apply search filter
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                db.or_(
                    User.username.ilike(search_term),
                    User.email.ilike(search_term),
                    User.name.ilike(search_term)
                )
            )

        # Apply role filter
        if role_filter:
            try:
                role_enum = UserRole[role_filter.upper()]
                query = query.filter(User.role == role_enum)
            except KeyError:
                current_app.logger.warning(f"Invalid role filter: {role_filter}")

        # Apply status filter
        if status_filter:
            if status_filter.lower() == 'active':
                query = query.filter(User.is_active == True)
            elif status_filter.lower() == 'inactive':
                query = query.filter(User.is_active == False)

        # Apply verification filter
        if verified_filter:
            if verified_filter.lower() == 'verified':
                query = query.filter(User.is_email_verified == True)
            elif verified_filter.lower() == 'unverified':
                query = query.filter(User.is_email_verified == False)

        # Apply sorting
        if sort_field and hasattr(User, sort_field):
            sort_column = getattr(User, sort_field)
            if sort_order.lower() == 'desc':
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            # Default sorting
            query = query.order_by(User.username.asc())

        # Execute paginated query
        users_pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        users_on_page = users_pagination.items

        # Get overall counts (for KPI cards)
        total_users_count = User.query.count()
        active_users_count = User.query.filter_by(is_active=True).count()
        admin_users_count = User.query.filter_by(role=UserRole.ADMIN).count()
        verified_users_count = User.query.filter_by(is_email_verified=True).count()

        # Log the admin action
        search_info = f" with search='{search}'" if search else ""
        filter_info = f" with filters: role={role_filter}, status={status_filter}, verified={verified_filter}" if any(
            [role_filter, status_filter, verified_filter]) else ""
        current_app.logger.info(
            f"Admin {current_user.username} accessed user list page {page}{search_info}{filter_info}.")

    except Exception as e:
        current_app.logger.error(f"Error fetching user list for admin: {e}", exc_info=True)
        flash("Could not load user list.", "danger")
        total_users_count = active_users_count = admin_users_count = verified_users_count = "Error"

    return render_template('admin/users.html',
                           title='User Administration Console',
                           users=users_on_page,
                           pagination=users_pagination,
                           total_users_count=total_users_count,
                           active_users_count=active_users_count,
                           admin_users_count=admin_users_count,
                           verified_users_count=verified_users_count,
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
        Activity.query.filter_by(user_id=user_id).delete()

        db.session.delete(user_to_delete)
        db.session.commit()
        record_activity('admin_user_delete', f"Admin {current_user.username} deleted user: {username_for_log}",
                        user_id_for_activity=current_user.id)
        flash('User resource ' + username_for_log + ' has been successfully deprovisioned.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user {user_id} by admin {current_user.username}: {e}", exc_info=True)
        flash(f'Error deleting user: {str(e)}', 'danger')
    return redirect(url_for('admin.admin_users_list'))

@admin_bp.route('/users/bulk_delete', methods=['POST'])
@login_required
@admin_required
def admin_bulk_delete_users():
    """Handles bulk deletion of users by an admin."""
    try:
        current_app.logger.info(f"Bulk delete called by {current_user.username}")

        # Get JSON data
        data = request.get_json()
        current_app.logger.info(f"Received data: {data}")

        if not data or 'user_ids' not in data:
            current_app.logger.error("Missing user_ids parameter")
            return jsonify({'status': 'error', 'message': 'Missing user_ids parameter.'}), 400

        user_ids_to_delete_str = data['user_ids']
        if not isinstance(user_ids_to_delete_str, list):
            current_app.logger.error("user_ids must be a list")
            return jsonify({'status': 'error', 'message': 'user_ids must be a list.'}), 400

        deleted_count = 0
        skipped_count = 0
        skipped_users_info = []

        # Convert string IDs to integers
        user_ids_to_delete = []
        for user_id_str_item in user_ids_to_delete_str:
            try:
                user_ids_to_delete.append(int(user_id_str_item))
            except ValueError:
                skipped_count += 1
                skipped_users_info.append(f"Invalid User ID format: {user_id_str_item}")

        if not user_ids_to_delete:
            return jsonify({'status': 'error', 'message': 'No valid user IDs provided for deletion.'}), 400

        # Get current admin count
        admin_users_total_in_db = User.query.filter_by(role=UserRole.ADMIN).count()
        current_app.logger.info(f"Current admin count: {admin_users_total_in_db}")

        # Process each user for deletion
        for user_id in user_ids_to_delete:
            current_app.logger.info(f"Processing user ID: {user_id}")

            # Check if trying to delete self
            if user_id == current_user.id:
                skipped_count += 1
                skipped_users_info.append(f"User ID {user_id} (cannot delete self)")
                current_app.logger.warning(f"User {current_user.username} tried to delete themselves")
                continue

            # Get the user
            user_to_delete = User.query.get(user_id)
            if not user_to_delete:
                skipped_count += 1
                skipped_users_info.append(f"User ID {user_id} (not found)")
                current_app.logger.warning(f"User ID {user_id} not found")
                continue

            # Check if it's the last admin
            if user_to_delete.is_admin() and admin_users_total_in_db <= 1:
                skipped_count += 1
                skipped_users_info.append(f"{user_to_delete.username} (cannot delete last admin)")
                current_app.logger.warning(f"Cannot delete last admin: {user_to_delete.username}")
                continue

            username_for_log = user_to_delete.username
            current_app.logger.info(f"Attempting to delete user: {username_for_log} (ID: {user_id})")

            try:
                # Delete related records first (avoid foreign key constraints)
                current_app.logger.info(f"Deleting activities for user {user_id}")
                Activity.query.filter_by(user_id=user_id).delete()

                # Add any other related data cleanup here if needed
                # For example, if you have other models with foreign keys to User:
                # TradingModel.query.filter_by(user_id=user_id).delete()
                # Trade.query.filter_by(user_id=user_id).delete()
                # DailyJournal.query.filter_by(user_id=user_id).delete()

                # Delete the user
                current_app.logger.info(f"Deleting user record: {username_for_log}")
                db.session.delete(user_to_delete)

                # Update admin count if this was an admin
                if user_to_delete.is_admin():
                    admin_users_total_in_db -= 1
                    current_app.logger.info(f"Admin count reduced to: {admin_users_total_in_db}")

                # Log the activity (but don't commit yet)
                record_activity('admin_bulk_user_delete',
                                f"Admin {current_user.username} bulk deleted user: {username_for_log} (ID: {user_id})",
                                user_id_for_activity=current_user.id)

                deleted_count += 1
                current_app.logger.info(f"Successfully processed deletion for: {username_for_log}")

            except Exception as e:
                current_app.logger.error(f"Error deleting user {username_for_log}: {str(e)}", exc_info=True)
                skipped_count += 1
                skipped_users_info.append(f"{username_for_log} (error: {str(e)})")
                # Continue processing other users

        # Commit all changes at once
        try:
            if deleted_count > 0:
                current_app.logger.info(f"Committing deletion of {deleted_count} users")
                db.session.commit()
                message = f"Successfully deleted {deleted_count} user(s)."
                status = 'success'
                current_app.logger.info(f"Bulk delete successful: {deleted_count} users deleted")
            else:
                current_app.logger.info("No users were deleted")
                message = "No users were deleted."
                status = 'success'

        except Exception as e:
            current_app.logger.error(f"Error committing bulk delete: {str(e)}", exc_info=True)
            db.session.rollback()
            message = f'Error during deletion: {str(e)}'
            status = 'error'

        # Add skipped info to message
        if skipped_count > 0:
            message += f" Skipped {skipped_count} user(s)."

        response_data = {
            'status': status,
            'message': message,
            'deleted_count': deleted_count,
            'skipped_count': skipped_count,
            'skipped_info': skipped_users_info
        }

        current_app.logger.info(f"Bulk delete response: {response_data}")
        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Unexpected error in bulk delete: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'Unexpected error: {str(e)}'}), 500


@admin_bp.route('/users/bulk_activate', methods=['POST'])
@login_required
@admin_required
def admin_bulk_activate_users():
    """Handles bulk activation of users by an admin."""
    try:
        current_app.logger.info(f"Bulk activate called by {current_user.username}")

        data = request.get_json()
        current_app.logger.info(f"Received data: {data}")

        if not data or 'user_ids' not in data:
            return jsonify({'status': 'error', 'message': 'Missing user_ids parameter.'}), 400

        user_ids_to_activate_str = data['user_ids']
        if not isinstance(user_ids_to_activate_str, list):
            return jsonify({'status': 'error', 'message': 'user_ids must be a list.'}), 400

        activated_count = 0
        skipped_count = 0
        skipped_users_info = []

        user_ids_to_activate = []
        for user_id_str_item in user_ids_to_activate_str:
            try:
                user_ids_to_activate.append(int(user_id_str_item))
            except ValueError:
                skipped_count += 1
                skipped_users_info.append(f"Invalid User ID format: {user_id_str_item}")

        if not user_ids_to_activate:
            return jsonify({'status': 'error', 'message': 'No valid user IDs provided.'}), 400

        for user_id in user_ids_to_activate:
            try:
                user_to_activate = User.query.get(user_id)
                if not user_to_activate:
                    skipped_count += 1
                    skipped_users_info.append(f"User ID {user_id} (not found)")
                    continue

                if user_to_activate.is_active:
                    skipped_count += 1
                    skipped_users_info.append(f"User {user_to_activate.username} (already active)")
                    continue

                user_to_activate.is_active = True
                activated_count += 1

            except Exception as e:
                skipped_count += 1
                skipped_users_info.append(f"User ID {user_id} (error: {str(e)})")

        db.session.commit()
        record_activity('admin_bulk_activate_users',
                        f"Admin {current_user.username} activated {activated_count} users",
                        user_id_for_activity=current_user.id)

        message = f"Successfully activated {activated_count} user(s)."
        if skipped_count > 0:
            message += f" Skipped {skipped_count} user(s)."

        return jsonify({
            'status': 'success',
            'message': message,
            'activated_count': activated_count,
            'skipped_count': skipped_count,
            'skipped_info': skipped_users_info
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk user activation: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'Bulk activation failed: {str(e)}'}), 500


@admin_bp.route('/users/bulk_deactivate', methods=['POST'])
@login_required
@admin_required
def admin_bulk_deactivate_users():
    """Handles bulk deactivation of users by an admin."""
    try:
        current_app.logger.info(f"Bulk deactivate called by {current_user.username}")

        data = request.get_json()
        current_app.logger.info(f"Received data: {data}")

        if not data or 'user_ids' not in data:
            return jsonify({'status': 'error', 'message': 'Missing user_ids parameter.'}), 400

        user_ids_to_deactivate_str = data['user_ids']
        if not isinstance(user_ids_to_deactivate_str, list):
            return jsonify({'status': 'error', 'message': 'user_ids must be a list.'}), 400

        deactivated_count = 0
        skipped_count = 0
        skipped_users_info = []

        user_ids_to_deactivate = []
        for user_id_str_item in user_ids_to_deactivate_str:
            try:
                user_ids_to_deactivate.append(int(user_id_str_item))
            except ValueError:
                skipped_count += 1
                skipped_users_info.append(f"Invalid User ID format: {user_id_str_item}")

        if not user_ids_to_deactivate:
            return jsonify({'status': 'error', 'message': 'No valid user IDs provided.'}), 400

        admin_users_total_in_db = User.query.filter_by(role=UserRole.ADMIN).count()

        for user_id in user_ids_to_deactivate:
            try:
                user_to_deactivate = User.query.get(user_id)
                if not user_to_deactivate:
                    skipped_count += 1
                    skipped_users_info.append(f"User ID {user_id} (not found)")
                    continue

                if user_id == current_user.id:
                    skipped_count += 1
                    skipped_users_info.append(f"User {user_to_deactivate.username} (cannot deactivate self)")
                    continue

                if user_to_deactivate.is_admin() and admin_users_total_in_db <= 1:
                    skipped_count += 1
                    skipped_users_info.append(f"User {user_to_deactivate.username} (cannot deactivate last admin)")
                    continue

                if not user_to_deactivate.is_active:
                    skipped_count += 1
                    skipped_users_info.append(f"User {user_to_deactivate.username} (already inactive)")
                    continue

                user_to_deactivate.is_active = False
                deactivated_count += 1

            except Exception as e:
                skipped_count += 1
                skipped_users_info.append(f"User ID {user_id} (error: {str(e)})")

        db.session.commit()
        record_activity('admin_bulk_deactivate_users',
                        f"Admin {current_user.username} deactivated {deactivated_count} users",
                        user_id_for_activity=current_user.id)

        message = f"Successfully deactivated {deactivated_count} user(s)."
        if skipped_count > 0:
            message += f" Skipped {skipped_count} user(s)."

        return jsonify({
            'status': 'success',
            'message': message,
            'deactivated_count': deactivated_count,
            'skipped_count': skipped_count,
            'skipped_info': skipped_users_info
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk user deactivation: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'Bulk deactivation failed: {str(e)}'}), 500


@admin_bp.route('/users/bulk_reset_passwords', methods=['POST'])
@login_required
@admin_required
def admin_bulk_reset_passwords():
    """Handles bulk password reset for users by an admin."""
    try:
        current_app.logger.info(f"Bulk password reset called by {current_user.username}")

        data = request.get_json()
        current_app.logger.info(f"Received data: {data}")

        if not data or 'user_ids' not in data:
            return jsonify({'status': 'error', 'message': 'Missing user_ids parameter.'}), 400

        user_ids_to_reset_str = data['user_ids']
        if not isinstance(user_ids_to_reset_str, list):
            return jsonify({'status': 'error', 'message': 'user_ids must be a list.'}), 400

        reset_count = 0
        skipped_count = 0
        skipped_users_info = []

        user_ids_to_reset = []
        for user_id_str_item in user_ids_to_reset_str:
            try:
                user_ids_to_reset.append(int(user_id_str_item))
            except ValueError:
                skipped_count += 1
                skipped_users_info.append(f"Invalid User ID format: {user_id_str_item}")

        if not user_ids_to_reset:
            return jsonify({'status': 'error', 'message': 'No valid user IDs provided.'}), 400

        for user_id in user_ids_to_reset:
            try:
                user_to_reset = User.query.get(user_id)
                if not user_to_reset:
                    skipped_count += 1
                    skipped_users_info.append(f"User ID {user_id} (not found)")
                    continue

                # Generate new password
                import secrets
                import string
                new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

                # Set new password
                user_to_reset.set_password(new_password)

                # Try to send email (skip if email fails)
                try:
                    email_sent = send_email(
                        to=user_to_reset.email,
                        subject="Your Password Has Been Reset - Trading Journal",
                        template_name="password_reset_by_admin.html",
                        username=user_to_reset.username,
                        new_password=new_password,
                        reset_by_admin=current_user.username
                    )
                    reset_count += 1
                except:
                    # Still count as success even if email fails
                    reset_count += 1
                    skipped_users_info.append(f"User {user_to_reset.username} (password reset, email failed)")

            except Exception as e:
                skipped_count += 1
                skipped_users_info.append(f"User ID {user_id} (error: {str(e)})")

        db.session.commit()
        record_activity('admin_bulk_reset_passwords',
                        f"Admin {current_user.username} reset passwords for {reset_count} users",
                        user_id_for_activity=current_user.id)

        message = f"Successfully reset passwords for {reset_count} user(s)."
        if skipped_count > 0:
            message += f" Skipped {skipped_count} user(s)."

        return jsonify({
            'status': 'success',
            'message': message,
            'reset_count': reset_count,
            'skipped_count': skipped_count,
            'skipped_info': skipped_users_info
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk password reset: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'Password reset failed: {str(e)}'}), 500


@admin_bp.route('/users/bulk_verify_emails', methods=['POST'])
@login_required
@admin_required
def admin_bulk_verify_emails():
    """Handles bulk email verification for users by an admin."""
    try:
        current_app.logger.info(f"Bulk email verification called by {current_user.username}")

        data = request.get_json()
        current_app.logger.info(f"Received data: {data}")

        if not data or 'user_ids' not in data:
            return jsonify({'status': 'error', 'message': 'Missing user_ids parameter.'}), 400

        user_ids_to_verify_str = data['user_ids']
        if not isinstance(user_ids_to_verify_str, list):
            return jsonify({'status': 'error', 'message': 'user_ids must be a list.'}), 400

        verified_count = 0
        skipped_count = 0
        skipped_users_info = []

        user_ids_to_verify = []
        for user_id_str_item in user_ids_to_verify_str:
            try:
                user_ids_to_verify.append(int(user_id_str_item))
            except ValueError:
                skipped_count += 1
                skipped_users_info.append(f"Invalid User ID format: {user_id_str_item}")

        if not user_ids_to_verify:
            return jsonify({'status': 'error', 'message': 'No valid user IDs provided.'}), 400

        for user_id in user_ids_to_verify:
            try:
                user_to_verify = User.query.get(user_id)
                if not user_to_verify:
                    skipped_count += 1
                    skipped_users_info.append(f"User ID {user_id} (not found)")
                    continue

                if user_to_verify.is_email_verified:
                    skipped_count += 1
                    skipped_users_info.append(f"User {user_to_verify.username} (email already verified)")
                    continue

                user_to_verify.is_email_verified = True
                verified_count += 1

            except Exception as e:
                skipped_count += 1
                skipped_users_info.append(f"User ID {user_id} (error: {str(e)})")

        db.session.commit()
        record_activity('admin_bulk_verify_emails',
                        f"Admin {current_user.username} verified emails for {verified_count} users",
                        user_id_for_activity=current_user.id)

        message = f"Successfully verified emails for {verified_count} user(s)."
        if skipped_count > 0:
            message += f" Skipped {skipped_count} user(s)."

        return jsonify({
            'status': 'success',
            'message': message,
            'verified_count': verified_count,
            'skipped_count': skipped_count,
            'skipped_info': skipped_users_info
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk email verification: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'Email verification failed: {str(e)}'}), 500

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
                flash(f'Instrument with symbol \'{form.symbol.data.upper()}\' already exists.', 'danger')
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

            flash(f'Instrument \'{instrument.symbol}\' created successfully!', 'success')
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

            flash(f"Instrument '{instrument.symbol}' updated successfully!", 'success')
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
        flash(f"Instrument '{instrument.symbol}' changed from {old_status} to {new_status}!", 'success')
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
            flash(f'Cannot delete instrument \'{instrument.symbol}\'. It has {trades_count} associated trades. '
                  f'Deactivate it instead if you want to stop using it.', 'warning')
            return redirect(url_for('admin.instruments_list'))

        symbol = instrument.symbol
        db.session.delete(instrument)
        db.session.commit()

        flash(f'Instrument \'{symbol}\' deleted successfully!', 'success')
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


@admin_bp.route('/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Enhanced administration center with real-time system health monitoring."""
    try:
        # Import system health monitoring
        from app.utils.system_health import get_system_health, format_status_display

        # Get current timestamp
        current_timestamp = datetime.utcnow()

        # ===== EXISTING STATS COLLECTION =====

        # User statistics
        total_users = User.query.filter_by(is_active=True).count()
        active_users_count = User.query.filter(
            User.is_active == True,
            User.last_login >= datetime.utcnow() - timedelta(days=30)
        ).count()
        admin_users_count = User.query.filter_by(role=UserRole.ADMIN, is_active=True).count()

        # Instrument statistics
        total_instruments = Instrument.query.count()
        active_instruments = Instrument.query.filter_by(is_active=True).count()
        inactive_instruments = total_instruments - active_instruments

        # Get instruments by asset class
        instruments_by_class = db.session.query(
            Instrument.asset_class,
            func.count(Instrument.id).label('count')
        ).group_by(Instrument.asset_class).all()

        # Tag statistics
        total_tags = Tag.query.filter_by(is_default=True).count()
        active_tags = Tag.query.filter_by(is_default=True, is_active=True).count()
        inactive_tags = total_tags - active_tags

        # Get tags by category
        tags_by_category = db.session.query(
            Tag.category,
            func.count(Tag.id).label('count')
        ).filter_by(is_default=True).group_by(Tag.category).all()

        # Trading Model statistics
        default_models_count = TradingModel.query.filter_by(is_default=True).count()

        # ===== NEW SYSTEM HEALTH MONITORING =====

        # Get comprehensive system health status
        system_health = get_system_health()

        # Format system health for template display
        formatted_health = {}
        for component_name, component_data in system_health.get('components', {}).items():
            formatted_health[component_name] = {
                'data': component_data,
                'display': format_status_display(component_name, component_data)
            }

        # Get P12 scenario count (real-time)
        p12_active_count = P12Scenario.query.filter_by(is_active=True).count()
        p12_total_count = P12Scenario.query.count()

        # System version info (you can make this dynamic)
        system_info = {
            'version': 'v2.1.0',
            'environment': current_app.config.get('ENVIRONMENT', 'Production'),
            'last_updated': current_timestamp.strftime('%b %d, %Y'),
            'uptime_hours': system_health.get('components', {}).get('application', {}).get('uptime_hours', 'N/A')
        }

        # Resource utilization from system health
        resources = system_health.get('resources', {})

        current_app.logger.info(f"Admin dashboard accessed by {current_user.username}")

    except Exception as e:
        current_app.logger.error(f"Error fetching admin dashboard stats: {e}", exc_info=True)
        flash("Could not load all dashboard statistics.", "warning")

        # Fallback values
        total_users = active_users_count = admin_users_count = 0
        total_instruments = active_instruments = inactive_instruments = 0
        instruments_by_class = []
        total_tags = active_tags = inactive_tags = 0
        tags_by_category = []
        default_models_count = 0
        p12_active_count = p12_total_count = 0

        # Fallback system health
        system_health = {
            'overall_status': 'unknown',
            'components': {},
            'resources': {
                'instruments': {'active': 0, 'total': 0, 'percentage': 0},
                'tags': {'active': 0, 'total': 0, 'percentage': 0},
                'users': {'current': 0, 'capacity': 100, 'percentage': 0}
            }
        }
        formatted_health = {}
        system_info = {
            'version': 'v2.1.0',
            'environment': 'Production',
            'last_updated': 'Today',
            'uptime_hours': 'N/A'
        }
        resources = system_health['resources']

    return render_template('admin/dashboard.html',
                           title='Administration Center',
                           # Existing stats
                           total_users=total_users,
                           active_users_count=active_users_count,
                           admin_users_count=admin_users_count,
                           total_instruments=total_instruments,
                           active_instruments=active_instruments,
                           inactive_instruments=inactive_instruments,
                           instruments_by_class=instruments_by_class,
                           total_tags=total_tags,
                           active_tags=active_tags,
                           inactive_tags=inactive_tags,
                           tags_by_category=tags_by_category,
                           default_models_count=default_models_count,
                           current_timestamp=current_timestamp,
                           # New system health data
                           system_health=system_health,
                           formatted_health=formatted_health,
                           system_info=system_info,
                           resources=resources,
                           p12_active_count=p12_active_count,
                           p12_total_count=p12_total_count)


# ===== NEW API ENDPOINT FOR REAL-TIME UPDATES =====

@admin_bp.route('/api/system-health')
@login_required
@admin_required
def api_system_health():
    """API endpoint for real-time system health updates (AJAX)."""
    try:
        # Try to import system health monitoring
        try:
            from app.utils.system_health import get_system_health, format_status_display
            system_health_available = True
        except ImportError:
            system_health_available = False

        if system_health_available:
            # Get fresh system health data
            system_health = get_system_health()

            # Format for JSON response
            response_data = {
                'success': True,
                'overall_status': system_health.get('overall_status'),
                'components': {},
                'resources': system_health.get('resources', {}),
                'metrics': system_health.get('metrics', {}),
                'last_updated': system_health.get('last_updated'),
                'timestamp': datetime.utcnow().isoformat()
            }

            # Format component data for frontend
            for component_name, component_data in system_health.get('components', {}).items():
                display_info = format_status_display(component_name, component_data)
                response_data['components'][component_name] = {
                    'status': component_data.get('status'),
                    'details': component_data.get('details'),
                    'display_class': display_info['class'],
                    'display_label': display_info['label'],
                    'display_icon': display_info['icon'],
                    'raw_data': component_data
                }
        else:
            # Fallback response without advanced monitoring
            p12_active_count = P12Scenario.query.filter_by(is_active=True).count()

            response_data = {
                'success': True,
                'overall_status': 'operational',
                'components': {
                    'application': {
                        'status': 'operational',
                        'details': 'Application running',
                        'display_class': 'status-operational',
                        'display_label': 'Operational',
                        'display_icon': 'fas fa-check-circle'
                    },
                    'database': {
                        'status': 'operational',
                        'details': 'Connected',
                        'display_class': 'status-operational',
                        'display_label': 'Operational',
                        'display_icon': 'fas fa-check-circle'
                    },
                    'p12_engine': {
                        'status': 'operational',
                        'details': f'{p12_active_count} Scenarios Active',
                        'display_class': 'status-operational',
                        'display_label': 'Operational',
                        'display_icon': 'fas fa-check-circle'
                    },
                    'analytics_engine': {
                        'status': 'maintenance',
                        'details': 'Scheduled Deployment',
                        'display_class': 'status-maintenance',
                        'display_label': 'Maintenance',
                        'display_icon': 'fas fa-tools'
                    }
                },
                'resources': {},
                'metrics': {},
                'timestamp': datetime.utcnow().isoformat()
            }

        # Add P12 engine real-time data
        p12_active_count = P12Scenario.query.filter_by(is_active=True).count()
        response_data['p12_scenarios'] = {
            'active_count': p12_active_count,
            'display_text': f'{p12_active_count} Scenarios Active'
        }

        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Error fetching system health API: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'overall_status': 'error'
        }), 500


@admin_bp.route('/api/system-metrics')
@login_required
@admin_required
def api_system_metrics():
    """API endpoint for detailed system metrics (for monitoring dashboards)."""
    try:
        from app.utils.system_health import get_system_health

        system_health = get_system_health()

        # Extract detailed metrics
        metrics = system_health.get('metrics', {})
        resources = system_health.get('resources', {})

        # Add database performance metrics
        db_component = system_health.get('components', {}).get('database', {})

        response = {
            'success': True,
            'performance': {
                'cpu_usage': metrics.get('cpu_usage_percent'),
                'memory_usage': metrics.get('memory_usage_percent'),
                'disk_usage': metrics.get('disk_usage_percent'),
                'database_response_time': db_component.get('response_time_ms')
            },
            'capacity': {
                'instruments_utilization': resources.get('instruments', {}).get('percentage', 0),
                'tags_utilization': resources.get('tags', {}).get('percentage', 0),
                'users_utilization': resources.get('users', {}).get('percentage', 0)
            },
            'database': {
                'connection_pool_size': db_component.get('connection_pool_size'),
                'active_connections': db_component.get('checked_out_connections'),
                'available_connections': db_component.get('checked_in_connections')
            },
            'timestamp': datetime.utcnow().isoformat()
        }

        return jsonify(response)

    except Exception as e:
        current_app.logger.error(f"Error fetching system metrics API: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/debug/routes')
@login_required
@admin_required
def debug_routes():
    routes = []
    for rule in current_app.url_map.iter_rules():
        if 'bulk' in rule.rule:
            routes.append(f"{rule.rule} - Methods: {list(rule.methods)}")
    return f"<pre>{'<br>'.join(routes)}</pre>"

@admin_bp.route('/users/test_bulk', methods=['POST'])
@login_required
@admin_required
def test_bulk():
    return jsonify({'status': 'success', 'message': 'Test route working!'})


@admin_bp.route('/debug/check-routes')
@login_required
@admin_required
def debug_check_routes():
    """Debug endpoint to check if bulk routes are registered."""
    from flask import current_app

    routes_info = []
    for rule in current_app.url_map.iter_rules():
        if 'bulk' in rule.rule:
            routes_info.append({
                'rule': rule.rule,
                'methods': list(rule.methods),
                'endpoint': rule.endpoint
            })

    return jsonify({
        'status': 'success',
        'message': 'Route check completed',
        'bulk_routes': routes_info,
        'total_routes': len(list(current_app.url_map.iter_rules()))
    })


# SIMPLE TEST ROUTE - to verify basic POST requests work
@admin_bp.route('/users/test-post', methods=['POST'])
@login_required
@admin_required
def test_post_route():
    """Simple test route to verify POST requests work."""
    try:
        data = request.get_json()
        return jsonify({
            'status': 'success',
            'message': 'Test POST route working!',
            'received_data': data,
            'user': current_user.username
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Test route error: {str(e)}'
        }), 500
