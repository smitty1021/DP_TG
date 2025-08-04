from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, PasswordField, BooleanField, SubmitField, MultipleFileField,
                     TextAreaField, FloatField, SelectField, IntegerField, DateField,
                     TimeField, FormField, FieldList, SelectMultipleField, DecimalField)  # <-- Add DecimalField here
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange, InputRequired
from app.models import UserRole  # Assuming UserRole is used elsewhere or for consistency
from app.models import TagCategory
from wtforms.fields import SelectMultipleField
from app.models import P12Scenario




class OptGroupSelectMultipleField(SelectMultipleField):
    """Custom SelectMultipleField that handles optgroups correctly with tag colors"""

    def iter_choices(self):
        """Iterate over choices, flattening optgroups for validation"""
        for choice in self.choices:
            if isinstance(choice, (list, tuple)) and len(choice) == 2:
                # Check if this is an optgroup (group_label, [(value, label, color), ...])
                group_label, group_choices = choice
                if isinstance(group_choices, (list, tuple)) and group_choices:
                    # This is an optgroup, yield individual choices
                    for choice_item in group_choices:
                        if isinstance(choice_item, (list, tuple)):
                            if len(choice_item) >= 3:
                                # Format: (value, label, color)
                                value, label, color = choice_item[0], choice_item[1], choice_item[2]
                                yield (value, label, value in (self.data or []))
                            elif len(choice_item) == 2:
                                # Format: (value, label)
                                value, label = choice_item
                                yield (value, label, value in (self.data or []))
                        else:
                            # Single item
                            yield (choice_item, choice_item, choice_item in (self.data or []))
                else:
                    # This is a regular choice (value, label)
                    yield (choice[0], choice[1], choice[0] in (self.data or []))
            else:
                # Fallback for other choice formats
                yield (choice, choice, choice in (self.data or []))

# Custom coerce function for optional integer select fields
def coerce_int_optional(value):
    if value == '':
        return None
    try:
        return int(value)
    except ValueError:
        return None


# --- Authentication and User-Related Forms ---
class LoginForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=4, max=80)],
                           render_kw={"placeholder": "Enter your username"})
    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=6)],
                             render_kw={"placeholder": "Enter your password"})
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(message="Username is required."),
                                       Length(min=3, max=25, message="Username must be between 3 and 25 characters.")])
    email = StringField('Email',
                        validators=[DataRequired(message="Email is required."),
                                    Email(message="Please enter a valid email address.")])
    password = PasswordField('Password',
                             validators=[DataRequired(message="Password is required."),
                                         Length(min=8, message="Password must be at least 8 characters long.")])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(message="Please confirm your password."),
                                                 EqualTo('password', message="Passwords must match.")])
    submit = SubmitField('Register')


class ResendVerificationForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(message="Email is required."),
                                    Email(message="Please enter a valid email address.")],
                        render_kw={"placeholder": "Enter your registered email address"})
    submit = SubmitField('Resend Verification Email')


class RequestPasswordResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(message="Email is required."),
                                    Email(message="Please enter a valid email address.")],
                        render_kw={"placeholder": "Enter your account's email address"})
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password',
                             validators=[DataRequired(message="Password is required."),
                                         Length(min=8, message="Password must be at least 8 characters long.")])
    confirm_password = PasswordField('Confirm New Password',
                                     validators=[DataRequired(message="Please confirm your new password."),
                                                 EqualTo('password', message="Passwords must match.")])
    submit = SubmitField('Reset Password')


class ProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[Optional(), Length(max=100)])
    email = StringField('Email Address',
                        validators=[DataRequired(), Email(message="Invalid email address."), Length(max=120)])
    bio = TextAreaField('About Me (Optional)', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Save Profile Changes')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8,
                                                                                    message='Password must be at least 8 characters long.')])
    confirm_password = PasswordField('Confirm New Password',
                                     validators=[DataRequired(),
                                                 EqualTo('new_password', message='New passwords must match.')])
    submit = SubmitField('Update Password')


# --- File Upload Form (General Purpose) ---
class FileUploadForm(FlaskForm):
    file = FileField('Select File', validators=[DataRequired(),
                                                FileAllowed(
                                                    ['pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx', 'txt',
                                                     'csv'],
                                                    'Allowed file types: pdf, png, jpg, jpeg, doc, docx, xls, xlsx, txt, csv')
                                                ])
    description = TextAreaField('Description (Optional)', validators=[Optional(), Length(max=500)])
    is_public = BooleanField('Make Public', default=False)
    submit = SubmitField('Upload File')


# --- Trading Model Form ---
class TradingModelForm(FlaskForm):
    name = StringField('Model Name', validators=[DataRequired(), Length(max=150)])
    version = StringField('Version', validators=[Optional(), Length(max=50)])
    is_active = BooleanField('Is Active', default=True)
    overview_logic = TextAreaField('Overview & Logic', validators=[Optional()])
    primary_chart_tf = StringField('Primary Chart TF (Analysis/Setup)', validators=[Optional(), Length(max=50)])
    execution_chart_tf = StringField('Execution Chart TF (Entry/Fine-tuning)', validators=[Optional(), Length(max=50)])
    context_chart_tf = StringField('Higher Timeframe (Context/Trend)', validators=[Optional(), Length(max=50)])
    technical_indicators_used = TextAreaField('Technical Indicators Used (and settings)', validators=[Optional()])
    chart_patterns_used = TextAreaField('Chart Patterns Used', validators=[Optional()])
    price_action_signals = TextAreaField('Price Action Signals', validators=[Optional()])
    key_levels_identification = TextAreaField('Key Levels Identification', validators=[Optional()])
    volume_analysis_notes = TextAreaField('Volume Analysis (if applicable)', validators=[Optional()])
    fundamental_analysis_notes = TextAreaField('Fundamental Analysis Considerations (if applicable)',
                                               validators=[Optional()])
    instrument_applicability = TextAreaField('Instrument Applicability (e.g., NQ, ES, specific stocks)',
                                             validators=[Optional()])
    session_applicability = TextAreaField('Session Applicability (e.g., London Open, NY Open)', validators=[Optional()])
    optimal_market_conditions = TextAreaField('Optimal Market Conditions for this Model', validators=[Optional()])
    sub_optimal_market_conditions = TextAreaField('Sub-optimal Market Conditions (or when to avoid)',
                                                  validators=[Optional()])
    entry_trigger_description = TextAreaField('Entry Trigger Description (Specific conditions for entry)',
                                              validators=[DataRequired()])
    stop_loss_strategy = TextAreaField('Stop-Loss Strategy (e.g., ATR-based, fixed points, structure)',
                                       validators=[DataRequired()])
    take_profit_strategy = TextAreaField('Take-Profit Strategy (e.g., fixed R:R, key levels, trailing)',
                                         validators=[DataRequired()])
    min_risk_reward_ratio = FloatField('Minimum Acceptable Risk:Reward Ratio', validators=[Optional(),
                                                                                           NumberRange(min=0.0,
                                                                                                       message="R:R must be a positive number or zero.")])
    position_sizing_rules = TextAreaField('Position Sizing Rules (e.g., % of account, fixed lot)',
                                          validators=[Optional()])
    scaling_in_out_rules = TextAreaField('Scaling In/Out Rules (if applicable)', validators=[Optional()])
    trade_management_breakeven_rules = TextAreaField('Trade Management: Breakeven Rules', validators=[Optional()])
    trade_management_trailing_stop_rules = TextAreaField('Trade Management: Trailing Stop Rules',
                                                         validators=[Optional()])
    trade_management_partial_profit_rules = TextAreaField('Trade Management: Partial Profit Taking Rules',
                                                          validators=[Optional()])
    trade_management_adverse_price_action = TextAreaField('Trade Management: Handling Adverse Price Action',
                                                          validators=[Optional()])
    model_max_loss_per_trade = StringField('Max Risk per Trade for this Model (e.g., 1% or $X)',
                                           validators=[Optional(), Length(max=100)])
    model_max_daily_loss = StringField('Max Daily Loss when using this Model (e.g., 3% or $Y)',
                                       validators=[Optional(), Length(max=100)])
    model_max_weekly_loss = StringField('Max Weekly Loss when using this Model',
                                        validators=[Optional(), Length(max=100)])
    model_consecutive_loss_limit = StringField('Consecutive Loss Limit for this Model (e.g., 3 trades)',
                                               validators=[Optional(), Length(max=100)])
    model_action_on_max_drawdown = TextAreaField('Action if Max Drawdown (for this model) is Hit',
                                                 validators=[Optional()])
    pre_trade_checklist = TextAreaField('Pre-Trade Routine Checklist (Model Specific - one item per line)',
                                        validators=[Optional()])
    order_types_used = TextAreaField('Order Types Primarily Used (e.g., Market, Limit, Stop)', validators=[Optional()])
    broker_platform_notes = TextAreaField('Broker/Platform Specific Notes', validators=[Optional()])
    execution_confirmation_notes = TextAreaField('Confirmation after Execution Notes', validators=[Optional()])
    post_trade_routine_model = TextAreaField('Post-Trade Routine (Model Specific)', validators=[Optional()])
    strengths = TextAreaField('Perceived Strengths of this Model', validators=[Optional()])
    weaknesses = TextAreaField('Perceived Weaknesses of this Model', validators=[Optional()])
    backtesting_forwardtesting_notes = TextAreaField('Backtesting/Forward-Testing Notes & Results',
                                                     validators=[Optional()])
    refinements_learnings = TextAreaField('Refinements & Learnings Over Time', validators=[Optional()])
    
    # Chart Examples and Visual Analysis
    chart_examples = MultipleFileField('Chart Examples', 
                                     validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 
                                                                        'Images only! Supported formats: JPG, PNG, GIF, WebP')])
    
    submit = SubmitField('Save Trading Model')


