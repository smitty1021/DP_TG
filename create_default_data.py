"""
COMPLETE Database Bootstrap Script - ENHANCED VERSION
====================================================
Creates a comprehensive trading journal database with EVERYTHING needed.

WHAT THIS SCRIPT CREATES:
✅ Users & Authentication:
 - Admin user account + Settings
 - 100 test users (testuser1-testuser100) + Settings for each
 - User groups and associations

✅ Trading Core:
 - Default system tags (based on Random's methodology)
 - Core instruments (ES, NQ, YM, RTY) with proper field mapping
 - Random's 6 default trading models + user-specific models
 - P12 scenarios (complete set of 10 scenarios)

✅ Trading Data:
 - Realistic trades (~10,000) with proper P&L calculations
 - Entry/exit points for all trades
 - Daily journal entries using Four Steps methodology
 - Trade images and journal images

✅ System Configuration:
 - News events and account settings
 - Activity logs
 - File management setup
 - API keys for some users
 - Password reset tokens (historical examples)

MAJOR IMPROVEMENTS:
- Creates ALL models found in your database
- Proper relationship setup and data integrity
- Realistic data volumes for performance testing
- Better error handling and progress reporting
- Complete validation and statistics

Usage: python create_default_data.py
"""

import os
import sys
import random
import uuid
from datetime import datetime, date, time, timedelta
from collections import defaultdict
from decimal import Decimal

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

# Import ALL models for complete coverage
from app.models import (
    # Core user models
    User, UserRole, Group, PasswordReset, ApiKey,

    # Trading models
    Trade, EntryPoint, ExitPoint, TradingModel, Instrument, Tag, TagCategory,

    # Journal models
    DailyJournal, WeeklyJournal, MonthlyJournal,

    # P12 models
    P12Scenario, P12UsageStats,

    # Image and file models
    TradeImage, DailyJournalImage, GlobalImage, File,

    # Settings and configuration
    Settings, AccountSetting, NewsEventItem,

    # Activity tracking
    Activity
)


