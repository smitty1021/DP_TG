from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, session
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Settings, Tag, TagCategory
from app.forms import TagForm
import json

settings_bp = Blueprint('settings', __name__, template_folder='../templates/settings')


@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
def view_settings():
    """Updated settings page with statistics"""
    try:

        # Get tag statistics
        total_available_tags = Tag.query.filter(
            db.or_(
                Tag.is_default == True,
                Tag.user_id == current_user.id
            )
        ).filter(Tag.is_active == True).count()

        total_default_tags = Tag.query.filter_by(is_default=True, is_active=True).count()
        total_personal_tags = Tag.query.filter_by(user_id=current_user.id).count()

        # Get tags by category (available to user)
        from app.models import TagCategory
        tags_by_category = []
        for category in TagCategory:
            count = Tag.query.filter(
                db.or_(
                    Tag.is_default == True,
                    Tag.user_id == current_user.id
                )
            ).filter(
                Tag.is_active == True,
                Tag.category == category
            ).count()

            if count > 0:  # Only include categories with tags
                # Convert enum to display name and shorten
                category_name = category.value.replace(' & ', ' ').replace(' Factors', '')
                if len(category_name) > 15:
                    category_name = category_name.replace('Psychological Emotional', 'Psychology')
                    category_name = category_name.replace('Execution Management', 'Execution')
                    category_name = category_name.replace('Market Conditions', 'Market')
                tags_by_category.append((category_name, count))

        return render_template('settings/settings.html',
                               title='User Settings',
                               total_available_tags=total_available_tags,
                               total_default_tags=total_default_tags,
                               total_personal_tags=total_personal_tags,
                               tags_by_category=tags_by_category)

    except Exception as e:
        current_app.logger.error(f"Error loading settings: {e}", exc_info=True)
        flash("Could not load settings data.", "danger")
        return render_template('settings/settings.html', title='User Settings')


@settings_bp.route('/personal-tags')
@login_required
def manage_personal_tags():
    """Personal tags management page"""
    try:
        # Get all tags available to the user (default + personal)
        available_tags = Tag.query.filter(
            db.or_(
                Tag.is_default == True,
                Tag.user_id == current_user.id
            )
        ).order_by(Tag.category, Tag.name).all()

        # Organize by category
        from app.models import TagCategory
        tags_by_category = {}
        for category in TagCategory:
            category_tags = [tag for tag in available_tags if tag.category == category]
            tags_by_category[category.value] = category_tags

        return render_template('settings/personal_tags.html',
                               title='Manage Personal Tags',
                               tags_by_category=tags_by_category,
                               TagCategory=TagCategory)

    except Exception as e:
        current_app.logger.error(f"Error loading personal tags: {e}", exc_info=True)
        flash("Could not load personal tags.", "danger")
        return redirect(url_for('settings.view_settings'))