# --- Admin Forms ---
class AdminCreateUserForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(message="Username is required."),
                                       Length(min=3, max=25, message="Username must be between 3 and 25 characters.")])
    email = StringField('Email',
                        validators=[DataRequired(message="Email is required."),
                                    Email(message="Please enter a valid email address.")])
    name = StringField('Full Name (Optional)', validators=[Optional(), Length(max=100)])
    password = PasswordField('Password',
                             validators=[DataRequired(message="Password is required."),
                                         Length(min=8, message="Password must be at least 8 characters long.")])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(message="Please confirm your password."),
                                                 EqualTo('password', message="Passwords must match.")])
    role = SelectField('Role',
                       choices=[(role.value, role.name.title()) for role in UserRole],
                       validators=[DataRequired()])
    is_active = BooleanField('Account Active', default=True)
    is_email_verified = BooleanField('Email Verified by Admin', default=False)
    submit = SubmitField('Create User')


class AdminEditUserForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(message="Username is required."),
                                       Length(min=3, max=25, message="Username must be between 3 and 25 characters.")])
    email = StringField('Email',
                        validators=[DataRequired(message="Email is required."),
                                    Email(message="Please enter a valid email address.")])
    name = StringField('Full Name (Optional)', validators=[Optional(), Length(max=100)])
    role = SelectField('Role',
                       choices=[(role.value, role.name.title()) for role in UserRole],
                       validators=[DataRequired()])
    is_active = BooleanField('Account Active')
    is_email_verified = BooleanField('Email Verified by Admin')
    new_password = PasswordField('New Password (leave blank to keep current)',
                                 validators=[Optional(),
                                             Length(min=8,
                                                    message="If changing, password must be at least 8 characters long.")])
    confirm_new_password = PasswordField('Confirm New Password',
                                         validators=[EqualTo('new_password', message="New passwords must match.")])
    submit = SubmitField('Update User Details')


# --- FORMS FOR TRADE LOGGING ---

class EntryPointForm(FlaskForm):
    # Hidden field to track existing entry ID during edit
    id = IntegerField(validators=[Optional()])
    entry_time = TimeField('Time (HH:MM NY)', format='%H:%M', validators=[DataRequired(message="Entry time required.")],
                           render_kw={"placeholder": "HH:MM"})
    contracts = IntegerField('Contracts',
                             validators=[DataRequired(message="# Contracts required."), NumberRange(min=1)],
                             render_kw={"placeholder": "e.g., 1"})
    entry_price = FloatField('Price', validators=[DataRequired(message="Entry price required.")],
                             render_kw={"placeholder": "e.g., 15000.25"})


class ExitPointForm(FlaskForm):
    # Hidden field to track existing exit ID during edit
    id = IntegerField(validators=[Optional()])
    exit_time = TimeField('Time (HH:MM NY)', format='%H:%M', validators=[Optional()],
                          render_kw={"placeholder": "HH:MM"})
    contracts = IntegerField('Contracts', validators=[Optional(), NumberRange(min=1)],
                             render_kw={"placeholder": "e.g., 1"})
    exit_price = FloatField('Price', validators=[Optional()], render_kw={"placeholder": "e.g., 15010.50"})


