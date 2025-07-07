import os
from datetime import datetime as dt_parser  # Alias for parsing
from functools import wraps

# Imports from Flask that are generally safe at module level
from flask import current_app, render_template, request, flash, redirect, url_for
from flask_login import current_user as flask_login_current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask import flash as flask_flash, session, request
from urllib.parse import urlparse

# flask_mail.Message will be imported locally in send_email

# DO NOT import db or mail from 'app' here at the top level of utils.py

# --- Token Generation/Verification Helpers ---
def generate_token(data, salt):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(data, salt=salt)


def verify_token(token, salt, max_age_seconds=3600):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return s.loads(token, salt=salt, max_age=max_age_seconds)
    except (SignatureExpired, BadTimeSignature):
        current_app.logger.warning(
            f"Token verification failed (expired/bad signature). Salt: {salt}, Token: {token[:20]}...")
        return None
    except Exception as e:
        current_app.logger.error(f"Token verification error. Salt: {salt}, Error: {e}", exc_info=True)
        return None


# --- Email Sending Helper ---
def send_email(to, subject, template_name, **kwargs):
    from app.extensions import mail  # Import mail when the function is called
    from flask_mail import Message  # Import Message locally
    try:
        if not template_name.startswith('email/'):
            template_name = f'email/{template_name}'
        msg = Message(subject, recipients=[to], html=render_template(template_name, **kwargs),
                      sender=current_app.config.get('MAIL_DEFAULT_SENDER'))
        mail.send(msg)
        current_app.logger.info(f"Email sent to {to} (Subject: '{subject}') via template '{template_name}'.")
        return True
    except Exception as e:
        current_app.logger.error(f"Email send failure to {to} (Subject: '{subject}'): {e}", exc_info=True)
        return False


# --- Activity Logging Helper ---
def record_activity(action, details=None, user_id_for_activity=None):
    from app.extensions import db  # Import db when the function is called
    from app.models import Activity, User  # Local model import

    actual_user_id = user_id_for_activity
    username_for_log = "UnknownUser"
    if actual_user_id is None and flask_login_current_user.is_authenticated:
        actual_user_id = flask_login_current_user.id
        username_for_log = flask_login_current_user.username
    elif actual_user_id:
        user_obj = User.query.get(actual_user_id)
        username_for_log = user_obj.username if user_obj else f"UserID_{actual_user_id}"

    if actual_user_id is None:
        current_app.logger.warning(f"Activity log attempt for '{action}' without user ID.")
        return

    try:
        new_activity = Activity(
            user_id=actual_user_id, action=action, details=details,
            ip_address=request.remote_addr if request else None,
            user_agent=request.user_agent.string if request and request.user_agent else None)
        db.session.add(new_activity)
        db.session.commit()
        current_app.logger.info(
            f"User {username_for_log} (ID: {actual_user_id}) activity: {action} - Details: {details or ''}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Activity log fail for User {username_for_log} (ID: {actual_user_id}), Action: {action}: {e}",
            exc_info=True)


# --- Form Data Parsers (These are self-contained, no app imports needed at module level) ---
def _parse_form_float(form_value_str):
    if form_value_str and str(form_value_str).strip():
        try:
            return float(form_value_str)
        except ValueError:
            return None
    return None


def _parse_form_int(form_value_str):
    if form_value_str and str(form_value_str).strip():
        try:
            return int(form_value_str)
        except ValueError:
            return None
    return None


def _parse_form_time(form_value_str):
    if form_value_str and str(form_value_str).strip():
        try:
            return dt_parser.strptime(form_value_str, '%H:%M').time()
        except ValueError:
            return None
    return None


# --- News Event Options (This needs db and models, so import locally) ---
def get_news_event_options():
    from app.extensions import db  # Import db when the function is called
    from app.models import NewsEventItem  # Local model import
    try:
        news_event_items = [item.name for item in NewsEventItem.query.order_by(NewsEventItem.name).all()]
        options = [""]
        db_items = [n for n in news_event_items if n.lower() != 'none']
        options.extend(sorted(db_items))
        if "Other" not in options: options.append("Other")
        return list(dict.fromkeys(options))
    except Exception as e:
        current_app.logger.error(f"Error fetching news event options: {e}", exc_info=True)
        return ["", "Other"]


# --- File Upload Helper (This is self-contained, uses current_app.config) ---
def allowed_file(filename, allowed_extensions_set):
    if not filename or '.' not in filename: return False
    return filename.rsplit('.', 1)[1].lower() in allowed_extensions_set


# --- Admin Required Decorator (This is self-contained, uses flask_login.current_user) ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not flask_login_current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth.login', next=request.path if request else None))
        if not hasattr(flask_login_current_user, 'is_admin') or not flask_login_current_user.is_admin():
            flash('You do not have permission to access this admin page.', 'danger')
            try:
                return redirect(url_for('main.index'))
            except Exception:
                return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated_function


# --- Formatters for Jinja (These must be self-contained at module level if imported by __init__.py early) ---
def format_filesize(value):
    if value is None or not isinstance(value, (int, float)) or value < 0: return "0 B"
    if value < 1024:
        return f"{int(value)} B"
    elif value < 1024 ** 2:
        return f"{value / 1024:.1f} KB"
    elif value < 1024 ** 3:
        return f"{value / (1024 ** 2):.1f} MB"
    else:
        return f"{value / (1024 ** 3):.1f} GB"


def format_date_filter(value, date_format='%Y-%m-%d %H:%M'):  # Assuming this is the date filter
    from datetime import datetime as dt_datetime, date as py_date, time as py_time  # Local import for types
    if value is None: return ""
    if isinstance(value, (dt_datetime, py_date, py_time)):
        return value.strftime(date_format)
    return str(value)


def flash_for_page(message, category='message', page_pattern=None):
    """
    Flash a message that's tied to a specific page or pattern.

    Args:
        message: The flash message
        category: Flash category (success, danger, warning, info)
        page_pattern: URL pattern to match (e.g., '/admin/instruments', 'instruments')
                     If None, uses current request path
    """
    if page_pattern is None:
        page_pattern = request.path

    # Store the target page with the flash message
    flask_flash(message, category)
    session['_flash_target_page'] = page_pattern


def smart_flash(message, category='message'):
    """
    Smart flash that auto-expires if not displayed on the same page type.
    """
    current_path = request.path
    flask_flash(message, category)
    session['_flash_source_page'] = current_path