@settings_bp.route('/tags/create', methods=['POST'])
@login_required
def create_tag():
    """Create a new personal tag"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        category_name = data.get('category', '')
        color_category = data.get('color_category', 'neutral')

        # Improved is_active handling with explicit type checking
        is_active = data.get('is_active')
        if is_active is None:
            is_active = True  # Default to active
        elif isinstance(is_active, str):
            is_active = is_active.lower() == 'true'
        elif not isinstance(is_active, bool):
            is_active = bool(is_active)

        if not name or not category_name:
            return jsonify({'success': False, 'message': 'Name and category are required'})

        # Validate color category
        if color_category not in ['neutral', 'good', 'bad']:
            color_category = 'neutral'

        # Validate category
        try:
            from app.models import TagCategory
            category = TagCategory[category_name]
        except KeyError:
            return jsonify({'success': False, 'message': 'Invalid category'})

        # Check for duplicates (user's tags + default tags)
        existing = Tag.query.filter(
            Tag.name == name,
            db.or_(
                Tag.user_id == current_user.id,
                Tag.is_default == True
            )
        ).first()

        if existing:
            return jsonify({'success': False, 'message': 'Tag name already exists'})

        # Create new personal tag
        new_tag = Tag(
            name=name,
            category=category,
            color_category=color_category,
            user_id=current_user.id,
            is_default=False,
            is_active=is_active
        )

        db.session.add(new_tag)
        db.session.commit()

        # Log the creation for debugging
        current_app.logger.info(f"User {current_user.username} created tag '{name}' with active status: {is_active}")

        return jsonify({
            'success': True,
            'message': f'Tag "{name}" created successfully',
            'tag': {
                'id': new_tag.id,
                'name': new_tag.name,
                'category': new_tag.category.name,
                'color_category': new_tag.color_category,
                'is_default': new_tag.is_default,
                'is_active': new_tag.is_active
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating personal tag: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Error creating tag'})


@settings_bp.route('/tags/<int:tag_id>/edit', methods=['POST'])
@login_required
def edit_tag(tag_id):
    """Edit a personal tag"""
    try:
        tag = Tag.query.get_or_404(tag_id)

        # Ensure user owns this tag (not a default tag)
        if tag.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Cannot edit this tag'})

        data = request.get_json()
        name = data.get('name', '').strip()
        category_name = data.get('category', '')
        color_category = data.get('color_category', 'neutral')

        # Improved is_active handling with explicit type checking
        is_active = data.get('is_active')
        if is_active is None:
            is_active = tag.is_active  # Keep current value if not provided
        elif isinstance(is_active, str):
            is_active = is_active.lower() == 'true'
        elif not isinstance(is_active, bool):
            is_active = bool(is_active)

        if not name or not category_name:
            return jsonify({'success': False, 'message': 'Name and category are required'})

        # Validate color category
        if color_category not in ['neutral', 'good', 'bad']:
            color_category = 'neutral'

        # Validate category
        try:
            from app.models import TagCategory
            category = TagCategory[category_name]
        except KeyError:
            return jsonify({'success': False, 'message': 'Invalid category'})

        # Check for duplicates (excluding current tag)
        existing = Tag.query.filter(
            Tag.id != tag_id,
            Tag.name == name,
            db.or_(
                Tag.user_id == current_user.id,
                Tag.is_default == True
            )
        ).first()

        if existing:
            return jsonify({'success': False, 'message': 'Tag name already exists'})

        # Store old values for logging
        old_name = tag.name
        old_active = tag.is_active

        # Update tag
        tag.name = name
        tag.category = category
        tag.color_category = color_category
        tag.is_active = is_active
        db.session.commit()

        # Log the update for debugging
        if old_active != is_active:
            current_app.logger.info(
                f"User {current_user.username} changed tag '{old_name}' active status from {old_active} to {is_active}")

        return jsonify({
            'success': True,
            'message': f'Tag "{name}" updated successfully',
            'tag': {
                'id': tag.id,
                'name': tag.name,
                'category': tag.category.name,
                'color_category': tag.color_category,
                'is_default': tag.is_default,
                'is_active': tag.is_active
            }
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error editing personal tag {tag_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Error updating tag'})


@settings_bp.route('/tags')
@login_required
def manage_tags():
    """User tags management page"""
    # Get default tags (available to all users)
    default_tags = Tag.query.filter_by(is_default=True, is_active=True).order_by(Tag.name).all()

    # Get user's personal tags
    user_tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name).all()

    # Get user's selected default tags (many-to-many relationship)
    user_selected_defaults = current_user.selected_default_tags if hasattr(current_user,
                                                                           'selected_default_tags') else []

    return render_template('settings/tags.html',
                           title='Manage Tags',
                           default_tags=default_tags,
                           user_tags=user_tags,
                           user_selected_defaults=user_selected_defaults)


@settings_bp.route('/tags/toggle-default/<int:tag_id>', methods=['POST'])
@login_required
def toggle_default_tag(tag_id):
    """Toggle a default tag for the current user"""
    tag = Tag.query.get_or_404(tag_id)

    if not tag.is_default:
        return jsonify({'success': False, 'message': 'Can only toggle default tags'})

    # Add/remove tag from user's selected defaults
    if tag in current_user.selected_default_tags:
        current_user.selected_default_tags.remove(tag)
        action = 'removed'
    else:
        current_user.selected_default_tags.append(tag)
        action = 'added'

    db.session.commit()

    return jsonify({
        'success': True,
        'action': action,
        'message': f'Tag "{tag.name}" {action} successfully'
    })


@settings_bp.route('/tags/restore-defaults', methods=['POST'])
@login_required
def restore_default_tags():
    """Restore all default tags for the user"""
    default_tags = Tag.query.filter_by(is_default=True, is_active=True).all()
    current_user.selected_default_tags = default_tags
    db.session.commit()

    flash(f'Restored {len(default_tags)} default tags', 'success')
    return redirect(url_for('settings.manage_tags'))


@settings_bp.route('/tags/<int:tag_id>/delete', methods=['POST'])
@login_required
def delete_tag(tag_id):
    """Delete a user tag (including defaults copied to user)"""
    try:
        tag = Tag.query.get_or_404(tag_id)

        # Users can delete any tag in their collection (including copied defaults)
        # But they can't delete the master default tags (user_id=None)
        if tag.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Permission denied'})

        tag_name = tag.name
        db.session.delete(tag)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Tag "{tag_name}" deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting tag {tag_id}: {e}")
        return jsonify({'success': False, 'message': 'Error deleting tag'})


@settings_bp.route('/reset-default-tags', methods=['POST'])
@login_required
def reset_default_tags():
    """Reset user tags to only include defaults"""
    try:
        # Delete all user's custom tags (not default tags)
        user_tags = Tag.query.filter_by(user_id=current_user.id).all()
        custom_tag_count = len(user_tags)

        for tag in user_tags:
            db.session.delete(tag)

        db.session.commit()

        # Flash warning message that will show up as notification
        flash(f'Reset complete! Deleted {custom_tag_count} custom tags and restored default tags.', 'success')

        current_app.logger.info(
            f"User {current_user.username} reset tags to defaults, deleted {custom_tag_count} custom tags")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error resetting tags for user {current_user.id}: {e}", exc_info=True)
        flash('Error resetting tags. Please try again.', 'danger')

    return redirect(url_for('settings.manage_personal_tags'))


@settings_bp.route('/export/user-settings')
@login_required
def export_user_settings():
    """Export user configuration settings as JSON"""
    try:
        from flask import Response
        import json
        from datetime import datetime
        
        # Gather user settings data
        user_data = {
            'user_info': {
                'username': current_user.username,
                'email': current_user.email,
                'role': current_user.role.value,
                'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
                'is_active': current_user.is_active
            },
            'personal_tags': [],
            'export_date': datetime.utcnow().isoformat()
        }
        
        # Get user's personal tags
        personal_tags = Tag.query.filter_by(user_id=current_user.id).all()
        for tag in personal_tags:
            user_data['personal_tags'].append({
                'name': tag.name,
                'category': tag.category.name,
                'color_category': tag.color_category,
                'is_active': tag.is_active,
                'created_at': tag.created_at.isoformat() if hasattr(tag, 'created_at') and tag.created_at else None
            })
        
        # Generate filename
        filename = f"user_settings_{current_user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Create JSON response
        json_data = json.dumps(user_data, indent=2, sort_keys=True)
        
        return Response(
            json_data,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exporting user settings: {e}", exc_info=True)
        flash('Error exporting user settings. Please try again.', 'danger')
        return redirect(url_for('settings.view_settings'))


@settings_bp.route('/export/personal-tags')
@login_required
def export_personal_tags():
    """Export user's personal tags as JSON"""
    try:
        from flask import Response
        import json
        from datetime import datetime
        
        # Get user's personal tags
        personal_tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.category, Tag.name).all()
        
        tags_data = {
            'username': current_user.username,
            'export_date': datetime.utcnow().isoformat(),
            'total_tags': len(personal_tags),
            'tags': []
        }
        
        for tag in personal_tags:
            tags_data['tags'].append({
                'name': tag.name,
                'category': tag.category.name,
                'color_category': tag.color_category,
                'is_active': tag.is_active,
                'created_at': tag.created_at.isoformat() if hasattr(tag, 'created_at') and tag.created_at else None
            })
        
        # Generate filename
        filename = f"personal_tags_{current_user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Create JSON response
        json_data = json.dumps(tags_data, indent=2, sort_keys=True)
        
        return Response(
            json_data,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exporting personal tags: {e}", exc_info=True)
        flash('Error exporting personal tags. Please try again.', 'danger')
        return redirect(url_for('settings.view_settings'))