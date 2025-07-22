# Create new file: app/utils/discord_decorators.py

from functools import wraps
from flask import abort, flash, redirect, url_for, current_app
from flask_login import current_user


def require_discord_permission(permission):
    """
    Decorator to require specific Discord permissions.

    Args:
        permission (str): The permission to check for (e.g., 'can_access_portfolio')
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'info')
                return redirect(url_for('auth.login'))

            # Admin users have all permissions
            if current_user.is_admin():
                return f(*args, **kwargs)

            # Check Discord permission
            if not current_user.has_discord_permission(permission):
                current_app.logger.warning(
                    f"User {current_user.username} attempted to access {permission} without permission"
                )
                flash(f'Access denied: {permission.replace("_", " ").title()} permission required.', 'danger')
                return redirect(url_for('main.index'))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_discord_access_level(min_level):
    """
    Decorator to require minimum Discord access level.

    Args:
        min_level (str): Minimum access level ('basic', 'premium', 'vip', 'admin')
    """
    level_hierarchy = {'basic': 1, 'premium': 2, 'vip': 3, 'admin': 4}

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'info')
                return redirect(url_for('auth.login'))

            # Admin users have highest level
            if current_user.is_admin():
                return f(*args, **kwargs)

            # Get user's access level
            permissions = current_user.get_discord_permissions()
            user_level = permissions.get('access_level', 'basic')

            # Check if user meets minimum level
            if level_hierarchy.get(user_level, 0) < level_hierarchy.get(min_level, 0):
                current_app.logger.warning(
                    f"User {current_user.username} attempted to access {min_level} content with {user_level} level"
                )
                flash(f'Access denied: {min_level.title()} access level required.', 'danger')
                return redirect(url_for('main.index'))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_discord_linked(f):
    """
    Decorator to require Discord account to be linked.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth.login'))

        # Admin users can access without Discord
        if current_user.is_admin():
            return f(*args, **kwargs)

        if not current_user.discord_linked:
            flash('You must link your Discord account to access this feature.', 'warning')
            return redirect(url_for('auth.link_discord'))

        return f(*args, **kwargs)

    return decorated_function


def sync_discord_roles_if_needed(f):
    """
    Decorator to automatically sync Discord roles if they're stale.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if (current_user.is_authenticated and
                current_user.discord_linked and
                current_user.discord_id):

            from datetime import datetime, timedelta
            from app.services.discord_service import discord_service
            from app.extensions import db

            # Check if roles need syncing (older than 1 hour)
            if (not current_user.last_discord_sync or
                    current_user.last_discord_sync < datetime.utcnow() - timedelta(hours=1)):

                try:
                    current_roles = discord_service.get_user_roles_sync(current_user.discord_id)
                    current_user.sync_discord_roles(current_roles)
                    db.session.commit()
                except Exception as e:
                    current_app.logger.error(f"Failed to sync Discord roles for {current_user.username}: {e}")

        return f(*args, **kwargs)

    return decorated_function