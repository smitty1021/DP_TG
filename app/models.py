from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date as py_date, time as py_time
from datetime import datetime as dt  # Alias for dt.utcnow
from datetime import datetime, timezone
import enum
import uuid
import os
import statistics
from sqlalchemy import ForeignKey
from app.extensions import db
from enum import Enum



user_default_tags = db.Table('user_default_tags',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

# --- Constants for Models ---
QUARTER_NAMES = [None, "Q1 (Jan-Mar)", "Q2 (Apr-Jun)", "Q3 (Jul-Sep)", "Q4 (Oct-Dec)"]


# --- User and Authentication Models ---
class UserRole(enum.Enum):
    USER = 'user'
    EDITOR = 'editor'
    ADMIN = 'admin'

    def __str__(self): return self.value


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.USER)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    profile_picture = db.Column(db.String(200), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    is_email_verified = db.Column(db.Boolean, nullable=False, server_default='0')

    # Relationships
    activities = db.relationship('Activity', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    files = db.relationship('File', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    settings = db.relationship('Settings', backref='user', uselist=False, cascade='all, delete-orphan')
    api_keys = db.relationship('ApiKey', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    trading_models = db.relationship('TradingModel',
                                     foreign_keys='TradingModel.user_id',
                                     backref='user',
                                     lazy='dynamic')
    trades = db.relationship('Trade', backref='user', lazy='dynamic')
    daily_journals = db.relationship('DailyJournal', backref='user', lazy='dynamic')
    weekly_journals = db.relationship('WeeklyJournal', backref='user', lazy='dynamic')
    monthly_journals = db.relationship('MonthlyJournal', backref='user', lazy='dynamic')
    quarterly_journals = db.relationship('QuarterlyJournal', backref='user', lazy='dynamic')
    yearly_journals = db.relationship('YearlyJournal', backref='user', lazy='dynamic')

    selected_default_tags = db.relationship(
        'Tag',
        secondary=user_default_tags,
        backref=db.backref('users_who_selected', lazy='dynamic'),
        lazy='dynamic',
        primaryjoin='User.id == user_default_tags.c.user_id',
        secondaryjoin='and_(Tag.id == user_default_tags.c.tag_id, Tag.is_default == True)'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == UserRole.ADMIN

    def is_editor(self):
        return self.role in [UserRole.EDITOR, UserRole.ADMIN]

    def generate_api_key(self, name, expiration_days=30):
        api_key = ApiKey(
            user_id=self.id,
            name=name,
            key=uuid.uuid4().hex,
            expires_at=datetime.utcnow() + timedelta(days=expiration_days)
        )
        db.session.add(api_key)
        return api_key

    @property
    def storage_usage(self):
        return db.session.query(db.func.sum(File.filesize)).filter_by(user_id=self.id).scalar() or 0

    @classmethod
    def find_by_username(cls, username):
        return cls.query.filter_by(username=username).first()

    @classmethod
    def find_by_email(cls, email):
        return cls.query.filter_by(email=email.lower()).first()

    def __repr__(self):
        return f'<User {self.username} (ID: {self.id})>'


class Activity(db.Model):
    __tablename__ = 'activity'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_activity_user'), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    resource_id = db.Column(db.Integer, nullable=True)
    resource_type = db.Column(db.String(50), nullable=True)

    @classmethod
    def log(cls, user_id, action, details=None, ip_address=None, user_agent=None, resource_id=None, resource_type=None):
        activity = cls(
            user_id=user_id, action=action, details=details,
            ip_address=ip_address, user_agent=user_agent,
            resource_id=resource_id, resource_type=resource_type
        )
        db.session.add(activity)
        return activity

    def __repr__(self):
        return f'<Activity {self.action} by User {self.user_id} at {self.timestamp.strftime("%Y-%m-%d %H:%M")}>'


class File(db.Model):
    __tablename__ = 'file'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_file_user'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False, unique=True)
    filesize = db.Column(db.Integer, nullable=False)
    file_type = db.Column(db.String(50), nullable=True)
    mime_type = db.Column(db.String(100), nullable=True)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    last_accessed = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_public = db.Column(db.Boolean, nullable=False, default=False)
    download_count = db.Column(db.Integer, nullable=False, default=0)

    @property
    def full_disk_path(self):
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        return os.path.join(upload_folder, self.filepath)

    @property
    def extension(self):
        return os.path.splitext(self.filename)[1].lower().lstrip('.') if '.' in self.filename else ''

    @property
    def size_formatted(self):
        if not isinstance(self.filesize, (int, float)) or self.filesize < 0:
            return "0 B"
        if self.filesize < 1024:
            return f"{self.filesize} B"
        elif self.filesize < 1024 ** 2:
            return f"{self.filesize / 1024:.1f} KB"
        elif self.filesize < 1024 ** 3:
            return f"{self.filesize / (1024 ** 2):.1f} MB"
        return f"{self.filesize / (1024 ** 3):.1f} GB"

    def record_access(self, commit=False):
        self.last_accessed = datetime.utcnow()
        self.download_count += 1
        if commit:
            db.session.commit()
        return self

    def __repr__(self):
        return f'<File {self.filename} (ID: {self.id}, User: {self.user_id})>'


class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_settings_user'), nullable=False, unique=True)
    theme = db.Column(db.String(20), nullable=False, default='light')
    notifications_enabled = db.Column(db.Boolean, nullable=False, default=True)
    items_per_page = db.Column(db.Integer, nullable=False, default=20)
    language = db.Column(db.String(10), nullable=False, default='en')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)
    custom_settings = db.Column(db.JSON, nullable=True)

    @classmethod
    def get_for_user(cls, user_id):
        settings = cls.query.filter_by(user_id=user_id).first()
        if not settings:
            settings = cls(user_id=user_id)
            db.session.add(settings)
        return settings

    def __repr__(self):
        return f'<Settings for User ID: {self.user_id}>'


class ApiKey(db.Model):
    __tablename__ = 'api_key'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_apikey_user'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    key = db.Column(db.String(64), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    permissions = db.Column(db.String(255), nullable=True)

    @property
    def is_expired(self):
        return self.expires_at and datetime.utcnow() > self.expires_at

    @property
    def is_valid(self):
        return self.is_active and not self.is_expired

    def use(self):
        self.last_used_at = datetime.utcnow()

    @classmethod
    def find_by_key(cls, key_value):
        return cls.query.filter_by(key=key_value).first()

    def __repr__(self):
        return f'<ApiKey {self.name} (User: {self.user_id})>'


# --- Group and Association Models ---
user_group_association = db.Table('user_group_association',
                                  db.Column('user_id', db.Integer,
                                            db.ForeignKey('user.id', name='fk_user_group_assoc_user'),
                                            primary_key=True),
                                  db.Column('group_id', db.Integer,
                                            db.ForeignKey('group.id', name='fk_user_group_assoc_group'),
                                            primary_key=True)
                                  )


class Group(db.Model):
    __tablename__ = 'group'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_group_created_by_user'), nullable=True)
    creator = db.relationship('User', foreign_keys=[created_by_user_id])
    members = db.relationship('User', secondary=user_group_association,
                              backref=db.backref('member_of_groups', lazy='dynamic'))

    def __repr__(self):
        return f'<Group {self.name} (ID: {self.id})>'


class PasswordReset(db.Model):
    __tablename__ = 'password_reset'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_passwordreset_user'), nullable=False, index=True)
    token = db.Column(db.String(100), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    user = db.relationship('User', backref=db.backref('password_resets', lazy='dynamic', cascade='all, delete-orphan'))

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self):
        return not self.used and not self.is_expired

    @classmethod
    def generate_token(cls, user_id, expiration_hours=24):
        token_value = uuid.uuid4().hex
        reset = cls(
            user_id=user_id,
            token=token_value,
            expires_at=datetime.utcnow() + timedelta(hours=expiration_hours)
        )
        db.session.add(reset)
        return reset

    @classmethod
    def find_by_token(cls, token_value):
        return cls.query.filter_by(token=token_value).first()

    def use(self):
        self.used = True

    def __repr__(self):
        return f'<PasswordReset for User ID: {self.user_id} (Token: {self.token[:10]}...)>'


# --- Instrument Model (Fixed and consolidated) ---
class Instrument(db.Model):
    """
    Instrument model for Random's trading system.
    This version removes all hardcoded fallback logic.
    Data is sourced exclusively from the database.
    """
    __tablename__ = 'instrument'

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    exchange = db.Column(db.String(50), nullable=True)
    asset_class = db.Column(db.String(50), nullable=True, index=True)
    product_group = db.Column(db.String(50), nullable=True)
    point_value = db.Column(db.Float, nullable=False)
    tick_size = db.Column(db.Float, nullable=True)
    currency = db.Column(db.String(10), nullable=False, default='USD')
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to trades
    trades = db.relationship('Trade', back_populates='instrument_obj', lazy='dynamic')

    def __repr__(self):
        return f"<Instrument {self.symbol}: {self.name}>"

    @classmethod
    def get_instrument_choices(cls):
        """Returns choices for form SelectField, strictly from the database."""
        choices = [('', 'Select Instrument')]
        try:
            # Query only active instruments and order them for consistency
            instruments = cls.query.filter_by(is_active=True).order_by(cls.symbol).all()
            for instrument in instruments:
                choice_text = f"{instrument.symbol} ({instrument.name})"
                choices.append((str(instrument.id), choice_text)) # Use ID for value
        except Exception as e:
            # If the database query fails, log it and return an empty list
            current_app.logger.error(f"Could not load instrument choices from database: {e}")
            return [('', 'DB Error - No Instruments Found')]
        return choices

    @classmethod
    def get_point_value(cls, instrument_id):
        """Get point value for a specific instrument ID, strictly from the database."""
        try:
            instrument = cls.query.get(instrument_id)
            return instrument.point_value if instrument else None
        except Exception as e:
            current_app.logger.error(f"Could not get point value for instrument ID {instrument_id}: {e}")
            return None

    @classmethod
    def get_instrument_point_values(cls):
        """Returns a dictionary of all active instruments with their point values."""
        try:
            instruments = cls.query.filter_by(is_active=True).all()
            return {instrument.symbol: instrument.point_value for instrument in instruments}
        except Exception as e:
            current_app.logger.error(f"Could not load instrument point values dictionary: {e}")
            return {}

# Association table for the many-to-many relationship between Trades and Tags
trade_tags = db.Table('trade_tags',
    db.Column('trade_id', db.Integer, db.ForeignKey('trade.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)


class TagCategory(Enum):
    SETUP_STRATEGY = "Setup & Strategy"
    MARKET_CONDITIONS = "Market Conditions"
    EXECUTION_MANAGEMENT = "Execution & Management"
    PSYCHOLOGICAL_EMOTIONAL = "Psychological & Emotional Factors"


# Replace the existing Tag model with this enhanced version:
class Tag(db.Model):
    __tablename__ = 'tag'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    category = db.Column(db.Enum(TagCategory), nullable=False, default=TagCategory.SETUP_STRATEGY)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_tag_user'),
                        nullable=True)  # NULL for default tags
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    color_category = db.Column(db.String(20), nullable=True, default='neutral')  # 'good', 'bad', 'neutral'
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('tags', lazy='dynamic'))

    # Constraints: Either global default (user_id=None) or user-specific unique name
    __table_args__ = (
        db.UniqueConstraint('name', 'user_id', name='uq_tag_name_user'),
        db.Index('idx_tag_user_category', 'user_id', 'category'),
        db.Index('idx_tag_default_active', 'is_default', 'is_active'),
    )

    @classmethod
    def get_default_tags(cls):
        """Get all default tags organized by category"""
        return cls.query.filter_by(is_default=True, is_active=True).order_by(cls.category, cls.name).all()

    @classmethod
    def get_available_for_user(cls, user_id):
        """Get all tags available to a specific user (default + personal)"""
        return cls.query.filter(
            db.or_(
                cls.is_default == True,
                cls.user_id == user_id
            )
        ).filter(cls.is_active == True).order_by(cls.name).all()

    @classmethod
    def get_user_tags(cls, user_id, include_defaults=True):
        """Get user's tags, optionally including defaults"""
        query = cls.query.filter_by(user_id=user_id, is_active=True)

        if include_defaults:
            default_query = cls.query.filter_by(is_default=True, is_active=True)
            query = query.union(default_query)

        return query.order_by(cls.category, cls.name).all()

    @classmethod
    def get_tags_by_category(cls, user_id=None):
        """Get tags organized by category for a user (including defaults)"""
        if user_id:
            tags = cls.get_user_tags(user_id, include_defaults=True)
        else:
            tags = cls.get_default_tags()

        organized = {}
        for category in TagCategory:
            organized[category.value] = [tag for tag in tags if tag.category == category]

        return organized

    @classmethod
    def get_user_selected_defaults(cls, user_id):
        """Get default tags selected by a specific user"""
        user = User.query.get(user_id)
        return user.selected_default_tags.all() if user else []

    @classmethod
    def create_default_tags(cls):
        """Create Random's trading methodology default tag set with color categories"""
        from app.extensions import db
        from flask import current_app

        # Define tags with their categories and colors
        default_tags_with_colors = {
            TagCategory.SETUP_STRATEGY: [
                # All setup/strategy tags are neutral (blue)
                ("0930 Open", "neutral"),
                ("HOD LOD", "neutral"),
                ("P12", "neutral"),
                ("Captain Backtest", "neutral"),
                ("Quarter Trade", "neutral"),
                ("05 Box", "neutral"),
                ("Three Hour Quarter", "neutral"),
                ("Midnight Open", "neutral"),
                ("Breakout", "neutral"),
                ("Mean Reversion", "neutral"),
            ],

            TagCategory.MARKET_CONDITIONS: [
                # All market condition tags are neutral (blue)
                ("DWP", "neutral"),
                ("DNP", "neutral"),
                ("R1", "neutral"),
                ("R2", "neutral"),
                ("Asian Session", "neutral"),
                ("London Session", "neutral"),
                ("NY1 Session", "neutral"),
                ("NY2 Session", "neutral"),
                ("High Volatility", "neutral"),
                ("Low Volatility", "neutral"),
                ("News Driven", "neutral"),
                ("Extended Target", "neutral"),
            ],

            TagCategory.EXECUTION_MANAGEMENT: [
                # Mixed colors based on performance impact
                ("Front Run", "good"),  # Good execution
                ("Confirmation", "good"),  # Good execution
                ("Retest", "good"),  # Good execution
                ("Chased Entry", "bad"),  # Poor execution
                ("Late Entry", "bad"),  # Poor execution
                ("Proper Stop", "good"),  # Good risk management
                ("Moved Stop", "bad"),  # Poor risk management
                ("Cut Short", "bad"),  # Poor management
                ("Let Run", "good"),  # Good management
                ("Partial Profit", "good"),  # Good management
                ("Limit Order", "neutral"),  # Order type (neutral)
                ("Market Order", "neutral"),  # Order type (neutral)
            ],

            TagCategory.PSYCHOLOGICAL_EMOTIONAL: [
                # Green for positive psychology, red for negative
                ("Disciplined", "good"),  # Positive psychology
                ("Patient", "good"),  # Positive psychology
                ("Calm", "good"),  # Positive psychology
                ("Confident", "good"),  # Positive psychology
                ("Followed Plan", "good"),  # Positive psychology
                ("FOMO", "bad"),  # Negative psychology
                ("Revenge Trading", "bad"),  # Negative psychology
                ("Impulsive", "bad"),  # Negative psychology
                ("Anxious", "bad"),  # Negative psychology
                ("Broke Rules", "bad"),  # Negative psychology
                ("Overconfident", "bad"),  # Negative psychology
            ]
        }

        created_count = 0
        for category, tag_data_list in default_tags_with_colors.items():
            for tag_name, color_category in tag_data_list:
                # Check if tag already exists
                existing = cls.query.filter_by(name=tag_name, is_default=True).first()
                if not existing:
                    new_tag = cls(
                        name=tag_name,
                        category=category,
                        color_category=color_category,  # Set the color category
                        is_default=True,
                        is_active=True
                    )
                    db.session.add(new_tag)
                    created_count += 1
                else:
                    # Update existing tag's color if it's different
                    if existing.color_category != color_category:
                        existing.color_category = color_category
                        created_count += 1  # Count updates too

        if created_count > 0:
            try:
                db.session.commit()
                if current_app:
                    current_app.logger.info(
                        f"Created/updated {created_count} default tags for Random's system with colors")
            except Exception as e:
                db.session.rollback()
                if current_app:
                    current_app.logger.error(f"Error creating default tags: {e}")
                raise

        return created_count

    @classmethod
    def copy_defaults_to_user(cls, user_id):
        """Copy all default tags to a new user's selected defaults"""
        user = User.query.get(user_id)
        if not user:
            return 0

        default_tags = cls.get_default_tags()
        user.selected_default_tags = default_tags
        db.session.commit()

        return len(default_tags)

    def __repr__(self):
        return f'<Tag {self.name} ({self.category.value})>'


# --- Trading Models ---
class TradingModel(db.Model):
    """
    Trading model definitions for Random's system
    Includes: 0930 Open, HOD/LOD, P12, Captain Backtest, etc.
    """
    __tablename__ = 'trading_model'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    version = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Model Logic Fields
    overview_logic = db.Column(db.Text, nullable=True)
    primary_chart_tf = db.Column(db.String(50), nullable=True)
    execution_chart_tf = db.Column(db.String(50), nullable=True)
    context_chart_tf = db.Column(db.String(50), nullable=True)

    # Technical Analysis Fields
    technical_indicators_used = db.Column(db.Text, nullable=True)
    chart_patterns_used = db.Column(db.Text, nullable=True)
    price_action_signals = db.Column(db.Text, nullable=True)
    key_levels_identification = db.Column(db.Text, nullable=True)
    volume_analysis_notes = db.Column(db.Text, nullable=True)
    fundamental_analysis_notes = db.Column(db.Text, nullable=True)

    # Market Context Fields
    instrument_applicability = db.Column(db.Text, nullable=True)
    session_applicability = db.Column(db.Text, nullable=True)
    optimal_market_conditions = db.Column(db.Text, nullable=True)
    sub_optimal_market_conditions = db.Column(db.Text, nullable=True)

    # Entry/Exit Strategy Fields
    entry_trigger_description = db.Column(db.Text, nullable=True)
    stop_loss_strategy = db.Column(db.Text, nullable=True)
    take_profit_strategy = db.Column(db.Text, nullable=True)
    min_risk_reward_ratio = db.Column(db.Float, nullable=True)

    # Position Management Fields
    position_sizing_rules = db.Column(db.Text, nullable=True)
    scaling_in_out_rules = db.Column(db.Text, nullable=True)
    trade_management_breakeven_rules = db.Column(db.Text, nullable=True)
    trade_management_trailing_stop_rules = db.Column(db.Text, nullable=True)
    trade_management_partial_profit_rules = db.Column(db.Text, nullable=True)
    trade_management_adverse_price_action = db.Column(db.Text, nullable=True)

    # Risk Management Fields
    model_max_loss_per_trade = db.Column(db.String(100), nullable=True)
    model_max_daily_loss = db.Column(db.String(100), nullable=True)
    model_max_weekly_loss = db.Column(db.String(100), nullable=True)
    model_consecutive_loss_limit = db.Column(db.String(100), nullable=True)
    model_action_on_max_drawdown = db.Column(db.Text, nullable=True)

    # Execution Fields
    pre_trade_checklist = db.Column(db.Text, nullable=True)
    order_types_used = db.Column(db.Text, nullable=True)
    broker_platform_notes = db.Column(db.Text, nullable=True)
    execution_confirmation_notes = db.Column(db.Text, nullable=True)
    post_trade_routine_model = db.Column(db.Text, nullable=True)

    # Model Assessment Fields
    strengths = db.Column(db.Text, nullable=True)
    weaknesses = db.Column(db.Text, nullable=True)
    backtesting_forwardtesting_notes = db.Column(db.Text, nullable=True)
    refinements_learnings = db.Column(db.Text, nullable=True)

    # Meta Fields
    created_at = db.Column(db.DateTime, default=dt.utcnow)
    updated_at = db.Column(db.DateTime, default=dt.utcnow, onupdate=dt.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_tradingmodel_user'), nullable=False, index=True)

    # Add these fields after the existing fields in TradingModel class
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_by_admin_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Add this new relationship
    created_by_admin = db.relationship('User',
                                       foreign_keys=[created_by_admin_user_id],
                                       backref='created_default_models')

    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='uq_user_tradingmodel_name'),)

    def __repr__(self):
        return f"<TradingModel '{self.name}' (User: {self.user_id})>"

    @classmethod
    def get_default_models(cls):
        """Get all default trading models"""
        return cls.query.filter_by(is_default=True, is_active=True).order_by(cls.name).all()

    @classmethod
    def get_available_for_user(cls, user_id):
        """Get all models available to a specific user (default + personal)"""
        return cls.query.filter(
            db.or_(
                cls.is_default == True,
                cls.user_id == user_id
            )
        ).filter(cls.is_active == True).order_by(cls.name).all()


# --- Trade Related Models ---
class TradeImage(db.Model):
    """Trade screenshot and chart images"""
    __tablename__ = 'trade_image'
    id = db.Column(db.Integer, primary_key=True)
    trade_id = db.Column(db.Integer, db.ForeignKey('trade.id', name='fk_tradeimage_trade'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_tradeimage_user'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False, unique=True)
    filesize = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=True)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    caption = db.Column(db.String(255), nullable=True)
    uploader = db.relationship('User', backref='uploaded_trade_images', lazy=True)

    @property
    def full_disk_path(self):
        upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.instance_path, 'uploads'))
        return os.path.join(upload_folder, self.filepath)

    def __repr__(self):
        return f'<TradeImage {self.filename} for Trade ID {self.trade_id}>'


class Trade(db.Model):
    """
    Core Trade model for Random's trading journal
    Supports his Four Steps methodology and trading models
    """
    __tablename__ = 'trade'
    id = db.Column(db.Integer, primary_key=True)

    # Instrument fields (consolidated approach)
    instrument_id = db.Column(db.Integer, db.ForeignKey('instrument.id', name='fk_trade_instrument'), nullable=True)
    instrument_obj = db.relationship('Instrument', back_populates='trades')
    instrument_legacy = db.Column(db.String(20), nullable=True, index=True)  # Backward compatibility
    point_value = db.Column(db.Float, nullable=True)  # Direct storage for manual overrides
    pnl = db.Column(db.Float, nullable=True, index=True)  # Stored P&L for fast filtering

    # Basic trade information
    trade_date = db.Column(db.Date, nullable=False, default=py_date.today)
    direction = db.Column(db.String(5), nullable=False)  # Long/Short
    initial_stop_loss = db.Column(db.Float, nullable=True)
    terminus_target = db.Column(db.Float, nullable=True)
    is_dca = db.Column(db.Boolean, default=False)

    # Performance metrics
    mae = db.Column(db.Float, nullable=True)  # Maximum Adverse Excursion
    mfe = db.Column(db.Float, nullable=True)  # Maximum Favorable Excursion

    # Trade management and notes
    trade_notes = db.Column(db.Text, nullable=True)
    how_closed = db.Column(db.String(20), nullable=True)
    news_event = db.Column(db.String(100), nullable=True)

    # Scoring (1-5 scale for Random's system)
    rules_rating = db.Column(db.Integer, nullable=True)
    management_rating = db.Column(db.Integer, nullable=True)
    target_rating = db.Column(db.Integer, nullable=True)
    entry_rating = db.Column(db.Integer, nullable=True)
    preparation_rating = db.Column(db.Integer, nullable=True)

    # Psychology notes
    psych_scored_highest = db.Column(db.Text, nullable=True)
    psych_scored_lowest = db.Column(db.Text, nullable=True)

    # Analysis fields
    overall_analysis_notes = db.Column(db.Text, nullable=True)
    screenshot_link = db.Column(db.String(255), nullable=True)
    trade_management_notes = db.Column(db.Text, nullable=True)
    errors_notes = db.Column(db.Text, nullable=True)
    improvements_notes = db.Column(db.Text, nullable=True)
    tags = db.relationship('Tag', secondary=trade_tags, lazy='subquery',
                           backref=db.backref('trades', lazy=True))

    # Relationships
    trading_model_id = db.Column(db.Integer, db.ForeignKey('trading_model.id', name='fk_trade_trading_model'),
                                 nullable=True)
    trading_model = db.relationship('TradingModel', backref=db.backref('trades', lazy='dynamic'))
    entries = db.relationship('EntryPoint', backref='trade', lazy='dynamic', cascade="all, delete-orphan")
    exits = db.relationship('ExitPoint', backref='trade', lazy='dynamic', cascade="all, delete-orphan")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_trade_user'), nullable=False, index=True)
    images = db.relationship('TradeImage', backref='trade', lazy='dynamic', cascade="all, delete-orphan")

    @property
    def instrument(self):
        """Get instrument symbol - checks new relationship first, then legacy field"""
        if self.instrument_obj:
            return self.instrument_obj.symbol
        return self.instrument_legacy

    @instrument.setter
    def instrument(self, value):
        """Set instrument by symbol - tries to find in Instrument table first"""
        if isinstance(value, str):
            instr = Instrument.query.filter_by(symbol=value.upper(), is_active=True).first()
            if instr:
                self.instrument_id = instr.id
                self.instrument_legacy = None
            else:
                self.instrument_legacy = value.upper()
                self.instrument_id = None

    @property
    def point_value_safe(self):
        """
        Consolidated point value logic - single source of truth from the database.
        Priority: 1) Manual override on the trade, 2) Instrument table value.
        Returns None if no instrument is linked and no override is set.
        """
        # Check for manual override first
        if self.point_value is not None and self.point_value > 0:
            return self.point_value

        # Try to get from the instrument relationship
        if self.instrument_obj and hasattr(self.instrument_obj, 'point_value'):
            return self.instrument_obj.point_value

        # If no override and no linked instrument, there is no valid point value
        return None

    @property
    def total_contracts_entered(self):
        if not self.entries:
            return 0
        return sum(entry.contracts for entry in self.entries if entry.contracts is not None)

    @property
    def average_entry_price(self):
        total_contracts = self.total_contracts_entered
        if not total_contracts or total_contracts == 0:
            return None
        total_value = sum(entry.contracts * entry.entry_price for entry in self.entries
                          if entry.contracts is not None and entry.entry_price is not None)
        return total_value / total_contracts

    @property
    def total_contracts_exited(self):
        if not self.exits:
            return 0
        return sum(exit_point.contracts for exit_point in self.exits if exit_point.contracts is not None)

    @property
    def average_exit_price(self):
        total_exited = self.total_contracts_exited
        if not total_exited or total_exited == 0:
            return None
        total_exit_value = sum(exit_point.contracts * exit_point.exit_price for exit_point in self.exits
                               if exit_point.contracts is not None and exit_point.exit_price is not None)
        return total_exit_value / total_exited

    @property
    def gross_pnl(self):
        """Calculate gross P&L using consolidated point value logic"""
        avg_entry = self.average_entry_price
        avg_exit = self.average_exit_price
        contracts_exited = self.total_contracts_exited
        pv = self.point_value_safe

        # If point value could not be determined, PnL is zero.
        if pv is None or pv == 0:
            return 0.0

        if avg_entry is None or avg_exit is None or contracts_exited == 0:
            return 0.0

        pnl_per_contract_in_points = 0.0
        if self.direction == "Long":
            pnl_per_contract_in_points = avg_exit - avg_entry
        elif self.direction == "Short":
            pnl_per_contract_in_points = avg_entry - avg_exit

        return pnl_per_contract_in_points * contracts_exited * pv

    def calculate_and_store_pnl(self):
        """Calculate P&L and store it in the pnl column for fast database filtering"""
        calculated_pnl = self.gross_pnl  # Use the existing property calculation
        self.pnl = calculated_pnl
        return calculated_pnl

    @property
    def risk_reward_ratio(self):
        avg_entry = self.average_entry_price
        sl = self.initial_stop_loss
        tp = self.terminus_target
        if avg_entry is None or sl is None or tp is None or sl == avg_entry:
            return None
        potential_risk_per_contract = abs(avg_entry - sl)
        potential_reward_per_contract = abs(tp - avg_entry)
        return potential_reward_per_contract / potential_risk_per_contract if potential_risk_per_contract > 0 else None

    @property
    def time_in_trade(self):
        if not self.entries.first():
            return "N/A"
        first_entry_obj = self.entries.order_by(EntryPoint.entry_time).first()
        if not first_entry_obj or not first_entry_obj.entry_time:
            return "Open"
        min_entry_datetime = datetime.combine(self.trade_date, first_entry_obj.entry_time)
        last_exit_obj = self.exits.order_by(ExitPoint.exit_time.desc()).first()
        if not last_exit_obj or not last_exit_obj.exit_time:
            return "Open"
        max_exit_datetime = datetime.combine(self.trade_date, last_exit_obj.exit_time)
        if max_exit_datetime >= min_entry_datetime:
            duration = max_exit_datetime - min_entry_datetime
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours:02d}h {minutes:02d}m"
        return "N/A (Exit before Entry?)"

    @property
    def dollar_risk(self):
        first_entry = self.entries.order_by(EntryPoint.entry_time).first()
        sl = self.initial_stop_loss
        pv = self.point_value_safe

        if not first_entry or sl is None or pv is None or pv == 0:
            return None

        entry_price = first_entry.entry_price
        contracts = first_entry.contracts
        risk_per_contract_in_points = 0.0

        if self.direction == "Long":
            risk_per_contract_in_points = entry_price - sl
        elif self.direction == "Short":
            risk_per_contract_in_points = sl - entry_price

        return risk_per_contract_in_points * contracts * pv if risk_per_contract_in_points > 0 else 0.0

    @property
    def pnl_in_r(self):
        initial_risk_dollars = self.dollar_risk
        pnl_dollars = self.gross_pnl
        if initial_risk_dollars is None or initial_risk_dollars == 0 or pnl_dollars is None:
            return None
        if self.total_contracts_exited > 0 and self.how_closed not in ["Still Open", None, '']:
            return pnl_dollars / initial_risk_dollars
        return None

    def __repr__(self):
        return f"<Trade {self.id} {self.instrument} on {self.trade_date} (User: {self.user_id})>"

    @property
    def entry_timestamp(self):
        """
        Returns the full timestamp of the first entry for a trade.
        Combines the trade_date with the earliest entry_time.
        """
        if not self.entries.first():
            return None  # Or return a default datetime

        # Get the first entry, ordered by time
        first_entry = self.entries.order_by(EntryPoint.entry_time).first()

        if not first_entry or not first_entry.entry_time:
            return None  # Or handle as needed

        # Combine the trade date with the entry time
        from datetime import datetime
        return datetime.combine(self.trade_date, first_entry.entry_time)

    @property
    def images(self):
        """Get all images for this trade."""
        return GlobalImage.get_for_entity('trade', self.id)


class EntryPoint(db.Model):
    """Entry points for trades - supports multiple entries"""
    __tablename__ = 'entry_point'
    id = db.Column(db.Integer, primary_key=True)
    entry_time = db.Column(db.Time, nullable=False)
    contracts = db.Column(db.Integer, nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    trade_id = db.Column(db.Integer, db.ForeignKey('trade.id', name='fk_entrypoint_trade'), nullable=False)

    def __repr__(self):
        return f"<EntryPoint ID: {self.id} for Trade ID: {self.trade_id} ({self.contracts} @ {self.entry_price})>"


class ExitPoint(db.Model):
    """Exit points for trades - supports partial exits"""
    __tablename__ = 'exit_point'
    id = db.Column(db.Integer, primary_key=True)
    exit_time = db.Column(db.Time, nullable=True)
    contracts = db.Column(db.Integer, nullable=True)
    exit_price = db.Column(db.Float, nullable=True)
    trade_id = db.Column(db.Integer, db.ForeignKey('trade.id', name='fk_exitpoint_trade'), nullable=False)

    def __repr__(self):
        return f"<ExitPoint ID: {self.id} for Trade ID: {self.trade_id} ({self.contracts} @ {self.exit_price})>"


# --- Journal Models for Random's System ---
class DailyJournalImage(db.Model):
    """Images for daily journal entries"""
    __tablename__ = 'daily_journal_image'
    id = db.Column(db.Integer, primary_key=True)
    daily_journal_id = db.Column(db.Integer, db.ForeignKey('daily_journal.id', name='fk_dailyjournalimage_journal'),
                                 nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_dailyjournalimage_user'), nullable=False,
                        index=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False, unique=True)
    filesize = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=True)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    image_type = db.Column(db.String(50), nullable=True)  # e.g., 'pre_market_analysis', 'eod_chart'
    caption = db.Column(db.String(255), nullable=True)
    uploader = db.relationship('User', backref='uploaded_daily_journal_images', lazy=True)

    @property
    def full_disk_path(self):
        upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.instance_path, 'uploads'))
        return os.path.join(upload_folder, self.filepath)

    def __repr__(self):
        return f'<DailyJournalImage {self.filename} for Journal ID {self.daily_journal_id}>'