class TradeForm(FlaskForm):
    # Remove hardcoded instrument_choices - will be set dynamically
    direction_choices = [('', 'Select Direction'), ('Long', 'Long'), ('Short', 'Short')]
    how_closed_choices = [
        ('', 'Select How Closed'), ('Manual', 'Closed Manually'), ('SL', 'Closed by Stop Loss'),
        ('TP', 'Closed by Take Profit'), ('Trailing SL', 'Closed by Trailing Stop Loss'),
        ('Time Exit', 'Exited by Time Rule'), ('Still Open', 'Still Open / Partially Exited')
    ]
    rating_choices = [('', '-- Rate 1-5 --')] + [(str(i), str(i)) for i in range(1, 6)]

    instrument = SelectField('Instrument', choices=[('', 'Select Instrument')], validators=[DataRequired()])
    trade_date = DateField('Trade Date', validators=[DataRequired(message="Please select a trade date.")],
                           format='%Y-%m-%d', render_kw={"placeholder": "YYYY-MM-DD"})
    direction = SelectField('Direction', choices=direction_choices, validators=[DataRequired()])

    entries = FieldList(FormField(EntryPointForm), min_entries=1, label='Entry Points')
    exits = FieldList(FormField(ExitPointForm), min_entries=0, label='Exit Points')

    initial_stop_loss = FloatField('Stop Loss Price', validators=[Optional()], render_kw={"placeholder": "Price"})
    terminus_target = FloatField('Terminus Target Price', validators=[Optional()], render_kw={"placeholder": "Price"})
    is_dca = BooleanField('Check here if this trade is a DCA entry strategy')
    mae = FloatField('MAE (In Points)', validators=[Optional()], render_kw={"placeholder": "Points against"})
    mfe = FloatField('MFE (In Points)', validators=[Optional()], render_kw={"placeholder": "Points for"})

    trading_model_id = SelectField('Model Used', coerce=int, validators=[InputRequired(message="Select model")],
                                   choices=[(0, "Select Model")])
    news_event_select = SelectField('News Event', choices=[('', 'None')], validators=[Optional()])
    how_closed = SelectField('Trade Closure Method', choices=how_closed_choices, validators=[Optional()])

    preparation_rating = SelectField('Prep for This Trade', choices=rating_choices, coerce=coerce_int_optional,
                                     validators=[Optional()])
    rules_rating = SelectField('Follow My Rules', choices=rating_choices, coerce=coerce_int_optional, validators=[Optional()])
    management_rating = SelectField('Manage the Trade', choices=rating_choices, coerce=coerce_int_optional,
                                    validators=[Optional()])
    target_rating = SelectField('Place Targets', choices=rating_choices, coerce=coerce_int_optional, validators=[Optional()])
    entry_rating = SelectField('Enter the Trade', choices=rating_choices, coerce=coerce_int_optional, validators=[Optional()])

    trade_notes = TextAreaField('Pre-Trade Analysis', validators=[Optional()],
                                render_kw={"rows": 4, "placeholder": "Trade context, Consider P12 analysis, 4-steps process, etc..."})
    psych_scored_highest = TextAreaField('Where did I score highest and how will I sustain this?', validators=[Optional()], render_kw={"rows": 6})
    psych_scored_lowest = TextAreaField('Where did I score lowest and how will I improve this?', validators=[Optional()], render_kw={"rows": 6})
    overall_analysis_notes = TextAreaField('Post-Trade Analysis', validators=[Optional()],
                                           render_kw={"rows": 3, "placeholder": "Post-trade reflection..."})
    trade_management_notes = TextAreaField('Trade Management Notes', validators=[Optional()],
                                           render_kw={"rows": 2, "placeholder": "Adjustments to SL/TP, partials..."})
    errors_notes = TextAreaField('Errors Noted', validators=[Optional()], render_kw={"rows": 2})
    improvements_notes = TextAreaField('Improvements Noted', validators=[Optional()], render_kw={"rows": 2})

    trade_images = MultipleFileField('Trade Images', validators=[Optional(), FileAllowed(
        ['jpg', 'png', 'jpeg', 'gif'], 'Images only!')])
    screenshot_link = StringField('Screenshot Links', validators=[Optional(), Length(max=255)],
                                  render_kw={"placeholder": "http://..."})
    tags = OptGroupSelectMultipleField('Tags', choices=[],
                                       render_kw={'class': 'form-select', 'multiple': 'multiple'})
    submit = SubmitField('Save Trade')

    def __init__(self, *args, **kwargs):
        super(TradeForm, self).__init__(*args, **kwargs)
        # Load dynamic instrument choices
        from app.models import Instrument
        try:
            self.instrument.choices = Instrument.get_instrument_choices()
        except Exception:
            # Fallback to hardcoded choices if database fails
            self.instrument.choices = [
                ('', 'Select Instrument'),
                ('NQ', 'NQ (Nasdaq 100)'),
                ('ES', 'ES (S&P 500)'),
                ('YM', 'YM (Dow Jones)'),
                ('MNQ', 'MNQ (Micro Nasdaq)'),
                ('MES', 'MES (Micro S&P)'),
                ('MYM', 'MYM (Micro Dow)'),
                ('Other', 'Other (Specify)')
            ]
class TagForm(FlaskForm):
    name = StringField('Tag Name', validators=[
        DataRequired(message="Tag name is required."),
        Length(min=1, max=50, message="Tag name must be between 1 and 50 characters.")
    ])
    category = SelectField('Category',
                          choices=[(cat.name, cat.value) for cat in TagCategory],
                          validators=[DataRequired()])
    submit = SubmitField('Save Tag')

class AdminDefaultTagForm(FlaskForm):
    name = StringField('Tag Name', validators=[
        DataRequired(message="Tag name is required."),
        Length(min=1, max=50, message="Tag name must be between 1 and 50 characters.")
    ])
    category = SelectField('Category',
                          choices=[(cat.name, cat.value) for cat in TagCategory],
                          validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Default Tag')

# Form for filtering trades list
class TradeFilterForm(FlaskForm):
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[Optional()])
    instrument = SelectField('Instrument', choices=[('', 'All Instruments')], validators=[Optional()])
    direction = SelectField('Direction', choices=[('', 'All Directions')] + TradeForm.direction_choices[1:],
                            validators=[Optional()])
    trading_model_id = SelectField('Trading Model', coerce=int, choices=[(0, 'All Models')],
                                   validators=[Optional()])  # Choices populated in route
    tags = SelectField('Tag', choices=[('', 'All Tags')], validators=[Optional()])
    submit = SubmitField('Filter Trades')
    clear = SubmitField('Clear Filters', render_kw={'formnovalidate': True, 'class': 'btn btn-outline-secondary'})

    def __init__(self, *args, **kwargs):
        super(TradeFilterForm, self).__init__(*args, **kwargs)
        # Load dynamic instrument choices for filter
        from app.models import Instrument
        try:
            instrument_choices = Instrument.get_instrument_choices()
            self.instrument.choices = [('', 'All Instruments')] + instrument_choices[1:]  # Skip the 'Select Instrument' option
        except Exception:
            # Fallback to hardcoded choices
            self.instrument.choices = [
                ('', 'All Instruments'),
                ('NQ', 'NQ (Nasdaq 100)'),
                ('ES', 'ES (S&P 500)'),
                ('YM', 'YM (Dow Jones)'),
                ('MNQ', 'MNQ (Micro Nasdaq)'),
                ('MES', 'MES (Micro S&P)'),
                ('MYM', 'MYM (Micro Dow)'),
                ('Other', 'Other (Specify)')
            ]


# Form for importing trades
class ImportTradesForm(FlaskForm):
    csv_file = FileField('CSV File to Import',
                         validators=[DataRequired(), FileAllowed(['csv'], 'Only CSV files are allowed!')])
    submit = SubmitField('Upload and Import Trades')

