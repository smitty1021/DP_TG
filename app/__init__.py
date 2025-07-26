import os
import logging
from datetime import datetime, date as py_date, time as py_time
from flask import Flask, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user as flask_login_current_user
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer
from flask_session import Session
from app.services.discord_service import discord_service


# Import blueprints
from app.blueprints.main_bp import main_bp

# Import only self-contained utility functions needed for filter registration at module level
from .utils import format_date_filter, format_filesize

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"Warning: .env file not found at {dotenv_path}.")

from app.extensions import db, migrate, login_manager, mail, csrf, sess
serializer = None

# --- Constants ---
MONTH_NAMES = [None, "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]
QUARTER_NAMES = [None, "Q1 (Jan-Mar)", "Q2 (Apr-Jun)",
                 "Q3 (Jul-Sep)", "Q4 (Oct-Dec)"]
SESSION_DIRECTIONS = ["None", "Long", "Short"]
SESSION_STATUSES = ["None", "True", "False"]
SESSION_MODEL_STATUSES = ["None", "Valid", "Broken"]
P12_SCENARIO_CHOICES = ["None"] + [f"{i}{ab}" for i in range(1, 6) for ab in ["A", "B"]]
P12_OUTCOMES_MAP = {
    "1A": "Between 0600 – 0830 price starts in the upper half of the P12 box...",
    "1B": "Between 0600 – 0830 price starts in the lower half of the P12 box...",
    "2A": "Between 0600 – 0830 price starts in the lower half of the P12 box...",
    "2B": "Between 0600 – 0830 price starts in the upper half of the P12 box...",
    "3A": "Between 0600 – 0830 price starts in the upper half of the P12 box...",
    "3B": "Between 0600 – 0830 price starts in the lower half of the P12 box...",
    "4A": "Between 0600 – 0830 price starts in the upper half of the P12 box...",
    "4B": "Between 0600 – 0830 price starts in the lower half of the P12 box...",
    "5A": "Between 0600 – 0830 price is in a large range...",
    "5B": "Between 0600 – 0830 price is in a small range..."
}
P12_COMMON_TARGET_INFO = "Once the confirmation is in you will target 0.5% with stop loss at 0.35%."


def create_app(config_class=None):
    global serializer
    app = Flask(__name__, instance_relative_config=True)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError as e:
        print(f"Error creating instance folder {app.instance_path}: {e}")

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_fallback_secret_key'),
        WTF_CSRF_SECRET_KEY=os.environ.get('WTF_CSRF_SECRET_KEY', 'dev_fallback_csrf_key'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL',
                                               f"sqlite:///{os.path.join(app.instance_path, 'app.db')}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=os.path.join(app.instance_path, 'uploads'),
        MAX_CONTENT_LENGTH=int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)),
        ALLOWED_EXTENSIONS=set(
            os.environ.get('ALLOWED_EXTENSIONS', 'pdf,png,jpg,jpeg,doc,docx,xls,xlsx,txt,csv').split(',')),
        ALLOWED_IMAGE_EXTENSIONS={'png', 'jpg', 'jpeg', 'gif', 'webp'},

        # Global Image Management Configuration
        IMAGE_QUALITY=85,  # JPEG quality (1-100)
        MAX_IMAGE_DIMENSION=1920,  # Max width or height in pixels
        RESIZE_LARGE_IMAGES=True,

        ITEMS_PER_PAGE=int(os.environ.get('ITEMS_PER_PAGE', 10)),
        PER_PAGE_TRADES=int(os.environ.get('PER_PAGE_TRADES', 25)),

        # REMOVED: Profile picture configuration
        # PROFILE_PICS_FOLDER_REL=os.environ.get('PROFILE_PICS_FOLDER_REL', 'profile_pics'),
        # PROFILE_PICS_SAVE_PATH=os.path.join(os.path.abspath(os.path.join(app.root_path, 'static')),
        #                                     os.environ.get('PROFILE_PICS_FOLDER_REL', 'profile_pics')),

        # Email Configuration
        MAIL_SERVER=os.environ.get('MAIL_SERVER'),
        MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
        MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't'],
        MAIL_USE_SSL=os.environ.get('MAIL_USE_SSL', 'False').lower() in ['true', '1', 't'],
        MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
        MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
        MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@enterprise-trading.com'),
        MAIL_DEBUG=(os.environ.get('FLASK_DEBUG', '0') == '1'),

        # Discord Integration
        DISCORD_CLIENT_ID=os.environ.get('DISCORD_CLIENT_ID'),
        DISCORD_CLIENT_SECRET=os.environ.get('DISCORD_CLIENT_SECRET'),
        DISCORD_BOT_TOKEN=os.environ.get('DISCORD_BOT_TOKEN'),
        DISCORD_GUILD_ID=os.environ.get('DISCORD_GUILD_ID'),
        DISCORD_REDIRECT_URI=os.environ.get('DISCORD_REDIRECT_URI')
    )

    if config_class:
        app.config.from_object(config_class)

    # Session Configuration
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(app.instance_path, 'flask_session')
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

    # Create upload folders (remove profile_pics folder creation)
    p12_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'p12_scenarios')
    if not os.path.exists(p12_folder):
        try:
            os.makedirs(p12_folder)
        except OSError as e:
            app.logger.error(f"Could not create P12_SCENARIOS_FOLDER: {e}")

    # Create image folders (removed 'user_profile')
    image_folders = ['daily_journals', 'trades', 'general']
    for folder in image_folders:
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
            except OSError as e:
                app.logger.error(f"Could not create {folder} folder: {e}")

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

    # Login manager configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    # Logging configuration
    log_level = logging.DEBUG if app.debug else logging.INFO
    if not app.logger.handlers:
        log_dir = os.path.join(app.instance_path, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'app.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(log_level)

    app.logger.info('Enterprise Trading System startup')

    # Create upload folder
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        try:
            os.makedirs(app.config['UPLOAD_FOLDER'])
        except OSError as e:
            app.logger.error(f"Could not create UPLOAD_FOLDER: {e}")

    app.jinja_env.filters['format_date'] = format_date_filter
    app.jinja_env.filters['file_size'] = format_filesize

    @app.context_processor
    def inject_current_year():
        return {'current_year': datetime.utcnow().year}

    @app.context_processor
    def inject_theme():
        theme_to_apply = 'dark'  # Default theme
        if 'theme' in session:
            theme_to_apply = session['theme']
        elif flask_login_current_user.is_authenticated and hasattr(flask_login_current_user, 'settings') and \
                flask_login_current_user.settings and hasattr(flask_login_current_user.settings, 'theme') and \
                flask_login_current_user.settings.theme:
            theme_to_apply = flask_login_current_user.settings.theme
            session['theme'] = theme_to_apply  # Persist to session for logged-in user

        if theme_to_apply not in ['light', 'dark']:  # Fallback if invalid theme value
            theme_to_apply = 'dark'
        return dict(theme=theme_to_apply)

    @app.context_processor
    def inject_smart_flash_messages():
        """
        Enhanced flash message handling that prevents messages from showing on wrong pages
        """
        from flask import get_flashed_messages, session, request

        # Get current page info
        current_path = request.path
        current_endpoint = request.endpoint

        # Get regular flash messages
        messages = get_flashed_messages(with_categories=True)

        # Check if we have a target page set
        flash_target = session.pop('_flash_target_page', None)
        flash_source = session.pop('_flash_source_page', None)

        filtered_messages = []

        for category, message in messages:
            show_message = True

            # If we have a target page, only show on that page
            if flash_target:
                if flash_target not in current_path:
                    show_message = False

            # If we have a source page, check if we're on a related page
            elif flash_source:
                # Define page families that should share flash messages
                page_families = {
                    'admin': ['/admin/', 'admin.'],
                    'trades': ['/trades/', 'trades.'],
                    'journal': ['/journal/', 'journal.'],
                    'files': ['/files/', 'files.'],
                    'auth': ['/auth/', 'auth.']
                }

                source_family = None
                current_family = None

                # Find which family the source and current pages belong to
                for family, patterns in page_families.items():
                    if any(pattern in flash_source for pattern in patterns):
                        source_family = family
                    if any(pattern in current_path for pattern in patterns) or \
                            any(pattern in (current_endpoint or '') for pattern in patterns):
                        current_family = family

                # Only show message if we're in the same family or on a general page
                if source_family and current_family and source_family != current_family:
                    show_message = False

            if show_message:
                filtered_messages.append((category, message))

        return {'smart_flashed_messages': filtered_messages}

    with app.app_context():
        from . import models  # Import models after db is initialized and within app context

        @login_manager.user_loader
        def load_user(user_id):
            return models.User.query.get(int(user_id))

        # --- Register Blueprints ---
        from .blueprints.main_bp import main_bp
        app.register_blueprint(main_bp)
        from .blueprints.auth_bp import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
        from .blueprints.trading_models import bp as trading_models_bp
        app.register_blueprint(trading_models_bp)
        from .blueprints.files_bp import files_bp
        app.register_blueprint(files_bp, url_prefix='/files')
        from .blueprints.admin_bp import admin_bp
        app.register_blueprint(admin_bp, url_prefix='/admin')
        from .blueprints.trades_bp import trades_bp
        app.register_blueprint(trades_bp, url_prefix='/trades')
        from .blueprints.settings_bp import settings_bp
        app.register_blueprint(settings_bp, url_prefix='/settings')
        from app.blueprints.analytics_bp import analytics_bp
        app.register_blueprint(analytics_bp)
        from .blueprints.journal_bp import journal_bp
        app.register_blueprint(journal_bp, url_prefix='/journal')
        from app.blueprints.p12_scenarios_bp import p12_scenarios_bp
        app.register_blueprint(p12_scenarios_bp)
        from app.blueprints.image_bp import image_bp
        app.register_blueprint(image_bp)
        from app.template_filters import register_template_filters
        register_template_filters(app)  # FIXED THIS LINE
        from app.blueprints.portfolio_bp import portfolio_bp
        app.register_blueprint(portfolio_bp)

        from app.blueprints.admin_access_control import access_control_bp
        app.register_blueprint(access_control_bp)

        try:
            from app.services.discord_service import discord_service
            discord_service.initialize(app)  # Pass the app instance
            app.logger.info("Discord service initialized successfully")
        except Exception as e:
            app.logger.error(f"Failed to initialize Discord service: {e}")
            # Don't fail app startup if Discord service fails


        @app.errorhandler(403)
        def forbidden_page(error):
            app.logger.warning(f"403 Forbidden error at {request.path}: {error}")
            return render_template("errors/403.html", error=error, title="Forbidden"), 403

        @app.errorhandler(404)
        def page_not_found(error):
            app.logger.warning(f"404 Not Found error at {request.path}: {error}")
            return render_template("errors/404.html", error=error, title="Page Not Found"), 404

        @app.errorhandler(500)
        def server_error_page(error):
            app.logger.error(f"500 Server error at {request.path}: {error}", exc_info=True)
            db.session.rollback()  # Rollback session on server error
            return render_template("errors/500.html", error=error, title="Server Error"), 500

        # Initial Data Setup (runs once if tables exist and data is missing)
        if not app.config.get('TESTING', False):
            # Avoid running this during 'flask db' commands before tables are created
            # The 'is_flask_cli' check might need refinement based on actual CLI args if issues persist during migration
            is_flask_db_command = False
            if 'FLASK_RUN_FROM_CLI' in os.environ:  # Check if running via Flask CLI
                # Check if it's a db command (this is a heuristic)
                if request and hasattr(request, 'args') and request.args:
                    if any(arg in ['db', 'migrate', 'upgrade', 'revision'] for arg in request.args):
                        is_flask_db_command = True
                elif any(arg in ['db', 'migrate', 'upgrade', 'revision'] for arg in
                         (os.environ.get('FLASK_COMMAND_ARGS', '').split())):  # Fallback check for CLI args
                    is_flask_db_command = True

            if not is_flask_db_command:  # Only run if not a db command that precedes table creation
                try:
                    if models.AccountSetting.query.filter_by(setting_name='current_account_size').first() is None:
                        default_account_size = models.AccountSetting(setting_name='current_account_size',
                                                                     value_str='100000')
                        db.session.add(default_account_size)
                    if models.NewsEventItem.query.count() == 0:
                        from datetime import time as py_time_init  # Local import for clarity
                        default_events = [
                            models.NewsEventItem(name="FOMC Statement", default_release_time=py_time_init(14, 0)),
                            models.NewsEventItem(name="CPI", default_release_time=py_time_init(8, 30)),
                            models.NewsEventItem(name="NFP", default_release_time=py_time_init(8, 30)),
                            models.NewsEventItem(name="Other")
                        ]
                        for event in default_events: db.session.add(event)
                    db.session.commit()
                except Exception as e:  # Broad exception as tables might not exist during first 'flask run' after 'flask db upgrade'
                    db.session.rollback()
                    app.logger.info(
                        f"Initial data setup: Could not commit initial data (this might be expected if tables are not yet fully created or app is initializing for CLI migration command): {e}")

            #try:
            #    from app.models import Tag
            #    created_count = Tag.create_default_tags()
            #    if created_count > 0:
            #        app.logger.info(f"Created {created_count} default tags")
            #except Exception as e:
            #    app.logger.error(f"Error creating default tags: {e}")

    return app