class DailyJournal(db.Model):
    """
    Daily Journal for Random's Four Steps methodology
    Supports P12 analysis, session tracking, and mental state tracking
    """
    __tablename__ = 'daily_journal'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_dailyjournal_user'), nullable=False, index=True)
    journal_date = db.Column(db.Date, nullable=False)

    # Part 1: Pre-market Preparation (Mental State)
    key_events_today = db.Column(db.Text, nullable=True)
    key_tasks_today = db.Column(db.Text, nullable=True)
    on_my_mind = db.Column(db.Text, nullable=True)
    important_focus_today = db.Column(db.Text, nullable=True)
    mental_feeling_rating = db.Column(db.Integer, nullable=True)  # 1-5
    mental_mind_rating = db.Column(db.Integer, nullable=True)  # 1-5 (Clarity/Focus)
    mental_energy_rating = db.Column(db.Integer, nullable=True)  # 1-5
    mental_motivation_rating = db.Column(db.Integer, nullable=True)  # 1-5

    # Part 2: Pre-market Analysis (Four Steps & P12)
    p12_scenario_selected = db.Column(db.String(10), default="None")
    p12_expected_outcomes = db.Column(db.Text, nullable=True)
    p12_scenario_id = db.Column(db.Integer, db.ForeignKey('p12_scenario.id'), nullable=True)
    p12_scenario = db.relationship('P12Scenario', backref='daily_journals', lazy=True)

    # P12 Levels (optional reference data)
    p12_high = db.Column(db.Numeric(10, 2), nullable=True)
    p12_mid = db.Column(db.Numeric(10, 2), nullable=True)
    p12_low = db.Column(db.Numeric(10, 2), nullable=True)
    p12_notes = db.Column(db.Text, nullable=True)

    # Session Analysis (Asia, London, NY1, NY2)
    asia_direction = db.Column(db.String(10), default="None")
    asia_session_status = db.Column(db.String(10), default="None")  # True/False/Broken
    asia_model_status = db.Column(db.String(10), default="None")  # Valid/Broken (OU midline)
    asia_actual_range_points = db.Column(db.Float, nullable=True)
    asia_actual_range_percentage = db.Column(db.Float, nullable=True)
    asia_median_range_input_note = db.Column(db.Text, nullable=True)

    london_direction = db.Column(db.String(10), default="None")
    london_session_status = db.Column(db.String(10), default="None")
    london_model_status = db.Column(db.String(10), default="None")
    london_actual_range_points = db.Column(db.Float, nullable=True)
    london_actual_range_percentage = db.Column(db.Float, nullable=True)
    london_median_range_input_note = db.Column(db.Text, nullable=True)

    ny1_direction = db.Column(db.String(10), default="None")
    ny1_session_status = db.Column(db.String(10), default="None")
    ny1_model_status = db.Column(db.String(10), default="None")
    ny1_actual_range_points = db.Column(db.Float, nullable=True)
    ny1_actual_range_percentage = db.Column(db.Float, nullable=True)
    ny1_median_range_input_note = db.Column(db.Text, nullable=True)

    ny2_direction = db.Column(db.String(10), default="None")
    ny2_session_status = db.Column(db.String(10), default="None")
    ny2_model_status = db.Column(db.String(10), default="None")
    ny2_actual_range_points = db.Column(db.Float, nullable=True)
    ny2_actual_range_percentage = db.Column(db.Float, nullable=True)
    ny2_median_range_input_note = db.Column(db.Text, nullable=True)

    # HOD/LOD Projection Fields (Wargaming - condensed for space)
    # Note: In production, you'd want all 64 wg_ fields from your original model
    # This is a condensed version showing the pattern
    wg_ny1_lt_notes = db.Column(db.Text, nullable=True)
    wg_ny1_lt_hod_pct_l = db.Column(db.Float, nullable=True)
    wg_ny1_lt_hod_pct_h = db.Column(db.Float, nullable=True)
    wg_ny1_lt_hod_ts = db.Column(db.Time, nullable=True)
    wg_ny1_lt_hod_te = db.Column(db.Time, nullable=True)

    # Add remaining wg_ fields as needed...
    # [Additional wg_ fields would go here - truncated for brevity]

    # Step 3: Realistic Expectance
    adr_10_day_median_range_value = db.Column(db.Float, nullable=True)
    todays_total_range_points = db.Column(db.Float, nullable=True)
    todays_total_range_percentage = db.Column(db.Float, nullable=True)
    realistic_expectance_notes = db.Column(db.Text, nullable=True)

    # Step 4: Engagement Structure
    engagement_structure_notes = db.Column(db.Text, nullable=True)
    key_levels_notes = db.Column(db.Text, nullable=True)
    pre_market_news_notes = db.Column(db.Text, nullable=True)

    # Part 3: Post Market Analysis
    market_observations = db.Column(db.Text, nullable=True)
    self_observations = db.Column(db.Text, nullable=True)

    # Part 4: Daily Review and Reflection
    did_well_today = db.Column(db.Text, nullable=True)
    did_not_go_well_today = db.Column(db.Text, nullable=True)
    learned_today = db.Column(db.Text, nullable=True)
    improve_action_next_day = db.Column(db.Text, nullable=True)

    # Daily Psychology Review (1-5 scale)
    review_psych_discipline_rating = db.Column(db.Integer, nullable=True)
    review_psych_motivation_rating = db.Column(db.Integer, nullable=True)
    review_psych_focus_rating = db.Column(db.Integer, nullable=True)
    review_psych_mastery_rating = db.Column(db.Integer, nullable=True)
    review_psych_composure_rating = db.Column(db.Integer, nullable=True)
    review_psych_resilience_rating = db.Column(db.Integer, nullable=True)
    review_psych_mind_rating = db.Column(db.Integer, nullable=True)
    review_psych_energy_rating = db.Column(db.Integer, nullable=True)

    # Relationships
    images = db.relationship('DailyJournalImage', backref='daily_journal', lazy='dynamic', cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (db.UniqueConstraint('user_id', 'journal_date', name='uq_user_daily_journal_date'),)

    @property
    def images(self):
        """Get all images for this daily journal."""
        return GlobalImage.get_for_entity('daily_journal', self.id)

    @property
    def average_review_psych_rating(self):
        ratings = [
            self.review_psych_discipline_rating, self.review_psych_motivation_rating,
            self.review_psych_focus_rating, self.review_psych_mastery_rating,
            self.review_psych_composure_rating, self.review_psych_resilience_rating,
            self.review_psych_mind_rating, self.review_psych_energy_rating
        ]
        valid_ratings = [r for r in ratings if r is not None and isinstance(r, (int, float)) and 1 <= r <= 5]
        if not valid_ratings:
            return None
        return statistics.mean(valid_ratings)

    def __repr__(self):
        return f"<DailyJournal for {self.journal_date} (User: {self.user_id})>"


class WeeklyJournal(db.Model):
    """Weekly journal for longer-term reflection"""
    __tablename__ = 'weekly_journal'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    week_number = db.Column(db.Integer, nullable=False)
    weekly_improve_action_next_week = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_weeklyjournal_user'), nullable=False, index=True)

    __table_args__ = (db.UniqueConstraint('user_id', 'year', 'week_number', name='uq_user_year_week'),)

    @property
    def week_start_date_display(self):
        try:
            return py_date.fromisocalendar(self.year, self.week_number, 1).strftime('%d %b %Y')
        except ValueError:
            return "Invalid Week/Year"

    def __repr__(self):
        return f"<WeeklyJournal {self.year}-W{self.week_number:02d} (User: {self.user_id})>"


class MonthlyJournal(db.Model):
    """Monthly journal for strategic reflection"""
    __tablename__ = 'monthly_journal'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    coach_feedback_on_month = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_monthlyjournal_user'), nullable=False, index=True)

    __table_args__ = (db.UniqueConstraint('user_id', 'year', 'month', name='uq_user_year_month'),)

    @property
    def month_year_display(self):
        try:
            return py_date(self.year, self.month, 1).strftime('%B %Y')
        except ValueError:
            return f"Invalid Date {self.year}-{self.month}"

    def __repr__(self):
        return f"<MonthlyJournal {self.year}-{self.month:02d} (User: {self.user_id})>"


class QuarterlyJournal(db.Model):
    """Quarterly journal for business planning"""
    __tablename__ = 'quarterly_journal'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    quarter = db.Column(db.Integer, nullable=False)  # 1-4
    key_goals_for_quarter = db.Column(db.Text, nullable=True)
    major_focus_areas_strategies = db.Column(db.Text, nullable=True)
    anticipated_challenges_mitigation = db.Column(db.Text, nullable=True)
    quarterly_achievements_progress = db.Column(db.Text, nullable=True)
    what_went_well_quarter = db.Column(db.Text, nullable=True)
    what_did_not_go_well_quarter = db.Column(db.Text, nullable=True)
    key_lessons_learned_quarter = db.Column(db.Text, nullable=True)
    adjustments_for_next_quarter = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_quarterlyjournal_user'), nullable=False,
                        index=True)

    __table_args__ = (db.UniqueConstraint('user_id', 'year', 'quarter', name='uq_user_year_quarter'),)

    @property
    def quarter_display_name(self):
        return QUARTER_NAMES[self.quarter] if self.quarter and 1 <= self.quarter <= 4 else "Invalid Quarter"

    def __repr__(self):
        return f"<QuarterlyJournal {self.year}-Q{self.quarter} (User: {self.user_id})>"


