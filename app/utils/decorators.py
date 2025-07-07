from functools import wraps
from flask import abort
from flask_login import current_user
from app.models import UserRole

def admin_required(f):
    '''Decorator to require admin permissions.'''
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function