class DailyJournalForm(FlaskForm):
    journal_date = DateField('Journal Date', format='%Y-%m-%d', validators=[DataRequired()])

    # Part 1: Pre-market Preparation
    key_events_today = TextAreaField('Key Economic Events/News Today', validators=[Optional()], render_kw={"rows": 2,
                                                                                                           "placeholder": "List major news, speeches, data releases..."})
    key_tasks_today = TextAreaField('Key Personal Tasks for Today', validators=[Optional()], render_kw={"rows": 2,
                                                                                                        "placeholder": "Important non-trading tasks impacting your day..."})

    on_my_mind = TextAreaField('On My Mind (from yesterday / for today)', validators=[Optional()],
                               render_kw={"rows": 2, "placeholder": "Lingering thoughts, reflections, expectations..."})
    important_focus_today = TextAreaField('Most Important Things to Focus On In My Trading Today',
                                          validators=[Optional()], render_kw={"rows": 2,
                                                                              "placeholder": "Key principles, rules, or behaviors..."})

    mental_rating_choices = [('', '-- Rate --')] + [(str(i), str(i)) for i in range(1, 6)]  # 1-5
    mental_feeling_rating = SelectField('Mental Feeling (Overall Mood)', choices=mental_rating_choices,
                                        coerce=coerce_int_optional, validators=[Optional()])
    mental_mind_rating = SelectField('Mental Mind (Clarity/Focus)', choices=mental_rating_choices,
                                     coerce=coerce_int_optional, validators=[Optional()])
    mental_energy_rating = SelectField('Mental Energy (Physical)', choices=mental_rating_choices,
                                       coerce=coerce_int_optional, validators=[Optional()])
    mental_motivation_rating = SelectField('Mental Motivation (Drive)', choices=mental_rating_choices,
                                           coerce=coerce_int_optional, validators=[Optional()])

    # Part 2: Pre-market Analysis
    # Add to form class:
    p12_scenario_id = SelectField(
        'P12 Scenario',
        coerce=int,
        validators=[Optional()],
        description='Select the P12 scenario observed between 06:00-08:30 EST'
    )

    p12_high = DecimalField(
        'P12 High',
        validators=[Optional()],
        description='18:00-06:00 EST range high'
    )

    p12_mid = DecimalField(
        'P12 Mid',
        validators=[Optional()],
        description='Midpoint of P12 range'
    )

    p12_low = DecimalField(
        'P12 Low',
        validators=[Optional()],
        description='18:00-06:00 EST range low'
    )

    p12_notes = TextAreaField(
        'P12 Analysis Notes',
        validators=[Optional()],
        description='Additional P12 scenario observations',
        render_kw={'rows': 3}
    )

    session_direction_choices = [("None", "N/A")] + [(d, d) for d in ["Long", "Short"]]
    session_status_choices = [("None", "N/A")] + [(s, s) for s in
                                                  ["True", "False"]]  # True for normal, False for retrace
    session_model_choices = [("None", "N/A")] + [(m, m) for m in ["Valid", "Broken"]]  # For OU Midline

    # Asia Session
    asia_direction = SelectField('ASN Direction', choices=session_direction_choices, validators=[Optional()])
    asia_session_status = SelectField('ASN Session Status', choices=session_status_choices, validators=[Optional()])
    asia_model_status = SelectField('ASN Model (OU) Status', choices=session_model_choices, validators=[Optional()])
    asia_actual_range_points = FloatField('ASN Actual Range (Points)', validators=[Optional()])
    asia_median_range_input_note = TextAreaField('ASN Median Range Notes/Input', validators=[Optional()],
                                                 render_kw={"rows": 2,
                                                            "placeholder": "e.g., manual input for median range expectation"})

    # London Session
    london_direction = SelectField('LDN Direction', choices=session_direction_choices, validators=[Optional()])
    london_session_status = SelectField('LDN Session Status', choices=session_status_choices, validators=[Optional()])
    london_model_status = SelectField('LDN Model (OU) Status', choices=session_model_choices, validators=[Optional()])
    london_actual_range_points = FloatField('LDN Actual Range (Points)', validators=[Optional()])
    london_median_range_input_note = TextAreaField('LDN Median Range Notes/Input', validators=[Optional()],
                                                   render_kw={"rows": 2})

    # NY1 Session
    ny1_direction = SelectField('NY1 Direction', choices=session_direction_choices, validators=[Optional()])
    ny1_session_status = SelectField('NY1 Session Status', choices=session_status_choices, validators=[Optional()])
    ny1_model_status = SelectField('NY1 Model (OU) Status', choices=session_model_choices, validators=[Optional()])
    ny1_actual_range_points = FloatField('NY1 Actual Range (Points)', validators=[Optional()])
    ny1_median_range_input_note = TextAreaField('NY1 Median Range Notes/Input', validators=[Optional()],
                                                render_kw={"rows": 2})

    # NY1 HOD/LOD Projections (wg_ fields) - Example for one set (Long/True HOD)
    wg_ny1_lt_notes = TextAreaField('NY1 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny1_lt_hod_pct_l = FloatField('NY1 L/T HOD Low %', validators=[Optional()])
    wg_ny1_lt_hod_pct_h = FloatField('NY1 L/T HOD High %', validators=[Optional()])
    wg_ny1_lt_hod_ts = TimeField('NY1 L/T HOD Time Start', format='%H:%M', validators=[Optional()])
    wg_ny1_lt_hod_te = TimeField('NY1 L/T HOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny1_lf_notes = TextAreaField('NY1 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny1_lf_hod_pct_l = FloatField('NY1 L/T HOD Low %', validators=[Optional()])
    wg_ny1_lf_hod_pct_h = FloatField('NY1 L/T HOD High %', validators=[Optional()])
    wg_ny1_lf_hod_ts = TimeField('NY1 L/T HOD Time Start', format='%H:%M', validators=[Optional()])
    wg_ny1_lf_hod_te = TimeField('NY1 L/T HOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny1_st_notes = TextAreaField('NY1 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny1_st_hod_pct_l = FloatField('NY1 L/T HOD Low %', validators=[Optional()])
    wg_ny1_st_hod_pct_h = FloatField('NY1 L/T HOD High %', validators=[Optional()])
    wg_ny1_st_hod_ts = TimeField('NY1 L/T HOD Time Start', format='%H:%M', validators=[Optional()])
    wg_ny1_st_hod_te = TimeField('NY1 L/T HOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny1_sf_notes = TextAreaField('NY1 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny1_sf_hod_pct_l = FloatField('NY1 L/T HOD Low %', validators=[Optional()])
    wg_ny1_sf_hod_pct_h = FloatField('NY1 L/T HOD High %', validators=[Optional()])
    wg_ny1_sf_hod_ts = TimeField('NY1 L/T HOD Time Sfart', format='%H:%M', validators=[Optional()])
    wg_ny1_sf_hod_te = TimeField('NY1 L/T HOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny1_lt_notes = TextAreaField('NY1 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny1_lt_lod_pct_l = FloatField('NY1 L/T LOD Low %', validators=[Optional()])
    wg_ny1_lt_lod_pct_h = FloatField('NY1 L/T LOD High %', validators=[Optional()])
    wg_ny1_lt_lod_ts = TimeField('NY1 L/T LOD Time Start', format='%H:%M', validators=[Optional()])
    wg_ny1_lt_lod_te = TimeField('NY1 L/T LOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny1_lf_notes = TextAreaField('NY1 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny1_lf_lod_pct_l = FloatField('NY1 L/T LOD Low %', validators=[Optional()])
    wg_ny1_lf_lod_pct_h = FloatField('NY1 L/T LOD High %', validators=[Optional()])
    wg_ny1_lf_lod_ts = TimeField('NY1 L/T LOD Time Start', format='%H:%M', validators=[Optional()])
    wg_ny1_lf_lod_te = TimeField('NY1 L/T LOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny1_st_notes = TextAreaField('NY1 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny1_st_lod_pct_l = FloatField('NY1 L/T LOD Low %', validators=[Optional()])
    wg_ny1_st_lod_pct_h = FloatField('NY1 L/T LOD High %', validators=[Optional()])
    wg_ny1_st_lod_ts = TimeField('NY1 L/T LOD Time Start', format='%H:%M', validators=[Optional()])
    wg_ny1_st_lod_te = TimeField('NY1 L/T LOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny1_sf_notes = TextAreaField('NY1 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny1_sf_lod_pct_l = FloatField('NY1 L/T LOD Low %', validators=[Optional()])
    wg_ny1_sf_lod_pct_h = FloatField('NY1 L/T LOD High %', validators=[Optional()])
    wg_ny1_sf_lod_ts = TimeField('NY1 L/T LOD Time Sfart', format='%H:%M', validators=[Optional()])
    wg_ny1_sf_lod_te = TimeField('NY1 L/T LOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny2_lt_notes = TextAreaField('NY2 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny2_lt_hod_pct_l = FloatField('NY2 L/T HOD Low %', validators=[Optional()])
    wg_ny2_lt_hod_pct_h = FloatField('NY2 L/T HOD High %', validators=[Optional()])
    wg_ny2_lt_hod_ts = TimeField('NY2 L/T HOD Time Start', format='%H:%M', validators=[Optional()])
    wg_ny2_lt_hod_te = TimeField('NY2 L/T HOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny2_lf_notes = TextAreaField('NY2 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny2_lf_hod_pct_l = FloatField('NY2 L/T HOD Low %', validators=[Optional()])
    wg_ny2_lf_hod_pct_h = FloatField('NY2 L/T HOD High %', validators=[Optional()])
    wg_ny2_lf_hod_ts = TimeField('NY2 L/T HOD Time Start', format='%H:%M', validators=[Optional()])
    wg_ny2_lf_hod_te = TimeField('NY2 L/T HOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny2_st_notes = TextAreaField('NY2 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny2_st_hod_pct_l = FloatField('NY2 L/T HOD Low %', validators=[Optional()])
    wg_ny2_st_hod_pct_h = FloatField('NY2 L/T HOD High %', validators=[Optional()])
    wg_ny2_st_hod_ts = TimeField('NY2 L/T HOD Time Start', format='%H:%M', validators=[Optional()])
    wg_ny2_st_hod_te = TimeField('NY2 L/T HOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny2_sf_notes = TextAreaField('NY2 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny2_sf_hod_pct_l = FloatField('NY2 L/T HOD Low %', validators=[Optional()])
    wg_ny2_sf_hod_pct_h = FloatField('NY2 L/T HOD High %', validators=[Optional()])
    wg_ny2_sf_hod_ts = TimeField('NY2 L/T HOD Time Sfart', format='%H:%M', validators=[Optional()])
    wg_ny2_sf_hod_te = TimeField('NY2 L/T HOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny2_lt_notes = TextAreaField('NY2 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny2_lt_lod_pct_l = FloatField('NY2 L/T LOD Low %', validators=[Optional()])
    wg_ny2_lt_lod_pct_h = FloatField('NY2 L/T LOD High %', validators=[Optional()])
    wg_ny2_lt_lod_ts = TimeField('NY2 L/T LOD Time Start', format='%H:%M', validators=[Optional()])
    wg_ny2_lt_lod_te = TimeField('NY2 L/T LOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny2_lf_notes = TextAreaField('NY2 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny2_lf_lod_pct_l = FloatField('NY2 L/T LOD Low %', validators=[Optional()])
    wg_ny2_lf_lod_pct_h = FloatField('NY2 L/T LOD High %', validators=[Optional()])
    wg_ny2_lf_lod_ts = TimeField('NY2 L/T LOD Time Start', format='%H:%M', validators=[Optional()])
    wg_ny2_lf_lod_te = TimeField('NY2 L/T LOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny2_st_notes = TextAreaField('NY2 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny2_st_lod_pct_l = FloatField('NY2 L/T LOD Low %', validators=[Optional()])
    wg_ny2_st_lod_pct_h = FloatField('NY2 L/T LOD High %', validators=[Optional()])
    wg_ny2_st_lod_ts = TimeField('NY2 L/T LOD Time Start', format='%H:%M', validators=[Optional()])
    wg_ny2_st_lod_te = TimeField('NY2 L/T LOD Time End', format='%H:%M', validators=[Optional()])

    wg_ny2_sf_notes = TextAreaField('NY2 Long/True Projection Notes', validators=[Optional()], render_kw={"rows": 2})
    wg_ny2_sf_lod_pct_l = FloatField('NY2 L/T LOD Low %', validators=[Optional()])
    wg_ny2_sf_lod_pct_h = FloatField('NY2 L/T LOD High %', validators=[Optional()])
    wg_ny2_sf_lod_ts = TimeField('NY2 L/T LOD Time Sfart', format='%H:%M', validators=[Optional()])
    wg_ny2_sf_lod_te = TimeField('NY2 L/T LOD Time End', format='%H:%M', validators=[Optional()])

    # NY2 Session
    ny2_direction = SelectField('NY2 Direction', choices=session_direction_choices, validators=[Optional()])
    ny2_session_status = SelectField('NY2 Session Status', choices=session_status_choices, validators=[Optional()])
    ny2_model_status = SelectField('NY2 Model (OU) Status', choices=session_model_choices, validators=[Optional()])
    ny2_actual_range_points = FloatField('NY2 Actual Range (Points)', validators=[Optional()])
    ny2_median_range_input_note = TextAreaField('NY2 Median Range Notes/Input', validators=[Optional()],
                                                render_kw={"rows": 2})

    # Step 3: Realistic Expectance
    adr_10_day_median_range_value = FloatField('10-Day Median Range (ADR/MDR Value)', validators=[Optional()])
    todays_total_range_points = FloatField("Today's Total Range (Points)", validators=[Optional()])
    realistic_expectance_notes = TextAreaField('Step 3: Realistic Expectance Notes (RTE for images)',
                                               validators=[Optional()], render_kw={"rows": 4,
                                                                                   "placeholder": "Compare current range to historical, extension analysis..."})

    # Step 4: Engagement Structure
    engagement_structure_notes = TextAreaField('Step 4: Engagement Structure Notes (RTE for images)',
                                               validators=[Optional()], render_kw={"rows": 4,
                                                                                   "placeholder": "Highest statistical structure, entry types..."})

    key_levels_notes = TextAreaField('Key Levels Identified (Pre-Market)', validators=[Optional()],
                                     render_kw={"rows": 3, "placeholder": "Support, Resistance, Pivots, Fibs..."})
    pre_market_news_notes = TextAreaField('Pre-Market News Impact Analysis', validators=[Optional()],
                                          render_kw={"rows": 3, "placeholder": "How might today's news affect setups?"})

    pre_market_screenshots = MultipleFileField('Pre-Market Analysis Screenshots', validators=[Optional(), FileAllowed(
        ['jpg', 'png', 'jpeg', 'gif'], 'Images only!')])

    # Part 4: Post Market Analysis
    market_observations = TextAreaField('Post-Market Analysis / Market Observations (RTE for images)',
                                        validators=[Optional()], render_kw={"rows": 5,
                                                                            "placeholder": "How did the market actually behave? Key observations..."})
    self_observations = TextAreaField('Self-Observations / Re-engineering Notes (RTE for images)',
                                      validators=[Optional()], render_kw={"rows": 5,
                                                                          "placeholder": "Reflection on personal performance, decision-making..."})
    eod_chart_screenshots = MultipleFileField('End-of-Day Chart Screenshots', validators=[Optional(), FileAllowed(
        ['jpg', 'png', 'jpeg', 'gif'], 'Images only!')])

    # Part 5: Daily Review and Reflection
    did_well_today = TextAreaField('What I Did Well Today (RTE for images)', validators=[Optional()],
                                   render_kw={"rows": 3})
    did_not_go_well_today = TextAreaField('What Did Not Go So Well Today (RTE for images)', validators=[Optional()],
                                          render_kw={"rows": 3})
    learned_today = TextAreaField('Something I Learned About the Market or Myself Today (RTE for images)',
                                  validators=[Optional()], render_kw={"rows": 3})
    improve_action_next_day = TextAreaField('Action(s) I Can Take to Improve My Trading Performance Going Forward',
                                            validators=[Optional()], render_kw={"rows": 3})

    # Daily Psych Review scores (will be filled from model if editing)
    review_psych_discipline_rating = SelectField('Psych Review: Discipline', choices=mental_rating_choices,
                                                 coerce=coerce_int_optional, validators=[Optional()])
    review_psych_motivation_rating = SelectField('Psych Review: Motivation', choices=mental_rating_choices,
                                                 coerce=coerce_int_optional, validators=[Optional()])
    review_psych_focus_rating = SelectField('Psych Review: Focus', choices=mental_rating_choices,
                                            coerce=coerce_int_optional, validators=[Optional()])
    review_psych_mastery_rating = SelectField('Psych Review: Mastery', choices=mental_rating_choices,
                                              coerce=coerce_int_optional, validators=[Optional()])
    review_psych_composure_rating = SelectField('Psych Review: Composure', choices=mental_rating_choices,
                                                coerce=coerce_int_optional, validators=[Optional()])
    review_psych_resilience_rating = SelectField('Psych Review: Resilience', choices=mental_rating_choices,
                                                 coerce=coerce_int_optional, validators=[Optional()])
    review_psych_mind_rating = SelectField('Psych Review: Mind Clarity', choices=mental_rating_choices,
                                           coerce=coerce_int_optional, validators=[Optional()])
    review_psych_energy_rating = SelectField('Psych Review: Physical Energy', choices=mental_rating_choices,
                                             coerce=coerce_int_optional, validators=[Optional()])

    submit = SubmitField('Save Daily Journal')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Only populate P12 scenario choices for this form
        try:
            from app.models import P12Scenario
            scenarios = P12Scenario.query.filter_by(is_active=True).order_by(P12Scenario.scenario_number).all()

            # Only set this if the field exists (which it should for DailyJournalForm)
            if hasattr(self, 'p12_scenario_id'):
                self.p12_scenario_id.choices = [(0, 'Select P12 scenario...')] + [
                    (s.id, f"Scenario {s.scenario_number}: {s.scenario_name}") for s in scenarios
                ]
        except Exception as e:
            # P12 scenario loading is optional for this form
            if hasattr(self, 'p12_scenario_id'):
                self.p12_scenario_id.choices = [(0, 'Select P12 scenario...')]

class P12ScenarioForm(FlaskForm):
    """Form for creating/editing P12 scenarios."""

    scenario_number = StringField(
        'Scenario Number',
        validators=[DataRequired(), Length(min=1, max=10)],
        description='Enter scenario ID (e.g. 1A, 3B, etc)'
    )

    scenario_name = StringField(
        'Scenario Name',
        validators=[DataRequired(), Length(max=100)],
        description='Brief name for this scenario'
    )

    short_description = StringField(
        'Short Description',
        validators=[DataRequired(), Length(max=200)],
        description='One-line summary of the scenario'
    )

    detailed_description = TextAreaField(
        'Detailed Description',
        validators=[DataRequired()],
        description='Full explanation of what happens in this scenario',
        render_kw={'rows': 6}
    )

    hod_lod_implication = TextAreaField(
        'HOD/LOD Implication',
        validators=[DataRequired()],
        description='Where the High of Day/Low of Day is likely located',
        render_kw={'rows': 4}
    )

    directional_bias = SelectField(
        'Directional Bias',
        choices=[
            ('', 'Select bias...'),
            ('bullish', 'Bullish'),
            ('bearish', 'Bearish'),
            ('neutral', 'Neutral'),
            ('choppy', 'Choppy/Ranging')
        ],
        validators=[Optional()]
    )

    alert_criteria = TextAreaField(
        'Alert Criteria',
        validators=[DataRequired()],
        description='What price action to watch for to identify this scenario',
        render_kw={'rows': 4}
    )

    confirmation_criteria = TextAreaField(
        'Confirmation Criteria',
        validators=[DataRequired()],
        description='How to confirm this scenario is actually playing out',
        render_kw={'rows': 4}
    )

    entry_strategy = TextAreaField(
        'Entry Strategy',
        validators=[DataRequired()],
        description='How to trade this scenario (entry points, timing)',
        render_kw={'rows': 5}
    )

    typical_targets = TextAreaField(
        'Typical Targets',
        validators=[Optional()],
        description='Common target areas (P12 levels, percentages, etc.)',
        render_kw={'rows': 3}
    )

    stop_loss_guidance = TextAreaField(
        'Stop Loss Guidance',
        validators=[Optional()],
        description='Where to place stops for this scenario',
        render_kw={'rows': 3}
    )

    risk_percentage = FloatField(
        'Risk Percentage',
        validators=[Optional(), NumberRange(min=0.01, max=10.0)],
        description='Typical risk % for this scenario (e.g., 0.35, 0.50)'
    )

    scenario_image = FileField(
        'Scenario Image',
        validators=[
            FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
        ],
        description='Upload a chart image showing this scenario'
    )

    is_active = BooleanField(
        'Active Scenario',
        default=True,
        description='Whether this scenario is available for selection'
    )

    # NEW: Trading Model Recommendations Section
    models_to_activate = SelectMultipleField(
        'Trading Models to Activate',
        choices=[],  # Will be populated dynamically
        validators=[Optional()],
        description='Select trading models that should be activated for this scenario',
        render_kw={'class': 'form-select', 'multiple': True, 'size': '4'}
    )

    models_to_avoid = SelectMultipleField(
        'Trading Models to Avoid',
        choices=[],  # Will be populated dynamically
        validators=[Optional()],
        description='Select trading models that should be avoided for this scenario',
        render_kw={'class': 'form-select', 'multiple': True, 'size': '4'}
    )

    risk_guidance = TextAreaField(
        'Risk Management Guidance',
        validators=[Optional()],
        description='Guidance on risk percentage and risk management for this scenario',
        render_kw={'rows': 3, 'placeholder': 'e.g., "2.5% - 5% risk (higher confidence due to clear direction)"'}
    )

    preferred_timeframes = SelectMultipleField(
        'Preferred Timeframes',
        choices=[
            ('1m', '1 Minute'),
            ('5m', '5 Minutes'),
            ('15m', '15 Minutes'),
            ('1h', '1 Hour'),
            ('4h', '4 Hours'),
            ('1d', '1 Day')
        ],
        validators=[Optional()],
        description='Recommended timeframes for analyzing this scenario',
        render_kw={'class': 'form-select', 'multiple': True, 'size': '3'}
    )

    key_considerations = TextAreaField(
        'Key Trading Considerations',
        validators=[Optional()],
        render_kw={'rows': 4, 'placeholder': 'Important factors traders should consider when this scenario occurs...'}
    )

    submit = SubmitField('Save Scenario')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate trading model choices ONLY for P12ScenarioForm
        try:
            from app.models import TradingModel

            # Get all active trading models from database
            # Get only default trading models from database
            trading_models = TradingModel.query.filter_by(is_active=True, is_default=True).order_by(
                TradingModel.name).all()

            # Create choices list from database models
            models = [(model.name, model.name) for model in trading_models]
            # Add this temporarily to debug duplicates
            print(f"DEBUG: Loading {len(models)} unique trading models: {[m[0] for m in models]}")

            # If no models in database, provide helpful message
            if not models:
                models = [('', 'No trading models available - create models first')]

            # Only set choices if these fields exist (they should for P12ScenarioForm)
            if hasattr(self, 'models_to_activate'):
                self.models_to_activate.choices = models
            if hasattr(self, 'models_to_avoid'):
                self.models_to_avoid.choices = models

        except Exception as e:
            # Fallback to empty choices if database query fails
            from flask import current_app
            if current_app:
                current_app.logger.error(f"Error loading trading models for P12 form: {e}")

            fallback_models = [('', 'Error loading models - check database connection')]

            if hasattr(self, 'models_to_activate'):
                self.models_to_activate.choices = fallback_models
            if hasattr(self, 'models_to_avoid'):
                self.models_to_avoid.choices = fallback_models


class InstrumentForm(FlaskForm):
    """Form for creating/editing instruments"""
    symbol = StringField('Symbol',
                         validators=[DataRequired(), Length(min=1, max=20)],
                         render_kw={"placeholder": "e.g., ENQ, EES, EURUSD"})

    name = StringField('Full Name',
                       validators=[DataRequired(), Length(min=1, max=100)],
                       render_kw={"placeholder": "e.g., E-mini NASDAQ-100"})

    exchange = SelectField('Exchange',
                           validators=[DataRequired()],
                           choices=[
                               ('CME', 'Chicago Mercantile Exchange (CME)'),
                               ('CBOT', 'Chicago Board of Trade (CBOT)'),
                               ('NYMEX', 'New York Mercantile Exchange (NYMEX)'),
                               ('FOREX', 'Foreign Exchange Market'),
                               ('CRYPTO', 'Cryptocurrency Exchange'),
                               ('NYSE', 'New York Stock Exchange'),
                               ('NASDAQ', 'NASDAQ'),
                               ('OTHER', 'Other')
                           ])

    asset_class = SelectField('Asset Class',
                              validators=[DataRequired()],
                              choices=[
                                  ('Equity Index', 'Equity Index'),
                                  ('Currency', 'Currency'),
                                  ('Commodity', 'Commodity'),
                                  ('Interest Rate', 'Interest Rate'),
                                  ('Energy', 'Energy'),
                                  ('Agricultural', 'Agricultural'),
                                  ('Metals', 'Metals'),
                                  ('Cryptocurrency', 'Cryptocurrency'),
                                  ('Stock', 'Individual Stock'),
                                  ('Bond', 'Bond'),
                                  ('Other', 'Other')
                              ])

    product_group = SelectField('Product Group',
                                validators=[DataRequired()],
                                choices=[
                                    ('E-mini Futures', 'E-mini Futures'),
                                    ('Standard Futures', 'Standard Futures'),
                                    ('Micro Futures', 'Micro Futures'),
                                    ('Forex Spot', 'Forex Spot'),
                                    ('Forex Futures', 'Forex Futures'),
                                    ('Options', 'Options'),
                                    ('Stocks', 'Stocks'),
                                    ('ETFs', 'ETFs'),
                                    ('Cryptocurrencies', 'Cryptocurrencies'),
                                    ('Commodities', 'Commodities'),
                                    ('Other', 'Other')
                                ])

    point_value = FloatField('Point Value ($)',
                             validators=[DataRequired(), NumberRange(min=0.01)],
                             render_kw={"placeholder": "e.g., 5.0, 12.5, 1.0", "step": "0.01"})

    tick_size = FloatField('Tick Size',
                           validators=[DataRequired(), NumberRange(min=0.0001)],
                           render_kw={"placeholder": "e.g., 0.25, 0.1, 0.0001", "step": "0.0001"})

    currency = SelectField('Currency',
                           validators=[DataRequired()],
                           choices=[
                               ('USD', 'US Dollar (USD)'),
                               ('EUR', 'Euro (EUR)'),
                               ('GBP', 'British Pound (GBP)'),
                               ('JPY', 'Japanese Yen (JPY)'),
                               ('CAD', 'Canadian Dollar (CAD)'),
                               ('AUD', 'Australian Dollar (AUD)'),
                               ('CHF', 'Swiss Franc (CHF)'),
                               ('NZD', 'New Zealand Dollar (NZD)'),
                               ('OTHER', 'Other')
                           ],
                           default='USD')

    is_active = BooleanField('Active', default=True)

    submit = SubmitField('Save Instrument')


class InstrumentFilterForm(FlaskForm):
    """Form for filtering instruments in admin list"""
    search = StringField('Search',
                         render_kw={"placeholder": "Search by symbol or name..."})

    exchange = SelectField('Exchange',
                           choices=[('', 'All Exchanges')] + [
                               ('CME', 'CME'), ('CBOT', 'CBOT'), ('NYMEX', 'NYMEX'),
                               ('FOREX', 'FOREX'), ('CRYPTO', 'CRYPTO'),
                               ('NYSE', 'NYSE'), ('NASDAQ', 'NASDAQ'), ('OTHER', 'Other')
                           ])

    asset_class = SelectField('Asset Class',
                              choices=[('', 'All Asset Classes')] + [
                                  ('Equity Index', 'Equity Index'), ('Currency', 'Currency'),
                                  ('Commodity', 'Commodity'), ('Interest Rate', 'Interest Rate'),
                                  ('Energy', 'Energy'), ('Agricultural', 'Agricultural'),
                                  ('Metals', 'Metals'), ('Cryptocurrency', 'Cryptocurrency'),
                                  ('Stock', 'Stock'), ('Bond', 'Bond'), ('Other', 'Other')
                              ])

    status = SelectField('Status',
                         choices=[('', 'All'), ('active', 'Active Only'), ('inactive', 'Inactive Only')])


# --- Backtesting Forms ---
class BacktestForm(FlaskForm):
    """Form for creating and editing backtests"""
    name = StringField('Backtest Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    
    # Date range
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    
    # Status
    status = SelectField('Status',
                        choices=[('draft', 'Draft'),
                                ('running', 'Running'),
                                ('completed', 'Completed'),
                                ('failed', 'Failed'),
                                ('cancelled', 'Cancelled')],
                        validators=[DataRequired()],
                        default='draft')
    
    # Configuration fields
    initial_capital = FloatField('Initial Capital', validators=[Optional()])
    primary_instrument = StringField('Primary Instrument', validators=[Optional(), Length(max=50)])
    position_sizing = StringField('Position Sizing Strategy', validators=[Optional(), Length(max=200)])
    trade_management = TextAreaField('Trade Management Rules',
                                   validators=[Optional()],
                                   render_kw={"rows": 3, "placeholder": "Trade management and scaling rules..."})
    
    # Trading model selection
    trading_model_id = SelectField('Trading Model', 
                                  coerce=int, 
                                  validators=[DataRequired()],
                                  render_kw={"class": "form-select"})
    
    # Market context
    market_conditions = TextAreaField('Market Conditions', 
                                    validators=[Optional()],
                                    render_kw={"rows": 3, "placeholder": "Describe overall market conditions during backtest period..."})
    
    session_context = SelectField('Primary Session Context',
                                 choices=[('', 'All Sessions'),
                                         ('Asia', 'Asia Session'),
                                         ('London', 'London Session'),
                                         ('NY1', 'NY1 Session'),
                                         ('NY2', 'NY2 Session'),
                                         ('Overlap', 'Session Overlaps')],
                                 validators=[Optional()])
    
    # Rules and settings (JSON will be handled in view)
    specific_rules_used = TextAreaField('Specific Rules Used',
                                       validators=[Optional()],
                                       render_kw={"rows": 4, "placeholder": "List specific rules or modifications applied..."})
    
    entry_rules = TextAreaField('Entry Rules',
                               validators=[Optional()],
                               render_kw={"rows": 3, "placeholder": "Specific entry criteria for this backtest..."})
    
    exit_rules = TextAreaField('Exit Rules',
                              validators=[Optional()],
                              render_kw={"rows": 3, "placeholder": "Specific exit criteria for this backtest..."})
    
    trade_management_applied = TextAreaField('Trade Management Applied',
                                           validators=[Optional()],
                                           render_kw={"rows": 4, "placeholder": "Scaling, breakeven, trailing stops, etc."})
    
    risk_settings = TextAreaField('Risk Settings',
                                 validators=[Optional()],
                                 render_kw={"rows": 3, "placeholder": "Position sizing, max loss per trade, etc."})
    
    # Screenshots and notes
    tradingview_screenshot_links = TextAreaField('TradingView Screenshot Links',
                                               validators=[Optional()],
                                               render_kw={"rows": 2, "placeholder": "One URL per line..."})
    
    chart_screenshots = TextAreaField('Chart Screenshot Links',
                                    validators=[Optional()],
                                    render_kw={"rows": 2, "placeholder": "One URL per line..."})
    
    notes = TextAreaField('Additional Notes',
                         validators=[Optional()],
                         render_kw={"rows": 4, "placeholder": "Overall observations, lessons learned, etc."})
    
    submit = SubmitField('Save Backtest')

    def __init__(self, *args, **kwargs):
        super(BacktestForm, self).__init__(*args, **kwargs)
        # Trading model choices will be populated in the view


class BacktestTradeForm(FlaskForm):
    """Form for adding individual trades to a backtest"""
    # Basic trade information
    trade_date = DateField('Trade Date', validators=[DataRequired()])
    trade_time = TimeField('Trade Time', validators=[Optional()])
    instrument = StringField('Instrument', validators=[DataRequired(), Length(max=20)])
    direction = SelectField('Direction', 
                          choices=[('LONG', 'Long'), ('SHORT', 'Short')],
                          validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    
    # Entry and exit prices (for simple trades)
    entry_price = FloatField('Entry Price', validators=[Optional(), NumberRange(min=0)])
    exit_price = FloatField('Exit Price', validators=[Optional(), NumberRange(min=0)])
    
    # Stop and target levels
    stop_loss_price = FloatField('Stop Loss Price', validators=[Optional(), NumberRange(min=0)])
    take_profit_price = FloatField('Take Profit Price', validators=[Optional(), NumberRange(min=0)])
    
    # Exit reason
    actual_exit_reason = SelectField('Exit Reason',
                                   choices=[('', 'Select Reason'),
                                           ('take_profit', 'Take Profit'),
                                           ('stop_loss', 'Stop Loss'),
                                           ('trailing_stop', 'Trailing Stop'),
                                           ('time_exit', 'Time Exit'),
                                           ('manual_exit', 'Manual Exit'),
                                           ('breakeven_stop', 'Breakeven Stop'),
                                           ('partial_profit', 'Partial Profit'),
                                           ('market_close', 'Market Close')],
                                   validators=[Optional()])
    
    # Performance metrics
    profit_loss = FloatField('Profit/Loss ($)', validators=[DataRequired()])
    profit_loss_ticks = FloatField('P&L (Ticks)', validators=[Optional()])
    mae_ticks = FloatField('MAE (Ticks)', validators=[Optional()])
    mfe_ticks = FloatField('MFE (Ticks)', validators=[Optional()])
    duration_minutes = IntegerField('Duration (Minutes)', validators=[Optional(), NumberRange(min=0)])
    
    # Context
    market_conditions = StringField('Market Conditions', 
                                   validators=[Optional(), Length(max=100)],
                                   render_kw={"placeholder": "Trending, choppy, news-driven..."})
    
    session_context = SelectField('Session Context',
                                 choices=[('', 'Select Session'),
                                         ('Asia', 'Asia'),
                                         ('London', 'London'),
                                         ('NY1', 'NY1'),
                                         ('NY2', 'NY2'),
                                         ('Overlap', 'Overlap')],
                                 validators=[Optional()])
    
    # Screenshots and notes
    tradingview_screenshot_links = TextAreaField('TradingView Screenshots',
                                               validators=[Optional()],
                                               render_kw={"rows": 2, "placeholder": "One URL per line..."})
    
    chart_screenshots = TextAreaField('Chart Screenshots',
                                    validators=[Optional()],
                                    render_kw={"rows": 2, "placeholder": "One URL per line..."})
    
    notes = TextAreaField('Trade Notes',
                         validators=[Optional()],
                         render_kw={"rows": 3, "placeholder": "Setup quality, execution notes, lessons learned..."})
    
    # Tags (will be handled as JSON in view)
    tags = StringField('Tags', 
                      validators=[Optional()],
                      render_kw={"placeholder": "Comma-separated tags..."})
    
    submit = SubmitField('Add Trade')


class BacktestTradeEntryForm(FlaskForm):
    """Form for adding multiple entry points to a backtest trade"""
    entry_time = TimeField('Entry Time', validators=[DataRequired()])
    entry_price = FloatField('Entry Price', validators=[DataRequired(), NumberRange(min=0)])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    entry_reason = StringField('Entry Reason', 
                              validators=[Optional(), Length(max=100)],
                              render_kw={"placeholder": "Initial, scale-in, add to winner..."})
    market_conditions = StringField('Market Conditions',
                                   validators=[Optional(), Length(max=100)],
                                   render_kw={"placeholder": "Market state at this entry..."})
    notes = TextAreaField('Notes', 
                         validators=[Optional()],
                         render_kw={"rows": 2, "placeholder": "Why this entry was taken..."})


class BacktestTradeExitForm(FlaskForm):
    """Form for adding multiple exit points to a backtest trade"""
    exit_time = TimeField('Exit Time', validators=[DataRequired()])
    exit_price = FloatField('Exit Price', validators=[DataRequired(), NumberRange(min=0)])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    exit_reason = SelectField('Exit Reason',
                            choices=[('take_profit', 'Take Profit'),
                                    ('stop_loss', 'Stop Loss'),
                                    ('trailing_stop', 'Trailing Stop'),
                                    ('time_exit', 'Time Exit'),
                                    ('manual_exit', 'Manual Exit'),
                                    ('breakeven_stop', 'Breakeven Stop'),
                                    ('partial_profit', 'Partial Profit'),
                                    ('market_close', 'Market Close')],
                            validators=[DataRequired()])
    profit_loss = FloatField('P&L for this Exit', validators=[DataRequired()])
    market_conditions = StringField('Market Conditions',
                                   validators=[Optional(), Length(max=100)],
                                   render_kw={"placeholder": "Market state at this exit..."})
    notes = TextAreaField('Notes', 
                         validators=[Optional()],
                         render_kw={"rows": 2, "placeholder": "Why this exit was taken..."})


class BacktestFilterForm(FlaskForm):
    """Form for filtering and searching backtests"""
    search = StringField('Search',
                        render_kw={"placeholder": "Search by name or description..."})
    
    trading_model_id = SelectField('Trading Model',
                                  coerce=coerce_int_optional,
                                  choices=[('', 'All Models')],
                                  validators=[Optional()])
    
    status = SelectField('Status',
                        choices=[('', 'All Statuses'),
                                ('draft', 'Draft'),
                                ('running', 'Running'),
                                ('completed', 'Completed'),
                                ('failed', 'Failed'),
                                ('cancelled', 'Cancelled')],
                        validators=[Optional()])
    
    start_date_from = DateField('Start Date From', validators=[Optional()])
    start_date_to = DateField('Start Date To', validators=[Optional()])
    
    session_context = SelectField('Session Context',
                                 choices=[('', 'All Sessions'),
                                         ('Asia', 'Asia'),
                                         ('London', 'London'),
                                         ('NY1', 'NY1'),
                                         ('NY2', 'NY2'),
                                         ('Overlap', 'Overlap')],
                                 validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super(BacktestFilterForm, self).__init__(*args, **kwargs)
        # Trading model choices will be populated in the view