class YearlyJournal(db.Model):
    """Yearly journal for long-term vision and planning"""
    __tablename__ = 'yearly_journal'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    yearly_long_term_vision = db.Column(db.Text, nullable=True)
    yearly_key_goals = db.Column(db.Text, nullable=True)
    yearly_major_focus_areas = db.Column(db.Text, nullable=True)
    yearly_coach_advice_for_year_ahead = db.Column(db.Text, nullable=True)
    yearly_achievements = db.Column(db.Text, nullable=True)
    yearly_challenges_overcome = db.Column(db.Text, nullable=True)
    yearly_lessons_learned = db.Column(db.Text, nullable=True)
    yearly_goals_for_next_year = db.Column(db.Text, nullable=True)
    yearly_coach_feedback_on_year = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_yearlyjournal_user'), nullable=False, index=True)

    __table_args__ = (db.UniqueConstraint('user_id', 'year', name='uq_user_year'),)

    def __repr__(self):
        return f"<YearlyJournal for {self.year} (User: {self.user_id})>"


# --- Supporting Models ---
class NewsEventItem(db.Model):
    """News events that can affect trading"""
    __tablename__ = 'news_event_item'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    default_release_time = db.Column(db.Time, nullable=True)

    def __repr__(self):
        return f"<NewsEventItem '{self.name}'>"