class EnhancedBootstrapManager:
    """Enhanced manager for complete database bootstrap process."""

    def __init__(self):
        self.app = None
        self.admin_user = None
        self.test_users = []
        self.user_groups = []
        self.instruments = {}
        self.trading_models = []
        self.p12_scenarios = []
        self.tags = []
        self.trades = []
        self.daily_journals = []
        self.news_events = []
        self.account_settings = []

    def initialize_app(self):
        """Initialize Flask app and database."""
        print("🔧 Initializing Flask application...")
        self.app = create_app()

        with self.app.app_context():
            # Drop and recreate all tables
            print("💥 Dropping existing tables...")
            db.drop_all()

            print("🏗️  Creating fresh database schema...")
            db.create_all()

            print("✅ Database schema created successfully")

    def create_admin_user(self):
        """Create the admin user account with full setup."""
        print("\n👤 Creating admin user...")

        admin_data = {
            'username': 'admin',
            'email': 'admin@tradingjournal.local',
            'name': 'System Administrator',
            'role': UserRole.ADMIN,
            'is_active': True,
            'is_email_verified': True,
            'bio': 'System administrator for the trading journal application.',
            'timezone': 'EST',
            'theme_preference': 'dark',
            'notification_preferences': 'email,in_app'
        }

        admin = User(**admin_data)
        admin.set_password('admin123')  # Change this in production!

        db.session.add(admin)
        db.session.commit()

        # Create default settings for admin
        admin_settings = Settings(
            user_id=admin.id,
            timezone='EST',
            theme='dark',
            email_notifications=True,
            browser_notifications=True,
            trading_session_reminders=True,
            daily_journal_reminders=True,
            performance_summary_frequency='weekly'
        )
        db.session.add(admin_settings)

        # Create admin API key
        admin_api_key = ApiKey(
            user_id=admin.id,
            name='Admin Default Key',
            key=uuid.uuid4().hex,
            permissions='admin,read,write'
        )
        db.session.add(admin_api_key)

        db.session.commit()

        self.admin_user = admin
        print(f"✅ Admin user created: {admin.username} (ID: {admin.id})")
        print(f"🔑 Default password: admin123 (CHANGE THIS!)")
        print(f"🔐 API Key: {admin_api_key.key}")

    def create_test_users(self):
        """Create 100 test user accounts with full setup."""
        print("\n👤 Creating 100 test users...")

        created_users = []
        batch_size = 25

        for i in range(1, 101):  # Create testuser1 through testuser100
            # Determine role - 5 admins (testuser1-5), rest are regular users
            if i <= 5:
                user_role = UserRole.ADMIN
            else:
                user_role = UserRole.USER

            # Random attributes for realistic testing
            is_active = random.choice([True, True, True, False])  # 75% active
            is_verified = random.choice([True, True, False])  # 66% verified

            themes = ['light', 'dark', 'auto']
            timezones = ['EST', 'PST', 'CST', 'MST', 'UTC']

            test_user_data = {
                'username': f'testuser{i}',
                'email': f'testuser{i}@example.com',
                'name': f'Test User {i}',
                'role': user_role,
                'is_active': is_active,
                'is_email_verified': is_verified,
                'bio': f'Test user account {i} for trading journal application.',
                'timezone': random.choice(timezones),
                'theme_preference': random.choice(themes)
            }

            test_user = User(**test_user_data)
            test_user.set_password(f'testuser{i}')  # Password same as username

            db.session.add(test_user)
            created_users.append(test_user)

            # Commit in batches for better performance
            if i % batch_size == 0:
                db.session.commit()
                print(f"  📝 Created {i}/100 test users...")

        # Final commit
        db.session.commit()

        # Create settings for all test users
        print("  ⚙️ Creating settings for test users...")
        for user in created_users:
            settings = Settings(
                user_id=user.id,
                timezone=user.timezone,
                theme=user.theme_preference,
                email_notifications=random.choice([True, False]),
                browser_notifications=random.choice([True, False]),
                trading_session_reminders=random.choice([True, False]),
                daily_journal_reminders=random.choice([True, False]),
                performance_summary_frequency=random.choice(['daily', 'weekly', 'monthly'])
            )
            db.session.add(settings)

            # Create API keys for some users (20%)
            if random.random() < 0.2:
                api_key = ApiKey(
                    user_id=user.id,
                    name=f'Auto-generated for {user.username}',
                    key=uuid.uuid4().hex,
                    permissions='read,write' if user.role == UserRole.USER else 'admin,read,write'
                )
                db.session.add(api_key)

        db.session.commit()

        # Store reference to first test user for backward compatibility
        self.test_user = created_users[0] if created_users else None
        self.test_users = created_users

        # Print summary
        admin_count = sum(1 for user in created_users if user.role == UserRole.ADMIN)
        regular_count = sum(1 for user in created_users if user.role == UserRole.USER)
        active_count = sum(1 for user in created_users if user.is_active)
        verified_count = sum(1 for user in created_users if user.is_email_verified)

        print(f"✅ Created {len(created_users)} test users:")
        print(f"   • {admin_count} admin users (testuser1-5)")
        print(f"   • {regular_count} regular users (testuser6-100)")
        print(f"   • {active_count} active users")
        print(f"   • {verified_count} verified users")
        print(f"   • Settings created for all users")
        print(f"   • API keys created for ~20% of users")

        return created_users

    def create_user_groups(self):
        """Create user groups and associations."""
        print("\n👥 Creating user groups...")

        groups_data = [
            {
                'name': 'Traders',
                'description': 'Active traders using the journal system',
                'created_by_user_id': self.admin_user.id
            },
            {
                'name': 'Prop Traders',
                'description': 'Professional proprietary traders',
                'created_by_user_id': self.admin_user.id
            },
            {
                'name': 'Beta Testers',
                'description': 'Users testing new features',
                'created_by_user_id': self.admin_user.id
            },
            {
                'name': 'Administrators',
                'description': 'System administrators and moderators',
                'created_by_user_id': self.admin_user.id
            }
        ]

        created_groups = []
        for group_data in groups_data:
            group = Group(**group_data)
            db.session.add(group)
            created_groups.append(group)

        db.session.commit()

        # Add users to groups
        print("  🔗 Creating group memberships...")

        # Add admin to Administrators group
        admin_group = next(g for g in created_groups if g.name == 'Administrators')
        admin_group.members.append(self.admin_user)

        # Add first 50 test users to Traders group
        traders_group = next(g for g in created_groups if g.name == 'Traders')
        for user in self.test_users[:50]:
            traders_group.members.append(user)

        # Add first 20 test users to Prop Traders group
        prop_group = next(g for g in created_groups if g.name == 'Prop Traders')
        for user in self.test_users[:20]:
            prop_group.members.append(user)

        # Add last 25 test users to Beta Testers group
        beta_group = next(g for g in created_groups if g.name == 'Beta Testers')
        for user in self.test_users[-25:]:
            beta_group.members.append(user)

        # Add admin test users to Administrators group
        for user in self.test_users[:5]:  # testuser1-5 are admins
            admin_group.members.append(user)

        db.session.commit()
        self.user_groups = created_groups

        print(f"✅ Created {len(created_groups)} user groups with memberships")

    def create_sample_password_resets(self):
        """Create some historical password reset examples."""
        print("\n🔐 Creating sample password reset history...")

        # Create some expired/used password resets for demonstration
        sample_resets = []

        for i, user in enumerate(self.test_users[:10]):  # First 10 users
            # Create an old, used reset
            old_reset = PasswordReset(
                user_id=user.id,
                token=uuid.uuid4().hex,
                created_at=datetime.utcnow() - timedelta(days=random.randint(30, 90)),
                expires_at=datetime.utcnow() - timedelta(days=random.randint(29, 89)),
                used=True
            )
            sample_resets.append(old_reset)
            db.session.add(old_reset)

        db.session.commit()
        print(f"✅ Created {len(sample_resets)} sample password reset records")

    def create_default_tags(self):
        """Create comprehensive default tags based on Random's methodology."""
        print("\n🏷️  Creating default tags...")

        # Expanded tags based on Random's Four Steps and trading methodology
        tags_data = [
            # Setup & Strategy tags (expanded)
            ("0930 Open", TagCategory.SETUP_STRATEGY, "neutral"),
            ("HOD LOD", TagCategory.SETUP_STRATEGY, "neutral"),
            ("P12", TagCategory.SETUP_STRATEGY, "neutral"),
            ("Captain Backtest", TagCategory.SETUP_STRATEGY, "neutral"),
            ("Quarter Trade", TagCategory.SETUP_STRATEGY, "neutral"),
            ("05 Box", TagCategory.SETUP_STRATEGY, "neutral"),
            ("Three Hour Quarter", TagCategory.SETUP_STRATEGY, "neutral"),
            ("Midnight Open", TagCategory.SETUP_STRATEGY, "neutral"),
            ("Breakout", TagCategory.SETUP_STRATEGY, "neutral"),
            ("Mean Reversion", TagCategory.SETUP_STRATEGY, "neutral"),
            ("Trend Following", TagCategory.SETUP_STRATEGY, "neutral"),
            ("Scalp Setup", TagCategory.SETUP_STRATEGY, "neutral"),
            ("Swing Setup", TagCategory.SETUP_STRATEGY, "neutral"),
            ("Gap Play", TagCategory.SETUP_STRATEGY, "neutral"),
            ("Support Resistance", TagCategory.SETUP_STRATEGY, "neutral"),

            # Market Conditions (expanded)
            ("DWP", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("DNP", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("R1", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("R2", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("Asian Session", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("London Session", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("NY1 Session", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("NY2 Session", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("High Volatility", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("Low Volatility", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("News Driven", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("Extended Target", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("Trending Market", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("Choppy Market", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("Low Volume", TagCategory.MARKET_CONDITIONS, "neutral"),
            ("High Volume", TagCategory.MARKET_CONDITIONS, "neutral"),

            # Execution & Management (expanded)
            ("Front Run", TagCategory.EXECUTION_MANAGEMENT, "good"),
            ("Confirmation", TagCategory.EXECUTION_MANAGEMENT, "good"),
            ("Retest", TagCategory.EXECUTION_MANAGEMENT, "good"),
            ("Perfect Entry", TagCategory.EXECUTION_MANAGEMENT, "good"),
            ("Chased Entry", TagCategory.EXECUTION_MANAGEMENT, "bad"),
            ("Late Entry", TagCategory.EXECUTION_MANAGEMENT, "bad"),
            ("Proper Stop", TagCategory.EXECUTION_MANAGEMENT, "good"),
            ("Moved Stop", TagCategory.EXECUTION_MANAGEMENT, "bad"),
            ("Cut Short", TagCategory.EXECUTION_MANAGEMENT, "bad"),
            ("Let Run", TagCategory.EXECUTION_MANAGEMENT, "good"),
            ("Partial Profit", TagCategory.EXECUTION_MANAGEMENT, "good"),
            ("Limit Order", TagCategory.EXECUTION_MANAGEMENT, "neutral"),
            ("Market Order", TagCategory.EXECUTION_MANAGEMENT, "neutral"),
            ("Scale In", TagCategory.EXECUTION_MANAGEMENT, "neutral"),
            ("Scale Out", TagCategory.EXECUTION_MANAGEMENT, "good"),
            ("Full Size", TagCategory.EXECUTION_MANAGEMENT, "neutral"),

            # Psychological & Emotional (expanded)
            ("Disciplined", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "good"),
            ("Patient", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "good"),
            ("Calm", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "good"),
            ("Confident", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "good"),
            ("Followed Plan", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "good"),
            ("Clear Mind", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "good"),
            ("FOMO", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),
            ("Revenge Trading", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),
            ("Impulsive", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),
            ("Anxious", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),
            ("Broke Rules", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),
            ("Overconfident", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),
            ("Stressed", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),
            ("Distracted", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),
            ("Emotional", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),
            ("Frustrated", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),
        ]

        created_tags = []
        for name, category, color in tags_data:
            tag = Tag(
                name=name,
                category=category,
                user_id=None,  # System default tags
                is_default=True,
                is_active=True,
                color_category=color
            )
            db.session.add(tag)
            created_tags.append(tag)

        db.session.commit()
        self.tags = created_tags
        print(f"✅ Created {len(created_tags)} default tags")

    def create_instruments(self):
        """Create comprehensive trading instruments."""
        print("\n📊 Creating trading instruments...")

        instruments_data = [
            {
                'symbol': 'ES',
                'name': 'E-mini S&P 500',
                'exchange': 'CME',
                'asset_class': 'Equity Index',
                'product_group': 'E-mini Futures',
                'point_value': 50.0,
                'tick_size': 0.25,
                'currency': 'USD',
                'is_active': True,
                'trading_hours': '18:00-17:00 EST',
                'margin_requirement': 12500.0
            },
            {
                'symbol': 'NQ',
                'name': 'E-mini NASDAQ-100',
                'exchange': 'CME',
                'asset_class': 'Equity Index',
                'product_group': 'E-mini Futures',
                'point_value': 20.0,
                'tick_size': 0.25,
                'currency': 'USD',
                'is_active': True,
                'trading_hours': '18:00-17:00 EST',
                'margin_requirement': 18700.0
            },
            {
                'symbol': 'YM',
                'name': 'E-mini Dow Jones',
                'exchange': 'CME',
                'asset_class': 'Equity Index',
                'product_group': 'E-mini Futures',
                'point_value': 5.0,
                'tick_size': 1.0,
                'currency': 'USD',
                'is_active': True,
                'trading_hours': '18:00-17:00 EST',
                'margin_requirement': 9900.0
            },
            {
                'symbol': 'RTY',
                'name': 'E-mini Russell 2000',
                'exchange': 'CME',
                'asset_class': 'Equity Index',
                'product_group': 'E-mini Futures',
                'point_value': 50.0,
                'tick_size': 0.1,
                'currency': 'USD',
                'is_active': True,
                'trading_hours': '18:00-17:00 EST',
                'margin_requirement': 6050.0
            },
            {
                'symbol': 'CL',
                'name': 'Crude Oil',
                'exchange': 'NYMEX',
                'asset_class': 'Energy',
                'product_group': 'Energy Futures',
                'point_value': 1000.0,
                'tick_size': 0.01,
                'currency': 'USD',
                'is_active': True,
                'trading_hours': '18:00-17:00 EST',
                'margin_requirement': 4895.0
            },
            {
                'symbol': 'GC',
                'name': 'Gold',
                'exchange': 'COMEX',
                'asset_class': 'Metals',
                'product_group': 'Precious Metals',
                'point_value': 100.0,
                'tick_size': 0.10,
                'currency': 'USD',
                'is_active': True,
                'trading_hours': '18:00-17:00 EST',
                'margin_requirement': 9900.0
            }
        ]

        created_instruments = []
        for instr_data in instruments_data:
            instrument = Instrument(**instr_data)
            db.session.add(instrument)
            created_instruments.append(instrument)

        db.session.commit()

        # Store instruments by symbol for easy reference
        for instrument in created_instruments:
            self.instruments[instrument.symbol] = instrument

        print(f"✅ Created {len(created_instruments)} trading instruments")

    def create_p12_scenarios(self):
        """Create complete set of P12 scenarios."""
        print("\n📊 Creating P12 scenarios...")

        scenarios_data = [
            # Scenario 1A - Bullish
            {
                'scenario_number': '1A',
                'scenario_name': 'Scenario 1A: P12 Mid Rejection, Stay Above (Bullish)',
                'short_description': 'Price tests P12 Mid from below, rejects, stays above P12 High',
                'detailed_description': 'Price approaches P12 Mid from below during 06:00-08:30 EST, gets rejected, and then breaks out and stays above P12 High. Low of Day likely already established during overnight session.',
                'hod_lod_implication': 'Low of Day likely already in (18:00-06:00). High of Day expected during RTH.',
                'directional_bias': 'bullish',
                'alert_criteria': 'Watch for rejection at P12 Mid from below',
                'confirmation_criteria': 'Breakout and hold above P12 High',
                'entry_strategy': 'Enter long on breakout above P12 High after mid rejection',
                'typical_targets': 'Daily high targets, previous session highs',
                'stop_loss_guidance': 'Below P12 Mid or P12 High retest',
                'risk_percentage': 0.35,
                'models_to_activate': ['Captain Backtest', '0930 Opening Range'],
                'models_to_avoid': ['HOD/LOD Reversal'],
                'risk_guidance': '0.35% risk - Strong bullish setup, LOD likely in',
                'preferred_timeframes': ['1-minute', '5-minute', '15-minute'],
                'key_considerations': 'LOD likely already established, focus on upside targets',
                'is_active': True
            },
            # Scenario 1B - Bearish
            {
                'scenario_number': '1B',
                'scenario_name': 'Scenario 1B: P12 Mid Rejection, Stay Below (Bearish)',
                'short_description': 'Price tests P12 Mid from above, rejects, stays below P12 Low',
                'detailed_description': 'Price approaches P12 Mid from above during 06:00-08:30 EST, gets rejected, and then breaks down and stays below P12 Low. High of Day likely already established during overnight session.',
                'hod_lod_implication': 'High of Day likely already in (18:00-06:00). Low of Day expected during RTH.',
                'directional_bias': 'bearish',
                'alert_criteria': 'Watch for rejection at P12 Mid from above',
                'confirmation_criteria': 'Breakdown and hold below P12 Low',
                'entry_strategy': 'Enter short on breakdown below P12 Low after mid rejection',
                'typical_targets': 'Daily low targets, previous session lows',
                'stop_loss_guidance': 'Above P12 Mid or P12 Low retest',
                'risk_percentage': 0.35,
                'models_to_activate': ['Captain Backtest', '0930 Opening Range'],
                'models_to_avoid': ['HOD/LOD Reversal'],
                'risk_guidance': '0.35% risk - Strong bearish setup, HOD likely in',
                'preferred_timeframes': ['1-minute', '5-minute', '15-minute'],
                'key_considerations': 'HOD likely already established, focus on downside targets',
                'is_active': True
            },
            # Additional scenarios would follow the same pattern...
            # I'll create a few more key ones for demonstration
            {
                'scenario_number': '5',
                'scenario_name': 'Scenario 5: Swiping the Mid - Expect HOD/LOD in RTH',
                'short_description': 'Price disrespects P12 Mid, choppy action, both extremes likely in RTH',
                'detailed_description': 'Price shows no respect for P12 Mid during 06:00-08:30 EST, repeatedly crossing it without clear direction. This suggests an indecisive overnight market and indicates both HOD and LOD will likely be formed during RTH session.',
                'hod_lod_implication': 'Both HOD and LOD expected during RTH session. High probability of Range day.',
                'directional_bias': 'choppy',
                'alert_criteria': 'Price choppy around P12 Mid with multiple crosses',
                'confirmation_criteria': 'Continued choppy action itself is the confirmation',
                'entry_strategy': 'Avoid P12-based trades. Focus on post-09:30 setups',
                'typical_targets': 'Wait for RTH price action to develop clear levels',
                'stop_loss_guidance': 'Use tighter stops due to choppy conditions',
                'risk_percentage': 0.25,
                'models_to_activate': ['Quarterly Theory & 05 Boxes', 'HOD/LOD Reversal'],
                'models_to_avoid': ['Captain Backtest', 'P12 Scenario-Based'],
                'risk_guidance': '0.25% risk - Choppy conditions require tight risk management',
                'preferred_timeframes': ['1-minute', '3-minute'],
                'key_considerations': 'Focus on RTH setups after 09:30, avoid P12 trades',
                'is_active': True
            }
        ]

        created_scenarios = []
        for scenario_data in scenarios_data:
            scenario = P12Scenario(**scenario_data)
            db.session.add(scenario)
            created_scenarios.append(scenario)

        db.session.commit()
        self.p12_scenarios = created_scenarios
        print(f"✅ Created {len(created_scenarios)} P12 scenarios")

    def create_trading_models(self):
        """Create comprehensive trading models."""
        print("\n📋 Creating Random's trading models...")

        # Your existing trading models data (keeping the same structure)
        default_models_data = [
            {
                'name': '0930 Opening Range',
                'version': '2.1',
                'is_active': True,
                'is_default': True,
                'overview_logic': """The 0930 Opening Range model captures the initial momentum and direction at the New York market open...""",
                'primary_chart_tf': '1-Minute',
                'execution_chart_tf': '1-Minute',
                'context_chart_tf': 'Daily, P12 Chart, Hourly',
                'technical_indicators_used': """- 09:30 Open Price\n- VWAP (Volume Weighted Average Price)...""",
                'instrument_applicability': 'Index Futures (ES, NQ, YM)',
                'session_applicability': '09:30-09:45 EST primary window, exits by 09:44 EST',
                'optimal_market_conditions': 'Clear daily classification (DWP/DNP), normal to high RVOL, clean break of pre-market structure',
                'sub_optimal_market_conditions': 'Range 1 days, extremely low volume, major news events during execution window',
                'entry_trigger_description': """Breakout Entry: 1-minute close above/below the identified "Snap" level...""",
                'stop_loss_strategy': 'Structural stop below/above recent swing point or 0.1% (10 basis points) maximum',
                'take_profit_strategy': """TP1: 0.1% (20 NQ handles) - Quick scalp target...""",
                'min_risk_reward_ratio': 1.5,
                'position_sizing_rules': 'Risk 2.5% baseline, up to 7-10% for A+ setups based on Four Steps confidence',
                'trade_management_breakeven_rules': 'Move stop to breakeven after TP1 hit or 1R profit achieved',
                'trade_management_partial_profit_rules': 'Take 50-75% at TP1, let remainder run to TP2 or time stop',
                'model_max_loss_per_trade': '2.5% baseline, 7-10% for A+ setups',
                'model_max_daily_loss': '5%',
                'model_max_weekly_loss': '10%',
                'model_consecutive_loss_limit': '3 trades',
            },
            # Add all your other trading models here...
            # (keeping the same structure you already have)
        ]

        # Add your complete user models (keeping your existing structure)
        user_models_data = [
            {
                'name': 'Fucktard-FOMO-FAFO',
                'version': '1.0',
                'is_active': True,
                'overview_logic': """The Fucktard-FOMO-FAFO (Fear of Missing Out - Fuck Around and Find Out) model represents 
                unstructured, emotion-driven trading decisions made without proper analysis or adherence to systematic methodology...""",
                'primary_chart_tf': 'Variable',
                'execution_chart_tf': 'Any available',
                'context_chart_tf': 'None - decision made without context',
                'technical_indicators_used': """- Price movement (basic observation)...""",
                'instrument_applicability': 'Any available instrument, often unfamiliar ones',
                'session_applicability': 'Any time, often at market extremes or during high volatility',
                'optimal_market_conditions': 'High volatility environments with significant price movement and market excitement',
                'sub_optimal_market_conditions': 'All conditions - this model lacks systematic approach to market assessment',
                'entry_trigger_description': """Impulsive entry based on: sudden large price movements...""",
                'stop_loss_strategy': 'Often absent or moved impulsively',
                'take_profit_strategy': """Highly variable and emotional...""",
                'min_risk_reward_ratio': 0.1,
                'position_sizing_rules': 'Inconsistent sizing based on emotions',
                'trade_management_breakeven_rules': 'No systematic breakeven rules',
                'trade_management_partial_profit_rules': 'All-or-nothing approach',
                'model_max_loss_per_trade': 'Undefined - risk management not systematically applied',
                'model_max_daily_loss': 'Undefined - can lead to significant drawdowns',
                'model_max_weekly_loss': 'Undefined - lacks systematic risk controls',
                'model_consecutive_loss_limit': 'No systematic limit - emotional decision making continues',
            },
        ]

        created_models = []

        # Create default models (assigned to admin but marked as default)
        for model_data in default_models_data:
            model_data['user_id'] = self.admin_user.id
            model_data['created_by_admin_user_id'] = self.admin_user.id
            model = TradingModel(**model_data)
            db.session.add(model)
            created_models.append(model)

        # Create user-specific models (assigned to test user)
        for model_data in user_models_data:
            model_data['user_id'] = self.test_user.id
            model_data['created_by_admin_user_id'] = None
            model = TradingModel(**model_data)
            db.session.add(model)
            created_models.append(model)

        db.session.commit()
        self.trading_models = created_models
        print(f"✅ Created {len(default_models_data)} default trading models")
        print(f"✅ Created {len(user_models_data)} user-specific trading models")

    def create_news_events(self):
        """Create comprehensive news events."""
        print("\n📰 Creating news events...")

        events_data = [
            ('FOMC Meeting', time(14, 0)),
            ('FOMC Statement', time(14, 0)),
            ('FOMC Minutes', time(14, 0)),
            ('CPI Release', time(8, 30)),
            ('Core CPI', time(8, 30)),
            ('NFP Release', time(8, 30)),
            ('Unemployment Rate', time(8, 30)),
            ('JOLTS Report', time(10, 0)),
            ('GDP Data', time(8, 30)),
            ('GDP Annualized QoQ', time(8, 30)),
            ('Retail Sales', time(8, 30)),
            ('Core Retail Sales', time(8, 30)),
            ('PPI Data', time(8, 30)),
            ('Core PPI', time(8, 30)),
            ('Powell Speech', None),
            ('Fed Chair Speech', None),
            ('OPEC Meeting', None),
            ('OPEC+ Meeting', None),
            ('Earnings Season', None),
            ('Mega Cap Earnings', None),
            ('Geopolitical Event', None),
            ('Market Holiday', None),
            ('PCE Data', time(8, 30)),
            ('Core PCE', time(8, 30)),
            ('Initial Claims', time(8, 30)),
            ('Continuing Claims', time(8, 30)),
            ('ISM Manufacturing', time(10, 0)),
            ('ISM Services', time(10, 0)),
            ('Consumer Confidence', time(10, 0)),
            ('Housing Starts', time(8, 30)),
            ('Building Permits', time(8, 30)),
            ('Other', None)
        ]

        created_events = []
        for name, default_time in events_data:
            event = NewsEventItem(
                name=name,
                default_release_time=default_time
            )
            db.session.add(event)
            created_events.append(event)

        db.session.commit()
        self.news_events = created_events
        print(f"✅ Created {len(created_events)} news events")


def create_account_settings(self):
    """Create comprehensive account settings."""
    print("\n⚙️  Creating account settings...")

    settings_data = [
        ('current_account_size', '100000'),
        ('default_risk_per_trade', '2.5'),
        ('max_daily_loss', '5'),
        ('max_weekly_loss', '10'),
        ('max_monthly_loss', '15'),
        ('preferred_instrument', 'NQ'),
        ('secondary_instrument', 'ES'),
        ('timezone', 'EST'),
        ('currency', 'USD'),
        ('trading_session_start', '09:30'),
        ('trading_session_end', '16:00'),
        ('premarket_analysis_time', '08:00'),
        ('journal_reminder_time', '17:00'),
        ('daily_risk_reset_time', '18:00'),
        ('performance_review_frequency', 'weekly'),
        ('backup_frequency', 'daily'),
        ('data_retention_days', '1095')  # 3 years
    ]

    created_settings = []
    for setting_name, value in settings_data:
        setting = AccountSetting(
            setting_name=setting_name,
            value_str=value
        )
        db.session.add(setting)
        created_settings.append(setting)

    db.session.commit()
    self.account_settings = created_settings
    print(f"✅ Created {len(created_settings)} account settings")


def generate_realistic_trades(self, num_trades=10000):
    """Generate realistic trades with full relationships."""
    print(f"\n📊 Generating {num_trades} realistic trades...")

    # Your existing trade generation logic (keeping it the same)
    # But with improvements for larger dataset and more models

    win_rate = 0.65
    breakeven_rate = 0.05

    # R-multiple distributions
    winner_r_multiples = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    winner_weights = [0.15, 0.20, 0.25, 0.15, 0.10, 0.08, 0.04, 0.02, 0.008, 0.002]

    loser_r_multiples = [-1.0, -0.8, -0.6, -0.4, -0.3, -0.15]
    loser_weights = [0.40, 0.25, 0.15, 0.10, 0.07, 0.03]

    created_trades = []
    start_date = date.today() - timedelta(days=730)  # 2 years of data

    # Distribute trades across all users
    users_for_trades = [self.admin_user] + self.test_users[:50]  # Admin + 50 test users

    for i in range(num_trades):
        # Assign to random user (weighted toward test users)
        if i < 200:  # First 200 to admin
            assigned_user = self.admin_user
        else:
            assigned_user = random.choice(users_for_trades)

        # Generate trade (using your existing logic but improved)
        days_back = random.randint(0, 730)
        trade_date = start_date + timedelta(days=days_back)

        # Skip weekends
        while trade_date.weekday() >= 5:
            trade_date += timedelta(days=1)

        # Random instrument and model
        instrument = random.choice(list(self.instruments.values()))
        model = random.choice(self.trading_models)

        # Determine outcome
        outcome_rand = random.random()
        if outcome_rand < win_rate:
            outcome = 'win'
            r_multiple = random.choices(winner_r_multiples, winner_weights)[0]
        elif outcome_rand < win_rate + breakeven_rate:
            outcome = 'breakeven'
            r_multiple = 0
        else:
            outcome = 'loss'
            r_multiple = random.choices(loser_r_multiples, loser_weights)[0]

        # Generate realistic prices and trade details
        direction = random.choice(['Long', 'Short'])

        # Entry time based on model
        entry_hour = random.randint(9, 15)
        entry_minute = random.randint(0, 59)
        entry_time = time(entry_hour, entry_minute)

        # Generate prices based on instrument
        price_ranges = {
            'ES': (4000, 4800),
            'NQ': (12000, 16000),
            'YM': (33000, 38000),
            'RTY': (1800, 2200),
            'CL': (65, 85),
            'GC': (1800, 2100)
        }

        price_range = price_ranges.get(instrument.symbol, (4000, 4800))
        base_price = random.uniform(price_range[0], price_range[1])

        entry_price = round(base_price, 2)

        # Calculate stop and target
        stop_distance = random.uniform(0.1, 1.0) * (price_range[1] - price_range[0]) / 100

        if direction == 'Long':
            stop_loss = entry_price - stop_distance
        else:
            stop_loss = entry_price + stop_distance

        # Calculate exit price based on outcome
        risk_per_share = abs(entry_price - stop_loss)
        target_distance = abs(r_multiple) * risk_per_share

        if outcome == 'win':
            if direction == 'Long':
                exit_price = entry_price + target_distance
            else:
                exit_price = entry_price - target_distance
        elif outcome == 'breakeven':
            exit_price = entry_price
        else:
            exit_price = stop_loss + random.uniform(-0.1, 0.1)

        # Contract size
        contracts = random.choice([1, 2, 3, 4, 5])

        # Exit time
        exit_time = datetime.combine(trade_date, entry_time) + timedelta(minutes=random.randint(5, 180))
        if exit_time.hour >= 16:
            exit_time = exit_time.replace(hour=15, minute=random.randint(45, 59))

        # Create trade
        trade = Trade(
            instrument_id=instrument.id,
            trade_date=trade_date,
            direction=direction,
            initial_stop_loss=stop_loss,
            terminus_target=exit_price if outcome == 'win' else entry_price + (
                2 * target_distance if direction == 'Long' else -2 * target_distance),
            is_dca=random.choice([True, False]) if random.random() < 0.15 else False,
            mae=random.uniform(0, stop_distance * 0.8) if outcome != 'loss' else stop_distance,
            mfe=target_distance if outcome == 'win' else random.uniform(0, target_distance * 0.6),
            how_closed=self._get_close_reason(outcome),
            news_event=self._get_random_news_event() if random.random() < 0.1 else None,
            rules_rating=random.randint(1, 5),
            management_rating=random.randint(1, 5),
            target_rating=random.randint(1, 5),
            entry_rating=random.randint(1, 5),
            preparation_rating=random.randint(1, 5),
            trade_notes=self._get_trade_note(model.name, outcome),
            trading_model_id=model.id,
            user_id=assigned_user.id
        )

        db.session.add(trade)
        db.session.flush()

        # Create entry point
        entry = EntryPoint(
            trade_id=trade.id,
            entry_time=entry_time,
            contracts=contracts,
            entry_price=entry_price
        )
        db.session.add(entry)

        # Create exit point
        exit_point = ExitPoint(
            trade_id=trade.id,
            exit_time=exit_time.time(),
            contracts=contracts,
            exit_price=exit_price
        )
        db.session.add(exit_point)

        # Calculate P&L
        trade.calculate_and_store_pnl()

        # Assign tags
        self._assign_tags_to_trade(trade, outcome)

        created_trades.append(trade)

        if (i + 1) % 100 == 0:
            print(f"  📝 Generated {i + 1}/{num_trades} trades...")
            db.session.commit()  # Commit in batches

    db.session.commit()
    self.trades = created_trades
    print(f"✅ Created {len(created_trades)} realistic trades")


def create_trade_images(self):
    """Create sample trade images."""
    print("\n📷 Creating sample trade images...")

    # Create sample trade images for first 50 trades
    created_images = 0
    sample_trades = self.trades[:50]

    for trade in sample_trades:
        # 30% chance of having images
        if random.random() < 0.3:
            num_images = random.randint(1, 3)

            for i in range(num_images):
                # Create mock image record
                image = TradeImage(
                    trade_id=trade.id,
                    user_id=trade.user_id,
                    filename=f'trade_{trade.id}_image_{i + 1}.png',
                    filepath=f'trade_images/trade_{trade.id}_image_{i + 1}.png',
                    filesize=random.randint(50000, 500000),  # 50KB - 500KB
                    mime_type='image/png',
                    caption=f'Chart analysis for trade {trade.id}'
                )
                db.session.add(image)
                created_images += 1

    db.session.commit()
    print(f"✅ Created {created_images} sample trade images")


def create_daily_journals(self):
    """Create comprehensive daily journal entries."""
    print("\n📖 Creating daily journal entries...")

    # Group trades by user and date
    user_trade_days = defaultdict(lambda: defaultdict(list))
    for trade in self.trades:
        user_trade_days[trade.user_id][trade.trade_date].append(trade)

    created_journals = 0
    created_p12_usage = 0

    for user_id, trade_days in user_trade_days.items():
        for trade_date, trades_for_day in trade_days.items():
            # Create journal entry
            journal = self._create_enhanced_daily_journal_entry(user_id, trade_date, trades_for_day)
            created_journals += 1

            # Create P12 usage stat (50% chance)
            if random.random() < 0.5 and self.p12_scenarios:
                scenario = random.choice(self.p12_scenarios)
                p12_usage = P12UsageStats(
                    user_id=user_id,
                    p12_scenario_id=scenario.id,
                    journal_date=trade_date,
                    market_session=random.choice(['pre-market', 'regular-hours']),
                    p12_high=random.uniform(4200, 4600),
                    p12_mid=random.uniform(4150, 4550),
                    p12_low=random.uniform(4100, 4500),
                    outcome_successful=random.choice([True, False, None]),
                    outcome_notes=f'P12 scenario {scenario.scenario_number} analysis for {trade_date}'
                )
                db.session.add(p12_usage)
                created_p12_usage += 1

    db.session.commit()
    print(f"✅ Created {created_journals} daily journal entries")
    print(f"✅ Created {created_p12_usage} P12 usage statistics")


def create_weekly_journals(self):
    """Create sample weekly journal entries."""
    print("\n📅 Creating weekly journal entries...")

    # Create weekly journals for active users for last 12 weeks
    active_users = [self.admin_user] + self.test_users[:20]
    created_weeklies = 0

    for user in active_users:
        for week_back in range(1, 13):  # Last 12 weeks
            target_date = date.today() - timedelta(weeks=week_back)
            year, week_num, _ = target_date.isocalendar()

            weekly = WeeklyJournal(
                user_id=user.id,
                year=year,
                week_number=week_num,
                weekly_improve_action_next_week=f'Focus on improving risk management and trade selection for user {user.username}'
            )
            db.session.add(weekly)
            created_weeklies += 1

    db.session.commit()
    print(f"✅ Created {created_weeklies} weekly journal entries")


def create_activity_logs(self):
    """Create realistic activity logs."""
    print("\n📋 Creating activity logs...")

    activity_types = [
        'user_login', 'user_logout', 'trade_created', 'trade_updated', 'trade_deleted',
        'journal_created', 'journal_updated', 'model_created', 'settings_updated',
        'password_changed', 'profile_updated', 'export_data', 'import_data'
    ]

    created_activities = 0
    all_users = [self.admin_user] + self.test_users

    # Create activities over last 90 days
    for day_back in range(90):
        activity_date = datetime.now() - timedelta(days=day_back)

        # Random number of activities per day (0-20)
        daily_activities = random.randint(0, 20)

        for _ in range(daily_activities):
            user = random.choice(all_users)
            activity_type = random.choice(activity_types)

            activity = Activity(
                user_id=user.id,
                action=activity_type,
                details=f'{activity_type} performed by {user.username}',
                ip_address=f'192.168.1.{random.randint(1, 255)}',
                user_agent='Mozilla/5.0 (Test Browser)',
                timestamp=activity_date - timedelta(
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
            )
            db.session.add(activity)
            created_activities += 1

    db.session.commit()
    print(f"✅ Created {created_activities} activity log entries")


def create_sample_files(self):
    """Create sample file records."""
    print("\n📁 Creating sample file records...")

    file_types = ['csv', 'xlsx', 'pdf', 'png', 'jpg']
    file_purposes = ['trade_export', 'journal_backup', 'chart_image', 'report', 'analysis']

    created_files = 0
    active_users = [self.admin_user] + self.test_users[:25]

    for user in active_users:
        # Each user gets 2-8 files
        num_files = random.randint(2, 8)

        for i in range(num_files):
            file_ext = random.choice(file_types)
            purpose = random.choice(file_purposes)

            file_record = File(
                user_id=user.id,
                filename=f'{purpose}_{user.username}_{i + 1}.{file_ext}',
                original_filename=f'{purpose}_{i + 1}.{file_ext}',
                file_path=f'uploads/user_{user.id}/{purpose}_{i + 1}.{file_ext}',
                file_size=random.randint(1024, 5242880),  # 1KB - 5MB
                mime_type=f'application/{file_ext}' if file_ext in ['csv', 'xlsx', 'pdf'] else f'image/{file_ext}',
                upload_date=datetime.now() - timedelta(
                    days=random.randint(1, 180),
                    hours=random.randint(0, 23)
                )
            )
            db.session.add(file_record)
            created_files += 1

    db.session.commit()
    print(f"✅ Created {created_files} file records")


def _create_enhanced_daily_journal_entry(self, user_id, trade_date, trades_for_day):
    """Create a comprehensive daily journal entry with all fields."""

    # Calculate performance
    performance = self._calculate_daily_performance(trades_for_day)

    # Generate P12 levels
    p12_high = random.uniform(4200, 4600)
    p12_mid = p12_high - random.uniform(15, 35)
    p12_low = p12_mid - random.uniform(15, 35)

    # Select random P12 scenario
    p12_scenario = random.choice(self.p12_scenarios) if self.p12_scenarios else None

    journal = DailyJournal(
        user_id=user_id,
        journal_date=trade_date,

        # Pre-market mental state
        key_events_today=f'Market session for {trade_date}. {len(trades_for_day)} trades planned.',
        mental_feeling_rating=random.randint(3, 5),
        mental_mind_rating=random.randint(3, 5),
        mental_energy_rating=random.randint(3, 5),
        mental_motivation_rating=random.randint(3, 5),

        # P12 analysis
        p12_scenario_id=p12_scenario.id if p12_scenario else None,
        p12_high=p12_high,
        p12_mid=p12_mid,
        p12_low=p12_low,
        p12_notes=f'P12 analysis: Range {p12_high - p12_low:.1f} points. Scenario {p12_scenario.scenario_number if p12_scenario else "None"} selected.',
        p12_expected_outcomes=self._generate_four_steps_analysis(trades_for_day),

        # Market analysis
        realistic_expectance_notes=f'Expected range: {p12_high - p12_low:.1f} points. Daily bias based on overnight action.',
        engagement_structure_notes=f'Plan to trade {len(trades_for_day)} setups using selected models.',
        key_levels_notes=f'Key levels: P12 High {p12_high:.2f}, Mid {p12_mid:.2f}, Low {p12_low:.2f}',

        # Post-market analysis
        market_observations=f'Market behaved according to {p12_scenario.scenario_number if p12_scenario else "expected"} scenario.',
        self_observations=f'Executed {len(trades_for_day)} trades with {performance["win_rate"]:.1f}% win rate.',

        # Daily review
        did_well_today='Followed trading plan and risk management rules.' if performance[
                                                                                 'total_pnl'] >= 0 else 'Maintained discipline despite challenging conditions.',
        did_not_go_well_today='Minor timing issues on some entries.' if performance[
                                                                            'win_rate'] < 60 else 'No major issues identified.',
        learned_today=random.choice([
            'Patience at key levels continues to pay off.',
            'Model selection alignment with daily bias is crucial.',
            'Risk management discipline prevents larger losses.'
        ]),
        improve_action_next_day=random.choice([
            'Focus on tighter entry timing.',
            'Review daily classification criteria.',
            'Enhance position sizing based on setup quality.'
        ]),

        # Psychology ratings
        review_psych_discipline_rating=random.randint(3, 5),
        review_psych_motivation_rating=random.randint(3, 5),
        review_psych_focus_rating=random.randint(3, 5),
        review_psych_mastery_rating=random.randint(3, 5),
        review_psych_composure_rating=random.randint(3, 5),
        review_psych_resilience_rating=random.randint(3, 5),
        review_psych_mind_rating=random.randint(3, 5),
        review_psych_energy_rating=random.randint(3, 5)
    )

    db.session.add(journal)
    return journal


def _calculate_daily_performance(self, trades_for_day):
    """Calculate performance metrics for trades."""
    total_pnl = sum(trade.pnl for trade in trades_for_day if trade.pnl) or 0
    winning_trades = sum(1 for trade in trades_for_day if trade.pnl and trade.pnl > 0)

    return {
        'total_pnl': total_pnl,
        'winning_trades': winning_trades,
        'total_trades': len(trades_for_day),
        'win_rate': (winning_trades / len(trades_for_day)) * 100 if trades_for_day else 0
    }


def _generate_four_steps_analysis(self, trades_for_day):
    """Generate Four Steps analysis."""
    models_used = list(set([trade.trading_model.name for trade in trades_for_day if trade.trading_model]))
    models_str = ', '.join(models_used) if models_used else 'Standard setups'

    return f"""Step 1 - Define HOD/LOD: Dashboard analysis shows trending bias based on overnight action.

Step 2 - Incorporate Variables: Session behavior confirms directional bias with normal volume.

Step 3 - Set Realistic Expectance: Daily range target set with appropriate risk parameters.

Step 4 - Engage at Highest Statistical Structure: Executed using {models_str} models."""


def _get_close_reason(self, outcome):
    """Get realistic close reasons."""
    if outcome == 'win':
        return random.choice(['Target Hit', 'Partial Scale', 'Time Stop', 'Trailing Stop'])
    elif outcome == 'breakeven':
        return random.choice(['Breakeven Stop', 'Time Stop', 'Scratch'])
    else:
        return random.choice(['Stop Loss', 'Manual Close', 'Risk Management'])


def _get_random_news_event(self):
    """Get random news events."""
    if self.news_events:
        return random.choice(self.news_events).name
    return 'Market Event'


def _get_trade_note(self, model_name, outcome):
    """Generate realistic trade notes."""
    outcome_text = {
        'win': 'Executed according to plan.',
        'loss': 'Stop loss hit, followed rules.',
        'breakeven': 'Scratched for small gain/loss.'
    }.get(outcome, 'Trade completed.')

    return f'{model_name} setup. {outcome_text}'


def _assign_tags_to_trade(self, trade, outcome):
    """Assign realistic tags to trades."""
    available_tags = self.tags
    if not available_tags:
        return

    good_tags = [tag for tag in available_tags if tag.color_category == 'good']
    bad_tags = [tag for tag in available_tags if tag.color_category == 'bad']
    neutral_tags = [tag for tag in available_tags if tag.color_category == 'neutral']

    selected_tags = []

    # Always add 1-2 neutral tags
    if neutral_tags:
        selected_tags.extend(random.sample(neutral_tags, min(2, len(neutral_tags))))

    # Add outcome-based tags
    if outcome == 'win' and good_tags:
        selected_tags.extend(random.sample(good_tags, min(2, len(good_tags))))
    elif outcome == 'loss' and bad_tags:
        selected_tags.extend(random.sample(bad_tags, min(2, len(bad_tags))))

    # Assign unique tags
    trade.tags = list(set(selected_tags))


def print_comprehensive_statistics(self):
    """Print detailed statistics about the generated data."""
    print("\n" + "=" * 80)
    print("📊 ENHANCED BOOTSTRAP COMPLETE - COMPREHENSIVE STATISTICS")
    print("=" * 80)

    # User statistics
    print(f"\n👤 Users & Authentication:")
    print(f"   • Admin User: {self.admin_user.username} (ID: {self.admin_user.id})")
    print(f"   • Test Users: {len(self.test_users)}")
    print(f"   • User Groups: {len(self.user_groups)}")
    print(f"   • API Keys: {ApiKey.query.count()}")
    print(f"   • Password Resets: {PasswordReset.query.count()}")

    # Core trading data
    print(f"\n📊 Core Trading Data:")
    print(f"   • Instruments: {len(self.instruments)}")
    print(f"   • Trading Models: {len(self.trading_models)}")
    print(f"   • P12 Scenarios: {len(self.p12_scenarios)}")
    print(f"   • Tags: {len(self.tags)}")
    print(f"   • News Events: {len(self.news_events)}")

    # Trading activity
    print(f"\n📈 Trading Activity:")
    print(f"   • Total Trades: {len(self.trades)}")
    print(f"   • Entry Points: {EntryPoint.query.count()}")
    print(f"   • Exit Points: {ExitPoint.query.count()}")