class AccountSetting(db.Model):
    """Global account settings"""
    __tablename__ = 'account_setting'
    id = db.Column(db.Integer, primary_key=True)
    setting_name = db.Column(db.String(100), unique=True, nullable=False)
    value_str = db.Column(db.String(255), nullable=True)
    value_int = db.Column(db.Integer, nullable=True)
    value_float = db.Column(db.Float, nullable=True)
    value_bool = db.Column(db.Boolean, nullable=True)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<AccountSetting '{self.setting_name}'>"


class TagUsageStats(db.Model):
    """Track tag usage patterns for analytics and AI suggestions"""
    __tablename__ = 'tag_usage_stats'

    id = db.Column(db.Integer, primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tag.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    usage_count = db.Column(db.Integer, nullable=False, default=0)
    last_used = db.Column(db.DateTime, nullable=True)
    first_used = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    tag = db.relationship('Tag', backref='usage_stats')
    user = db.relationship('User', backref='tag_usage_stats')

    __table_args__ = (
        db.UniqueConstraint('tag_id', 'user_id', name='unique_tag_user_usage'),
    )

    @classmethod
    def record_tag_usage(cls, user_id, tag_ids):
        """
        Record or update tag usage statistics
        This method now ensures usage_count always matches actual trade count
        """
        for tag_id in tag_ids:
            # Get existing record or create new one
            usage_stat = cls.query.filter_by(user_id=user_id, tag_id=tag_id).first()

            if usage_stat:
                # Update last used time
                usage_stat.last_used = datetime.utcnow()
                usage_stat.updated_at = datetime.utcnow()

                # Recalculate actual usage count from trades
                from app.models import Trade
                actual_count = (Trade.query
                                .filter(Trade.user_id == user_id)
                                .filter(Trade.tags.any(Tag.id == tag_id))
                                .count())
                usage_stat.usage_count = actual_count
            else:
                # Create new record
                from app.models import Trade
                actual_count = (Trade.query
                                .filter(Trade.user_id == user_id)
                                .filter(Trade.tags.any(Tag.id == tag_id))
                                .count())

                usage_stat = cls(
                    user_id=user_id,
                    tag_id=tag_id,
                    usage_count=actual_count,
                    last_used=datetime.utcnow(),
                    first_used=datetime.utcnow()
                )
                db.session.add(usage_stat)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    @classmethod
    def cleanup_unused_stats(cls, user_id):
        """Remove usage stats for tags that are no longer on any trades"""
        # Get all usage stats for this user
        all_stats = cls.query.filter_by(user_id=user_id).all()

        for stat in all_stats:
            # Check if any trades still have this tag
            from app.models import Trade
            trade_count = (Trade.query
                           .filter(Trade.user_id == user_id)
                           .filter(Trade.tags.any(Tag.id == stat.tag_id))
                           .count())

            if trade_count == 0:
                # No trades have this tag anymore, remove the stat
                db.session.delete(stat)
            else:
                # Update the count to be accurate
                stat.usage_count = trade_count

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    @classmethod
    def get_user_most_used_tags(cls, user_id, limit=10):
        """Get user's most frequently used tags"""
        return (cls.query
                .filter_by(user_id=user_id)
                .join(Tag)
                .filter(Tag.is_active == True)
                .order_by(cls.usage_count.desc(), cls.last_used.desc())
                .limit(limit)
                .all())

    @classmethod
    def get_recently_used_tags(cls, user_id, days=30, limit=10):
        """Get tags used recently"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        return (cls.query
                .filter_by(user_id=user_id)
                .filter(cls.last_used >= cutoff_date)
                .join(Tag)
                .filter(Tag.is_active == True)
                .order_by(cls.last_used.desc())
                .limit(limit)
                .all())


class P12Scenario(db.Model):
    """
    P12 Scenarios based on Random's (Matt Mickey) methodology.
    Defines the 5 core P12 scenarios that occur between 06:00-08:30 EST.
    """
    __tablename__ = 'p12_scenario'

    id = db.Column(db.Integer, primary_key=True)
    scenario_number = db.Column(db.String(5), nullable=False, unique=True)
    scenario_name = db.Column(db.String(100), nullable=False, unique=True)
    short_description = db.Column(db.String(200), nullable=False)
    detailed_description = db.Column(db.Text, nullable=False)

    # Trading implications
    hod_lod_implication = db.Column(db.Text, nullable=False)  # Where HOD/LOD likely is
    directional_bias = db.Column(db.String(50), nullable=True)  # bullish/bearish/neutral/choppy

    # Alert and confirmation criteria
    alert_criteria = db.Column(db.Text, nullable=False)  # What to watch for
    confirmation_criteria = db.Column(db.Text, nullable=False)  # How to confirm scenario

    # Entry strategies
    entry_strategy = db.Column(db.Text, nullable=False)  # How to trade this scenario
    typical_targets = db.Column(db.Text, nullable=True)  # Common target areas

    # Risk management
    stop_loss_guidance = db.Column(db.Text, nullable=True)
    risk_percentage = db.Column(db.Float, nullable=True)  # 0.35, 0.50 etc.

    # Image and visual aids
    image_filename = db.Column(db.String(255), nullable=True)
    image_path = db.Column(db.String(500), nullable=True)

    # Metadata
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_date = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Trading Model Recommendations
    models_to_activate = db.Column(db.JSON, nullable=True)  # List of model names to activate
    models_to_avoid = db.Column(db.JSON, nullable=True)  # List of model names to avoid
    risk_guidance = db.Column(db.Text, nullable=True)  # Risk percentage guidance text

    # Additional trading guidance
    preferred_timeframes = db.Column(db.JSON, nullable=True)  # List of preferred timeframes
    key_considerations = db.Column(db.Text, nullable=True)  # Additional trading considerations

    # Usage tracking
    times_selected = db.Column(db.Integer, default=0, nullable=False)  # How often users select this

    def __repr__(self):
        return f'<P12Scenario {self.scenario_number}: {self.scenario_name}>'

    @property
    def full_image_path(self):
        """Get the full path to the scenario image."""
        if self.image_path:
            from flask import current_app
            upload_folder = current_app.config.get('UPLOAD_FOLDER',
                                                   os.path.join(current_app.instance_path, 'uploads'))
            return os.path.join(upload_folder, 'p12_scenarios', self.image_path)
        return None

    def increment_usage(self):
        """Track when this scenario is selected by users."""
        self.times_selected += 1
        db.session.commit()

    @property
    def images(self):
        """Get all images for this P12 scenario."""
        return GlobalImage.get_for_entity('p12_scenario', self.id)

    @property
    def primary_image(self):
        """Get the primary/first image for this scenario."""
        images = self.images
        return images[0] if images else None

# Add this to app/models.py

class P12UsageStats(db.Model):
    """
    Track detailed usage statistics for P12 scenarios.
    Provides analytics on which scenarios are most popular, when they're used, etc.
    """
    __tablename__ = 'p12_usage_stats'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    p12_scenario_id = db.Column(db.Integer, db.ForeignKey('p12_scenario.id'), nullable=False)
    journal_date = db.Column(db.Date, nullable=False)  # Date scenario was used
    selection_timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Context information
    market_session = db.Column(db.String(50), nullable=True)  # 'pre-market', 'opening', 'midday', etc.
    p12_high = db.Column(db.Numeric(10, 2), nullable=True)  # P12 levels when selected
    p12_mid = db.Column(db.Numeric(10, 2), nullable=True)
    p12_low = db.Column(db.Numeric(10, 2), nullable=True)

    # Outcome tracking (can be updated later)
    outcome_successful = db.Column(db.Boolean, nullable=True)  # Did the scenario play out as expected?
    outcome_notes = db.Column(db.Text, nullable=True)  # User's notes on how it played out

    # Relationships
    user = db.relationship('User', backref=db.backref('p12_usage_stats', lazy='dynamic'))
    scenario = db.relationship('P12Scenario', backref=db.backref('usage_stats', lazy='dynamic'))

    def __repr__(self):
        return f'<P12UsageStats User={self.user_id} Scenario={self.p12_scenario_id} Date={self.journal_date}>'

    @staticmethod
    def get_most_popular_scenarios(user_id=None, days=30):
        """Get most popular P12 scenarios in the last N days."""
        from sqlalchemy import func
        from datetime import date, timedelta

        cutoff_date = date.today() - timedelta(days=days)
        query = db.session.query(
            P12UsageStats.p12_scenario_id,
            func.count(P12UsageStats.id).label('usage_count'),
            P12Scenario.scenario_number,
            P12Scenario.scenario_name
        ).join(P12Scenario).filter(
            P12UsageStats.journal_date >= cutoff_date
        )

        if user_id:
            query = query.filter(P12UsageStats.user_id == user_id)

        return query.group_by(
            P12UsageStats.p12_scenario_id,
            P12Scenario.scenario_number,
            P12Scenario.scenario_name
        ).order_by(func.count(P12UsageStats.id).desc()).all()

    @staticmethod
    def get_user_scenario_history(user_id, scenario_id=None, limit=10):
        """Get recent usage history for a user, optionally filtered by scenario."""
        query = P12UsageStats.query.filter_by(user_id=user_id)

        if scenario_id:
            query = query.filter_by(p12_scenario_id=scenario_id)

        return query.order_by(P12UsageStats.selection_timestamp.desc()).limit(limit).all()

    @staticmethod
    def get_success_rate(scenario_id, user_id=None, days=90):
        """Calculate success rate for a scenario."""
        from sqlalchemy import func
        from datetime import date, timedelta

        cutoff_date = date.today() - timedelta(days=days)
        query = P12UsageStats.query.filter(
            P12UsageStats.p12_scenario_id == scenario_id,
            P12UsageStats.journal_date >= cutoff_date,
            P12UsageStats.outcome_successful.isnot(None)  # Only count where outcome was recorded
        )

        if user_id:
            query = query.filter(P12UsageStats.user_id == user_id)

        total_with_outcome = query.count()
        successful = query.filter(P12UsageStats.outcome_successful == True).count()

        if total_with_outcome == 0:
            return None  # No data available

        return (successful / total_with_outcome) * 100  # Return percentage


class GlobalImage(db.Model):
    """Global image model for all entities in the application."""
    __tablename__ = 'global_image'

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(50), nullable=False, index=True)
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    relative_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=True)

    image_width = db.Column(db.Integer, nullable=True)
    image_height = db.Column(db.Integer, nullable=True)
    has_thumbnail = db.Column(db.Boolean, default=False, nullable=False)
    thumbnail_path = db.Column(db.String(500), nullable=True)

    upload_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    caption = db.Column(db.String(500), nullable=True)
    image_type = db.Column(db.String(50), nullable=True)
    is_optimized = db.Column(db.Boolean, default=False, nullable=False)

    view_count = db.Column(db.Integer, default=0, nullable=False)
    last_accessed = db.Column(db.DateTime, nullable=True)

    # Relationships
    uploader = db.relationship('User', backref='uploaded_images', lazy=True)

    def __repr__(self):
        return f'<GlobalImage {self.filename} for {self.entity_type}:{self.entity_id}>'

    @classmethod
    def get_for_entity(cls, entity_type, entity_id):
        """Get all images for a specific entity."""
        return cls.query.filter_by(entity_type=entity_type, entity_id=entity_id).order_by(cls.upload_date.desc()).all()

