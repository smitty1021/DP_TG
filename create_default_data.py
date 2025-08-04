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

        # Only use fields that actually exist in the User model
        admin_data = {
            'username': 'admin',
            'email': 'admin@tradingjournal.local',
            'name': 'System Administrator',
            'role': UserRole.ADMIN,
            'is_active': True,
            'is_email_verified': True,
            'bio': 'System administrator for the trading journal application.'
            # Remove: timezone, theme_preference, notification_preferences
        }

        admin = User(**admin_data)
        admin.set_password('admin123')  # Change this in production!

        db.session.add(admin)
        db.session.commit()

        # Create default settings for admin in Settings table
        admin_settings = Settings(
            user_id=admin.id,
            theme='dark',  # 'theme' not 'timezone'
            notifications_enabled=True,  # Use correct field name
            items_per_page=20,
            language='en'
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

            # Only use fields that exist in the User model
            test_user_data = {
                'username': f'testuser{i}',
                'email': f'testuser{i}@example.com',
                'name': f'Test User {i}',
                'role': user_role,
                'is_active': is_active,
                'is_email_verified': is_verified,
                'bio': f'Test user account {i} for trading journal application.'
                # Remove: timezone, theme_preference - these go in Settings
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
        themes = ['light', 'dark']

        for user in created_users:
            settings = Settings(
                user_id=user.id,
                theme=random.choice(['light', 'dark']),
                notifications_enabled=random.choice([True, False]),
                items_per_page=random.choice([10, 20, 50]),
                language='en'
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
                'is_active': True
                # Remove: trading_hours, margin_requirement - these fields don't exist
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
                'is_active': True
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
                'is_active': True
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
                'is_active': True
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
                'is_active': True
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
                'is_active': True
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
            # Scenario 1A - Bullish (Low of Day likely already in)
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

            # Scenario 1B - Bearish (High of Day likely already in)
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

            # Scenario 2A - Bullish (Look above and fail, expect reversal up)
            {
                'scenario_number': '2B',
                'scenario_name': 'Scenario 2B: Look Above P12 High and Fail (Bearish Reversal)',
                'short_description': 'Price looks above P12 High then fails, expect low in and reversal up',
                'detailed_description': 'Price initially moves above P12 High but fails to hold and gets sucked back into the P12 range. High of Day likely set by this false breakout, expect reversal to upside.',
                'hod_lod_implication': 'Low of Day likely set by the failed breakout above. Reversal higher expected.',
                'directional_bias': 'bullish reversal',
                'alert_criteria': 'Price moves above P12 High then gets sucked back into range',
                'confirmation_criteria': 'Price closes back inside P12 range and breaks above P12 Mid',
                'entry_strategy': 'Enter long on return inside P12 range, target P12 High and beyond',
                'typical_targets': 'P12 High, then extended upside targets',
                'stop_loss_guidance': 'Below the failed breakout low',
                'risk_percentage': 0.50,
                'models_to_activate': ['HOD/LOD Reversal', 'P12 Scenario-Based'],
                'models_to_avoid': ['Captain Backtest'],
                'risk_guidance': '0.50% risk - Reversal setup after failed breakout',
                'preferred_timeframes': ['5-minute', '15-minute'],
                'key_considerations': 'Wait for clear failure confirmation, LOD likely in',
                'is_active': True
            },

            # Scenario 2B - Bearish (Look below and fail, expect reversal down)
            {
                'scenario_number': '2A',
                'scenario_name': 'Scenario 2A: Look Below P12 Low and Fail (Bearish Reversal)',
                'short_description': 'Price looks below P12 Low then fails, expect high in and reversal down',
                'detailed_description': 'Price initially moves below P12 Low but fails to hold and gets sucked back into the P12 range. Low of Day likely set by this false breakdown, expect reversal to downside.',
                'hod_lod_implication': 'High of Day likely set by the failed breakdown below. Reversal lower expected.',
                'directional_bias': 'bearish reversal',
                'alert_criteria': 'Price moves below P12 Low then gets sucked back into range',
                'confirmation_criteria': 'Price closes back inside P12 range and breaks below P12 Mid',
                'entry_strategy': 'Enter short on return inside P12 range, target P12 Low and beyond',
                'typical_targets': 'P12 Low, then extended downside targets',
                'stop_loss_guidance': 'Above the failed breakdown high',
                'risk_percentage': 0.50,
                'models_to_activate': ['HOD/LOD Reversal', 'P12 Scenario-Based'],
                'models_to_avoid': ['Captain Backtest'],
                'risk_guidance': '0.50% risk - Reversal setup after failed breakdown',
                'preferred_timeframes': ['5-minute', '15-minute'],
                'key_considerations': 'Wait for clear failure confirmation, HOD likely in',
                'is_active': True
            },

            # Scenario 3A - Bullish (Range between Mid and High, then break up)
            {
                'scenario_number': '3A',
                'scenario_name': 'Scenario 3A: Range Mid to High, Break Up (Bullish)',
                'short_description': 'Price ranges between P12 Mid and High, then breaks above High',
                'detailed_description': 'Price consolidates between P12 Mid and P12 High during analysis window, then breaks above P12 High with conviction. Low of Day likely already established.',
                'hod_lod_implication': 'Low of Day likely already in. Breakout suggests bullish continuation.',
                'directional_bias': 'bullish trending',
                'alert_criteria': 'Price ping-ponging between P12 Mid and P12 High',
                'confirmation_criteria': 'Clean breakout above P12 High',
                'entry_strategy': 'Enter long on breakout above consolidation range',
                'typical_targets': 'Extended targets above P12 range, daily highs',
                'stop_loss_guidance': 'Back inside the P12 Mid-High range',
                'risk_percentage': 0.25,
                'models_to_activate': ['Captain Backtest', 'P12 Scenario-Based'],
                'models_to_avoid': ['HOD/LOD Reversal'],
                'risk_guidance': '0.25% risk - Clear bullish breakout setup',
                'preferred_timeframes': ['5-minute', '10-minute'],
                'key_considerations': 'Ensure clean break of consolidation, LOD likely in',
                'is_active': True
            },

            # Scenario 3B - Bearish (Range between Mid and Low, then break down)
            {
                'scenario_number': '3B',
                'scenario_name': 'Scenario 3B: Range Mid to Low, Break Down (Bearish)',
                'short_description': 'Price ranges between P12 Mid and Low, then breaks below Low',
                'detailed_description': 'Price consolidates between P12 Mid and P12 Low during analysis window, then breaks below P12 Low with conviction. High of Day likely already established.',
                'hod_lod_implication': 'High of Day likely already in. Breakdown suggests bearish continuation.',
                'directional_bias': 'bearish trending',
                'alert_criteria': 'Price ping-ponging between P12 Mid and P12 Low',
                'confirmation_criteria': 'Clean breakdown below P12 Low',
                'entry_strategy': 'Enter short on breakdown below consolidation range',
                'typical_targets': 'Extended targets below P12 range, daily lows',
                'stop_loss_guidance': 'Back inside the P12 Mid-Low range',
                'risk_percentage': 0.25,
                'models_to_activate': ['Captain Backtest', 'P12 Scenario-Based'],
                'models_to_avoid': ['HOD/LOD Reversal'],
                'risk_guidance': '0.25% risk - Clear bearish breakdown setup',
                'preferred_timeframes': ['5-minute', '10-minute'],
                'key_considerations': 'Ensure clean break of consolidation, HOD likely in',
                'is_active': True
            },

            # Scenario 4A - Bullish (Breakout and hold above P12 High)
            {
                'scenario_number': '4A',
                'scenario_name': 'Scenario 4A: Stay Outside Above P12 High (Bullish)',
                'short_description': 'Clean breakout above P12 High, level acts as support',
                'detailed_description': 'Price breaks cleanly above P12 High and holds, with P12 High acting as dynamic support on any retests. Strong bullish momentum with Low of Day likely already established.',
                'hod_lod_implication': 'Low of Day likely already in overnight. Strong bullish continuation expected.',
                'directional_bias': 'strongly bullish',
                'alert_criteria': 'Price steps outside and holds above P12 High',
                'confirmation_criteria': 'P12 High acting as support on retests',
                'entry_strategy': 'Enter long on retests of P12 High acting as support',
                'typical_targets': 'Daily extremes, extended bullish targets',
                'stop_loss_guidance': 'Below P12 High with structural confirmation',
                'risk_percentage': 0.25,
                'models_to_activate': ['Captain Backtest', '0930 Opening Range', 'P12 Scenario-Based'],
                'models_to_avoid': ['HOD/LOD Reversal'],
                'risk_guidance': '0.25% risk - High probability bullish continuation',
                'preferred_timeframes': ['1-minute', '5-minute'],
                'key_considerations': 'Strong momentum setup, LOD likely in - size appropriately',
                'is_active': True
            },

            # Scenario 4B - Bearish (Breakout and hold below P12 Low)
            {
                'scenario_number': '4B',
                'scenario_name': 'Scenario 4B: Stay Outside Below P12 Low (Bearish)',
                'short_description': 'Clean breakdown below P12 Low, level acts as resistance',
                'detailed_description': 'Price breaks cleanly below P12 Low and holds, with P12 Low acting as dynamic resistance on any retests. Strong bearish momentum with High of Day likely already established.',
                'hod_lod_implication': 'High of Day likely already in overnight. Strong bearish continuation expected.',
                'directional_bias': 'strongly bearish',
                'alert_criteria': 'Price steps outside and holds below P12 Low',
                'confirmation_criteria': 'P12 Low acting as resistance on retests',
                'entry_strategy': 'Enter short on retests of P12 Low acting as resistance',
                'typical_targets': 'Daily extremes, extended bearish targets',
                'stop_loss_guidance': 'Above P12 Low with structural confirmation',
                'risk_percentage': 0.25,
                'models_to_activate': ['Captain Backtest', '0930 Opening Range', 'P12 Scenario-Based'],
                'models_to_avoid': ['HOD/LOD Reversal'],
                'risk_guidance': '0.25% risk - High probability bearish continuation',
                'preferred_timeframes': ['1-minute', '5-minute'],
                'key_considerations': 'Strong momentum setup, HOD likely in - size appropriately',
                'is_active': True
            },

            # Scenario 5 - Choppy (Swiping the Mid)
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
        """Create Random's 6 core trading models."""
        print("\n📋 Creating Random's trading models...")

        default_models_data = [
            {
                'name': '0930 Opening Range',
                'version': '2.1',
                'is_active': True,
                'is_default': True,
                'overview_logic': """The 0930 Opening Range model captures the initial momentum and direction at the New York market open. 
                Based on Random's Four Steps methodology, this model identifies "Snap" patterns (High, Low, HH/LL) in the first few minutes 
                after 9:30 AM EST. The model can trade either direction (breakout or Return to VWAP) depending on the daily classification 
                (DWP, DNP, Range 1, Range 2) determined through P12 analysis and session behavior assessment.""",

                'primary_chart_tf': '1-Minute',
                'execution_chart_tf': '1-Minute',
                'context_chart_tf': 'Daily, P12 Chart, Hourly',

                'technical_indicators_used': """- 09:30 Open Price
                - VWAP (Volume Weighted Average Price)
                - Previous Day High/Low
                - P12 High/Mid/Low levels
                - ADR (Average Daily Range) for context
                - RVOL (Relative Volume) for confirmation""",

                'instrument_applicability': 'Index Futures (ES, NQ, YM)',
                'session_applicability': '09:30-09:45 EST primary window, exits by 09:44 EST',
                'optimal_market_conditions': 'Clear daily classification (DWP/DNP), normal to high RVOL, clean break of pre-market structure',
                'sub_optimal_market_conditions': 'Range 1 days, extremely low volume, major news events during execution window',

                'entry_trigger_description': """Breakout Entry: 1-minute close above/below the identified "Snap" level (High/Low formed in first 1-3 minutes)
                RTV Entry: Return to VWAP after initial displacement, confirmed by price action
                Entry must align with daily bias from Four Steps analysis""",

                'stop_loss_strategy': 'Structural stop below/above recent swing point or 0.1% (10 basis points) maximum',
                'take_profit_strategy': """TP1: 0.1% (20 NQ handles) - Quick scalp target
                TP2: 50% of 09:30-10:00 session DRO
                Time-based exit: All positions closed by 09:44 EST""",
                'min_risk_reward_ratio': 1.5,

                'position_sizing_rules': 'Risk 2.5% baseline, up to 7-10% for A+ setups based on Four Steps confidence',
                'trade_management_breakeven_rules': 'Move stop to breakeven after TP1 hit or 1R profit achieved',
                'trade_management_partial_profit_rules': 'Take 50-75% at TP1, let remainder run to TP2 or time stop',

                'model_max_loss_per_trade': '2.5% baseline, 7-10% for A+ setups',
                'model_max_daily_loss': '5%',
                'model_max_weekly_loss': '10%',
                'model_consecutive_loss_limit': '3 trades',
            },

            {
                'name': 'HOD/LOD Reversal',
                'version': '1.8',
                'is_active': True,
                'is_default': True,
                'overview_logic': """Mean reversion strategy targeting reversals at the High of Day (HOD) or Low of Day (LOD). 
                Uses Random's Four Steps to identify likely HOD/LOD zones and times, then waits for confirmation signals like 
                059 boxes, hourly momentum changes, or 1-minute rejection patterns. NOT for trend days - requires patience 
                for proper reversal confirmation.""",

                'primary_chart_tf': '1-Minute',
                'execution_chart_tf': '1-Minute',
                'context_chart_tf': 'Daily, Hourly, P12 Chart',

                'technical_indicators_used': """- Dashboard logic for HOD/LOD identification
                - % move from 18:00 open
                - Hourly quarters and 059 boxes
                - Previous session behavior (Asia/London True/False/Broken)
                - ADR and RVOL analysis""",

                'instrument_applicability': 'Index Futures (ES, NQ, YM)',
                'session_applicability': 'Active throughout RTH, best during statistical HOD/LOD times',
                'optimal_market_conditions': 'Range days, broken Asia/London sessions, clear HOD/LOD zones defined',
                'sub_optimal_market_conditions': 'Strong trend days (DWP/DNP), unclear daily structure',

                'entry_trigger_description': """Wait for price to reach defined HOD/LOD zone, then:
                - 1-minute confirmation candle (rejection pattern)
                - Hourly momentum change
                - 059 box formation
                - NOT for catching falling knives - patience required""",

                'stop_loss_strategy': '0.1% (10 basis points) above/below the HOD/LOD zone',
                'take_profit_strategy': """TP1: 50% of NY1 DRO (Daily Range Objective)
                TP2: P12 Mid level
                TP3: Previous Day Mid (PDM) or Settlement""",
                'min_risk_reward_ratio': 2.0,

                'position_sizing_rules': 'Conservative sizing due to reversal nature, 2.5% baseline risk',
                'trade_management_breakeven_rules': 'Move to breakeven after 1R profit or TP1 achievement',
                'trade_management_partial_profit_rules': 'Scale out at TP1, trail stop on remainder',

                'model_max_loss_per_trade': '2.5%',
                'model_max_daily_loss': '5%',
                'model_max_weekly_loss': '8%',
                'model_consecutive_loss_limit': '2 trades',
            },

            {
                'name': 'Captain Backtest',
                'version': '2.3',
                'is_active': True,
                'is_default': True,
                'overview_logic': """Trend-following model designed to capture HOD/LOD by front-running NY2 session. 
                Requires H4 range (06:00-09:59 EST) break by 11:30, followed by pullback and continuation. 
                Higher expectancy but requires trending days (DWP/DNP). Targets 0.50% minimum with potential 
                extension to daily extremes.""",

                'primary_chart_tf': '10-Minute',
                'execution_chart_tf': '10-Minute',
                'context_chart_tf': 'Daily, P12 Chart, Hourly',

                'technical_indicators_used': """- H4 Range (06:00-09:59 EST High/Low)
                - 10-minute pullback patterns
                - Daily Range Objective (DRO) analysis
                - Hourly quarters for fine-tuning entries""",

                'instrument_applicability': 'Index Futures (ES, NQ, YM)',
                'session_applicability': 'Setup after 10:00 EST, entry by 11:30 EST, target 15:00 HOD/LOD',
                'optimal_market_conditions': 'Trending days (DWP/DNP), sufficient daily range available, clean H4 break',
                'sub_optimal_market_conditions': 'Range days, late H4 breaks after 11:30, insufficient DRO remaining',

                'entry_trigger_description': """1. H4 range must be breached by 10-minute close before 11:30 EST
                2. Wait for pullback formation on 10-minute chart
                3. Enter on 10-minute close beyond pullback extreme
                4. Use 05 boxes from hourly quarters for precision if desired""",

                'stop_loss_strategy': '0.25% (25 basis points) or structural level at previous hour 50%',
                'take_profit_strategy': """Minimum: 0.50% (50 basis points)
                Extended: Potential HOD/LOD at 15:00 if daily profile supports
                Partial scaling recommended at minimum target""",
                'min_risk_reward_ratio': 2.0,

                'position_sizing_rules': 'Standard to aggressive sizing for trending setups, 2.5-7% risk range',
                'trade_management_breakeven_rules': 'Move to breakeven after 1R (0.25%) profit',
                'trade_management_partial_profit_rules': 'Take 50% at 0.50% target, trail remainder to HOD/LOD',

                'model_max_loss_per_trade': '5%',
                'model_max_daily_loss': '7%',
                'model_max_weekly_loss': '12%',
                'model_consecutive_loss_limit': '3 trades',
            },

            {
                'name': 'P12 Scenario-Based',
                'version': '1.5',
                'is_active': True,
                'is_default': True,
                'overview_logic': """Uses 12-hour Globex range (18:00-06:00 EST) High/Mid/Low as key structural levels. 
                Observes 06:00-08:30 price action relative to P12 levels to classify into 5 scenarios. 
                Provides bias for HOD/LOD location and probable price path. Trades taken at P12 levels 
                with scenario confirmation.""",

                'primary_chart_tf': '15-Minute',
                'execution_chart_tf': '5-Minute',
                'context_chart_tf': 'Daily, P12 Chart',

                'technical_indicators_used': """- P12 High/Mid/Low levels (18:00-06:00 EST range)
                - 06:00-08:30 scenario analysis window
                - Daily classification integration
                - Quarter level analysis for entries""",

                'instrument_applicability': 'Index Futures (ES, NQ, YM) - Use MQ for Nasdaq analysis',
                'session_applicability': 'Analysis 06:00-08:30, execution after 09:30 EST',
                'optimal_market_conditions': 'Clear P12 scenario development, alignment with daily bias',
                'sub_optimal_market_conditions': 'Unclear scenario, price chopping around P12 levels',

                'entry_trigger_description': """Based on scenario analysis:
                - Above Mid: Target P12 High breakout, expect low of day in
                - Below Mid: Target P12 Low breakdown, expect high of day in
                - Entry on confirmation at P12 levels with quarter precision""",

                'stop_loss_strategy': 'Below/above P12 Mid or relevant P12 level based on scenario',
                'take_profit_strategy': """Next P12 level (High/Mid/Low)
                Scenario-specific targets: 25-75 basis points
                NFP/CPI exception: 50 basis points viable""",
                'min_risk_reward_ratio': 1.5,

                'position_sizing_rules': 'Risk adjusted by scenario confidence, 2.5-10% range',
                'trade_management_breakeven_rules': 'Move to breakeven at 1:1 R:R',
                'trade_management_partial_profit_rules': 'Scale at interim levels, hold runners to final target',

                'model_max_loss_per_trade': '5%',
                'model_max_daily_loss': '8%',
                'model_max_weekly_loss': '12%',
                'model_consecutive_loss_limit': '2 trades',
            },

            {
                'name': 'Quarterly Theory & 05 Boxes',
                'version': '1.2',
                'is_active': True,
                'is_default': True,
                'overview_logic': """Precision entry model using hourly quarter levels and 05 boxes for optimal 
                trade timing. Can be standalone or used to enhance other models. Focuses on statistical 
                reaction points within hourly structures. Emphasizes scaling and precise risk management.""",

                'primary_chart_tf': '1-Minute',
                'execution_chart_tf': '1-Minute',
                'context_chart_tf': 'Hourly, Daily',

                'technical_indicators_used': """- Hourly quarter levels (00, 15, 30, 45 minute marks)
                - 05 boxes (statistical reaction zones)
                - Volume analysis at quarter levels
                - Previous hour structure""",

                'instrument_applicability': 'Index Futures (ES, NQ, YM)',
                'session_applicability': 'Active throughout RTH, best at hourly turn times',
                'optimal_market_conditions': 'Clear hourly structure, normal volume, defined quarter reactions',
                'sub_optimal_market_conditions': 'High volatility news events, extremely low volume',

                'entry_trigger_description': """Entry at quarter levels on:
                - Rejection patterns at 05 boxes
                - Confirmation of hourly direction
                - Volume spike at quarter levels
                - Structure alignment with higher timeframes""",

                'stop_loss_strategy': 'Previous quarter level or 0.15% maximum',
                'take_profit_strategy': """Fixed target: 0.15%
                Scaling option: 50% at 1:1 R:R, trail remainder
                Next quarter level as extended target""",
                'min_risk_reward_ratio': 1.0,

                'position_sizing_rules': 'Conservative due to frequent entries, 1-3% risk per trade',
                'trade_management_breakeven_rules': 'Quick move to breakeven at 0.5R',
                'trade_management_partial_profit_rules': 'Heavy scaling at first target, small runner positions',

                'model_max_loss_per_trade': '3%',
                'model_max_daily_loss': '6%',
                'model_max_weekly_loss': '10%',
                'model_consecutive_loss_limit': '4 trades',
            },

            {
                'name': 'Midnight Open Retracement',
                'version': '1.0',
                'is_active': True,
                'is_default': True,
                'overview_logic': """Statistical retracement model targeting moves back to Midnight Open price. 
                Active 08:00-11:15 EST window. Uses hourly footprints and distribution analysis to identify 
                optimal entry points for mean reversion to Midnight Open level.""",

                'primary_chart_tf': '3-Minute',
                'execution_chart_tf': '1-Minute',
                'context_chart_tf': 'Hourly, Daily',

                'technical_indicators_used': """- Midnight Open price (00:00 EST)
                - Hourly footprints (overlapping wicks)
                - 3-minute distribution analysis
                - Asia Range context
                - RTH Gap measurements""",

                'instrument_applicability': 'Index Futures (ES, NQ, YM)',
                'session_applicability': '08:00-11:15 EST execution window',
                'optimal_market_conditions': 'Clear overextension from Midnight Open, defined hourly footprints',
                'sub_optimal_market_conditions': 'Price near Midnight Open, unclear distribution patterns',

                'entry_trigger_description': """Entry when:
                - Price overextended from Midnight Open
                - Reaction at hourly footprint level
                - Distribution extreme reached (bullish/bearish)
                - 1-minute confirmation of reversal""",

                'stop_loss_strategy': 'Beyond footprint extreme or distribution limit',
                'take_profit_strategy': """Primary: Midnight Open price level
                Statistical: 0.12-0.13% on NASDAQ
                Secondary: Asia Range opposing side or RTH Gap fill""",
                'min_risk_reward_ratio': 1.2,

                'position_sizing_rules': 'Increase size with multiple confluences, 2-7% risk range',
                'trade_management_breakeven_rules': 'Move to breakeven halfway to target',
                'trade_management_partial_profit_rules': 'Scale heavily at Midnight Open, minimal runners',

                'model_max_loss_per_trade': '4%',
                'model_max_daily_loss': '8%',
                'model_max_weekly_loss': '12%',
                'model_consecutive_loss_limit': '3 trades',
            },
        ]

        user_models_data = [
            {
                'name': 'Fucktard-FOMO-FAFO',
                'version': '1.0',
                'is_active': True,
                'overview_logic': """The Fucktard-FOMO-FAFO (Fear of Missing Out - Fuck Around and Find Out) model represents 
                unstructured, emotion-driven trading decisions made without proper analysis or adherence to systematic methodology. 
                This model captures impulsive entries based on price movement momentum, social media sentiment, or perceived "hot tips" 
                without consideration of Random's Four Steps framework or risk management protocols.""",

                'primary_chart_tf': 'Variable',
                'execution_chart_tf': 'Any available',
                'context_chart_tf': 'None - decision made without context',

                'technical_indicators_used': """- Price movement (basic observation)
                - Social media sentiment indicators
                - "Hot tip" information from unverified sources
                - Recent news headlines (surface level)
                - Fear/greed emotional indicators
                - Market "buzz" and momentum""",

                'instrument_applicability': 'Any available instrument, often unfamiliar ones',
                'session_applicability': 'Any time, often at market extremes or during high volatility',
                'optimal_market_conditions': 'High volatility environments with significant price movement and market excitement',
                'sub_optimal_market_conditions': 'All conditions - this model lacks systematic approach to market assessment',

                'entry_trigger_description': """Impulsive entry based on:
                - Sudden large price movements in either direction
                - Social media posts suggesting "guaranteed" profits
                - News headlines creating urgency
                - Feeling of missing out on profitable opportunities
                - Emotional reaction to recent wins/losses""",

                'stop_loss_strategy': 'Often absent or moved impulsively. When present, typically too tight or too wide without logical basis',
                'take_profit_strategy': """Highly variable and emotional:
                - Premature exits on small gains due to fear
                - Holding losing positions hoping for recovery
                - Moving targets based on greed rather than analysis
                - Exit driven by external noise rather than plan""",
                'min_risk_reward_ratio': 0.1,

                'position_sizing_rules': 'Inconsistent sizing based on emotions - often too large on "sure things" or revenge trades',
                'trade_management_breakeven_rules': 'No systematic breakeven rules - management driven by fear and greed cycles',
                'trade_management_partial_profit_rules': 'All-or-nothing approach - rarely scales positions systematically',

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
            model_data['created_by_admin_user_id'] = None  # Not created by admin
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

            # Generate trade details
            days_back = random.randint(0, 730)
            trade_date = start_date + timedelta(days=days_back)

            # Skip weekends
            while trade_date.weekday() >= 5:
                trade_date += timedelta(days=1)

            # Random instrument and model
            instrument = random.choice(list(self.instruments.values()))
            model = random.choice(self.trading_models) if self.trading_models else None

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
                trade_notes=self._get_trade_note(model.name if model else 'Manual', outcome),
                trading_model_id=model.id if model else None,
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
            if hasattr(trade, 'calculate_and_store_pnl'):
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

                # Use only fields that exist in the File model
                file_record = File(
                    user_id=user.id,
                    filename=f'{purpose}_{user.username}_{i + 1}.{file_ext}',  # This is the field name
                    filepath=f'uploads/user_{user.id}/{purpose}_{i + 1}.{file_ext}',  # This is the field name
                    filesize=random.randint(1024, 5242880),  # 1KB - 5MB (this is the field name)
                    file_type=file_ext,  # This field exists
                    mime_type=f'application/{file_ext}' if file_ext in ['csv', 'xlsx', 'pdf'] else f'image/{file_ext}',
                    upload_date=datetime.now() - timedelta(
                        days=random.randint(1, 180),
                        hours=random.randint(0, 23)
                    ),
                    description=f'{purpose} file for {user.username}',
                    is_public=random.choice([True, False]),
                    download_count=random.randint(0, 10)
                    # Remove: original_filename - this field doesn't exist
                    # Remove: file_path - use filepath instead
                    # Remove: file_size - use filesize instead
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
            did_well_today='Followed trading plan and risk management rules.' if performance['total_pnl'] >= 0 else 'Maintained discipline despite challenging conditions.',
            did_not_go_well_today='Minor timing issues on some entries.' if performance['win_rate'] < 60 else 'No major issues identified.',
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
        total_pnl = sum(trade.pnl for trade in trades_for_day if hasattr(trade, 'pnl') and trade.pnl) or 0
        winning_trades = sum(1 for trade in trades_for_day if hasattr(trade, 'pnl') and trade.pnl and trade.pnl > 0)

        return {
            'total_pnl': total_pnl,
            'winning_trades': winning_trades,
            'total_trades': len(trades_for_day),
            'win_rate': (winning_trades / len(trades_for_day)) * 100 if trades_for_day else 0
        }

    def _generate_four_steps_analysis(self, trades_for_day):
        """Generate Four Steps analysis."""
        models_used = list(set([trade.trading_model.name for trade in trades_for_day if hasattr(trade, 'trading_model') and trade.trading_model]))
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

    def create_backtesting_data(self):
        """Create comprehensive backtesting data for all trading models."""
        print("\n🧪 Creating backtesting data for all trading models...")
        
        if not self.trading_models:
            print("❌ No trading models found. Skipping backtesting data creation.")
            return
        
        from app.models import Backtest, BacktestTrade, BacktestStatus, BacktestExitReason
        
        created_backtests = []
        created_trades = []
        
        # Get a consistent instrument for all backtests (ES)
        es_instrument = None
        for instrument in self.instruments.values():
            if instrument.symbol == 'ES':
                es_instrument = instrument
                break
        
        if not es_instrument:
            print("❌ ES instrument not found. Cannot create backtesting data.")
            return
        
        # Generate 500+ days of backtesting data 
        end_date = date.today() - timedelta(days=30)  # End 30 days ago
        start_date = end_date - timedelta(days=500)   # 500 days of data
        
        # Create one backtest per trading model
        for model in self.trading_models:
            # Only create backtests for default models
            if not model.is_default:
                continue
                
            print(f"  📊 Creating backtest for {model.name}...")
            
            # Create the backtest
            backtest = Backtest(
                name=f"{model.name} - Historical Performance Analysis",
                description=f"Comprehensive 500-day backtest of the {model.name} trading model using ES futures. "
                           f"Testing period: {start_date.strftime('%m/%d/%Y')} to {end_date.strftime('%m/%d/%Y')}. "
                           f"This backtest validates the model's performance across various market conditions including trending, "
                           f"ranging, and volatile periods.",
                trading_model_id=model.id,
                user_id=self.admin_user.id,
                start_date=start_date,
                end_date=end_date,
                status=BacktestStatus.COMPLETED,
                created_at=datetime.utcnow() - timedelta(days=random.randint(60, 120)),
                completed_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                
                # Trading rules specific to each model
                specific_rules_used=f"Standard {model.name} rules with enhanced risk management for backtesting",
                entry_rules=f"Entry signals based on {model.name} methodology with statistical validation",
                exit_rules="Systematic exits using profit targets, stop losses, and time-based exits",
                trade_management_applied="Breakeven stops after 1R profit, partial profit taking at key levels",
                risk_settings="Maximum 2% risk per trade, maximum 5% daily drawdown limit",
                
                # Market context
                market_conditions="Mixed market conditions including trending, ranging, and volatile periods",
                session_context="Primary focus on NY1 session (9:30-12:00 EST)",
                
                # Will be calculated after adding trades
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                total_pnl=0.0,
                total_pnl_ticks=0.0
            )
            
            db.session.add(backtest)
            db.session.flush()  # Get the ID
            created_backtests.append(backtest)
            
            # Generate 1000 trades for this backtest
            print(f"    🔄 Generating 1000 trades...")
            
            # Trade generation parameters based on model characteristics
            model_params = self._get_model_backtest_params(model.name)
            
            model_trades = []
            current_date = start_date
            
            trades_generated = 0
            while trades_generated < 1000 and current_date <= end_date:
                # Skip weekends
                if current_date.weekday() >= 5:
                    current_date += timedelta(days=1)
                    continue
                
                # Generate 1-3 trades per day (randomly)
                trades_per_day = random.choices([0, 1, 2, 3], weights=[0.3, 0.4, 0.2, 0.1])[0]
                
                for _ in range(min(trades_per_day, 1000 - trades_generated)):
                    if trades_generated >= 1000:
                        break
                        
                    trade = self._generate_backtest_trade(
                        backtest=backtest,
                        trade_date=current_date,
                        instrument=es_instrument,
                        model_params=model_params
                    )
                    
                    model_trades.append(trade)
                    trades_generated += 1
                
                current_date += timedelta(days=1)
            
            # Add all trades to session
            for trade in model_trades:
                db.session.add(trade)
                created_trades.append(trade)
            
            # Calculate backtest performance metrics
            self._calculate_backtest_metrics(backtest, model_trades)
            
            print(f"    ✅ Created backtest with {len(model_trades)} trades")
        
        # Commit all backtesting data
        try:
            db.session.commit()
            print(f"\n✅ Successfully created {len(created_backtests)} backtests with {len(created_trades)} total trades")
            
            # Print summary statistics
            for backtest in created_backtests:
                print(f"   📊 {backtest.name[:50]}...")
                print(f"      Trades: {backtest.total_trades} | Win Rate: {backtest.win_percentage:.1f}% | "
                      f"P&L: ${backtest.total_pnl:,.2f} | PF: {backtest.profit_factor:.2f}")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating backtesting data: {e}")
            raise

    def _get_model_backtest_params(self, model_name):
        """Get backtest parameters specific to each trading model."""
        params = {
            '0930 Opening Range': {
                'win_rate': 0.68,
                'avg_winner': 1.8,
                'avg_loser': -0.9,
                'session_times': [(9, 30), (9, 45)],  # 9:30-9:45 AM
                'typical_duration': (5, 15),  # 5-15 minutes
                'primary_sessions': ['NY1'],
                'market_conditions': ['trending', 'breakout', 'high_volume']
            },
            'HOD/LOD Reversal': {
                'win_rate': 0.62,
                'avg_winner': 2.2,
                'avg_loser': -1.0,
                'session_times': [(10, 0), (15, 30)],  # Throughout the day
                'typical_duration': (10, 45),  # 10-45 minutes
                'primary_sessions': ['NY1', 'NY2'],
                'market_conditions': ['ranging', 'reversal', 'overextended']
            },
            'Captain Backtest': {
                'win_rate': 0.55,
                'avg_winner': 3.2,
                'avg_loser': -1.1,
                'session_times': [(9, 30), (16, 0)],  # Full day
                'typical_duration': (20, 120),  # 20-120 minutes
                'primary_sessions': ['NY1', 'NY2'],
                'market_conditions': ['trending', 'momentum', 'breakout']
            },
            'P12 Scenario-Based': {
                'win_rate': 0.70,
                'avg_winner': 1.5,
                'avg_loser': -0.8,
                'session_times': [(9, 30), (12, 0)],  # NY1 session
                'typical_duration': (8, 25),  # 8-25 minutes
                'primary_sessions': ['NY1'],
                'market_conditions': ['p12_setup', 'statistical', 'high_probability']
            },
            'Quarterly Theory & 05 Boxes': {
                'win_rate': 0.64,
                'avg_winner': 2.0,
                'avg_loser': -0.9,
                'session_times': [(9, 0), (16, 0)],  # Extended hours
                'typical_duration': (15, 60),  # 15-60 minutes
                'primary_sessions': ['NY1', 'NY2'],
                'market_conditions': ['quarterly_levels', 'precision', 'institutional']
            },
            'Midnight Open Retracement': {
                'win_rate': 0.66,
                'avg_winner': 1.7,
                'avg_loser': -0.85,
                'session_times': [(0, 0), (2, 0), (9, 30), (11, 0)],  # Midnight and morning
                'typical_duration': (10, 30),  # 10-30 minutes
                'primary_sessions': ['Asia', 'NY1'],
                'market_conditions': ['retracement', 'overnight', 'statistical']
            }
        }
        
        # Default parameters for unknown models
        default_params = {
            'win_rate': 0.60,
            'avg_winner': 2.0,
            'avg_loser': -1.0,
            'session_times': [(9, 30), (16, 0)],
            'typical_duration': (10, 45),
            'primary_sessions': ['NY1', 'NY2'],
            'market_conditions': ['mixed', 'general']
        }
        
        return params.get(model_name, default_params)

    def _generate_backtest_trade(self, backtest, trade_date, instrument, model_params):
        """Generate a single realistic backtest trade."""
        from app.models import BacktestTrade, BacktestExitReason
        
        # Determine trade outcome based on model win rate
        outcome_rand = random.random()
        if outcome_rand < model_params['win_rate']:
            outcome = 'win'
            r_multiple = random.uniform(0.5, model_params['avg_winner'])
        else:
            outcome = 'loss'
            r_multiple = random.uniform(model_params['avg_loser'], -0.2)
        
        # Generate realistic trade timing
        session_times = model_params['session_times']
        if len(session_times) >= 2:
            start_hour, start_min = session_times[0]
            end_hour, end_min = session_times[1]
        else:
            start_hour, start_min = 9, 30
            end_hour, end_min = 16, 0
            
        # Random entry time within session
        entry_hour = random.randint(start_hour, min(end_hour, 15))
        entry_minute = random.randint(0 if entry_hour > start_hour else start_min, 
                                     59 if entry_hour < end_hour else end_min)
        entry_time = time(entry_hour, entry_minute)
        
        # Trade duration
        min_duration, max_duration = model_params['typical_duration']
        duration = random.randint(min_duration, max_duration)
        
        # Calculate exit time
        entry_dt = datetime.combine(trade_date, entry_time)
        exit_dt = entry_dt + timedelta(minutes=duration)
        exit_time = exit_dt.time()
        
        # Generate realistic ES prices (around 4400-4600 range)
        base_price = random.uniform(4400, 4600)
        entry_price = round(base_price + random.uniform(-20, 20), 2)
        
        # Direction
        direction = random.choice(['LONG', 'SHORT'])
        
        # Calculate stop loss and take profit
        tick_value = 0.25  # ES tick size
        stop_distance_ticks = random.randint(8, 20)  # 8-20 ticks stop
        target_distance_ticks = random.randint(12, 40)  # 12-40 ticks target
        
        if direction == 'LONG':
            stop_loss = entry_price - (stop_distance_ticks * tick_value)
            take_profit = entry_price + (target_distance_ticks * tick_value)
            if outcome == 'win':
                exit_price = entry_price + (abs(r_multiple) * stop_distance_ticks * tick_value)
            else:
                exit_price = entry_price + (r_multiple * stop_distance_ticks * tick_value)
        else:
            stop_loss = entry_price + (stop_distance_ticks * tick_value)
            take_profit = entry_price - (target_distance_ticks * tick_value)
            if outcome == 'win':
                exit_price = entry_price - (abs(r_multiple) * stop_distance_ticks * tick_value)
            else:
                exit_price = entry_price - (r_multiple * stop_distance_ticks * tick_value)
        
        exit_price = round(exit_price, 2)
        
        # Calculate P&L
        if direction == 'LONG':
            pnl_ticks = (exit_price - entry_price) / tick_value
        else:
            pnl_ticks = (entry_price - exit_price) / tick_value
            
        pnl_dollars = pnl_ticks * 12.50  # ES point value
        
        # Generate MAE/MFE
        mae_ticks = random.uniform(1, stop_distance_ticks * 0.8)
        if outcome == 'win':
            mfe_ticks = abs(pnl_ticks) + random.uniform(0, 5)
        else:
            mfe_ticks = random.uniform(0, stop_distance_ticks * 0.3)
        
        # Exit reason
        if outcome == 'win':
            exit_reason = random.choice([
                BacktestExitReason.TAKE_PROFIT,
                BacktestExitReason.PARTIAL_PROFIT,
                BacktestExitReason.TRAILING_STOP
            ])
        else:
            exit_reason = random.choice([
                BacktestExitReason.STOP_LOSS,
                BacktestExitReason.TIME_EXIT,
                BacktestExitReason.MANUAL_EXIT
            ])
        
        # Session context and market conditions
        session_context = random.choice(model_params['primary_sessions'])
        market_condition = random.choice(model_params['market_conditions'])
        
        # Create the trade
        trade = BacktestTrade(
            backtest_id=backtest.id,
            trade_date=trade_date,
            trade_time=entry_time,
            instrument=instrument.symbol,
            direction=direction.lower(),
            quantity=1,
            entry_price=entry_price,
            exit_price=exit_price,
            stop_loss_price=round(stop_loss, 2),
            take_profit_price=round(take_profit, 2),
            profit_loss=round(pnl_dollars, 2),
            profit_loss_ticks=round(pnl_ticks, 1),
            mae_ticks=round(-abs(mae_ticks), 1),  # MAE is negative
            mfe_ticks=round(mfe_ticks, 1),
            duration_minutes=duration,
            actual_exit_reason=exit_reason,
            exit_time=exit_time,
            market_conditions=f"{market_condition.replace('_', ' ').title()}, Normal Volume",
            session_context=session_context,
            notes=f"Systematic {backtest.trading_model.name} trade. Setup quality: {random.choice(['A+', 'A', 'B+', 'B'])}. "
                  f"Execution: {random.choice(['Perfect', 'Good', 'Fair'])}.",
            tags=f"[\"{backtest.trading_model.name.lower().replace(' ', '-')}\", \"{outcome}\", \"{market_condition}\"]",
            created_at=datetime.combine(trade_date, entry_time) + timedelta(minutes=duration + 5)
        )
        
        return trade

    def _calculate_backtest_metrics(self, backtest, trades):
        """Calculate and update backtest performance metrics."""
        if not trades:
            return
            
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.profit_loss > 0)
        losing_trades = sum(1 for t in trades if t.profit_loss < 0)
        breakeven_trades = total_trades - winning_trades - losing_trades
        
        total_pnl = sum(t.profit_loss for t in trades)
        total_pnl_ticks = sum(t.profit_loss_ticks for t in trades)
        
        win_percentage = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate profit factor
        gross_profit = sum(t.profit_loss for t in trades if t.profit_loss > 0)
        gross_loss = abs(sum(t.profit_loss for t in trades if t.profit_loss < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
        
        # Calculate averages
        winners = [t.profit_loss for t in trades if t.profit_loss > 0]
        losers = [t.profit_loss for t in trades if t.profit_loss < 0]
        
        avg_win = sum(winners) / len(winners) if winners else 0
        avg_loss = sum(losers) / len(losers) if losers else 0
        avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        # Calculate max drawdown (simplified)
        running_pnl = 0
        peak_pnl = 0
        max_drawdown = 0
        
        for trade in sorted(trades, key=lambda t: (t.trade_date, t.trade_time or time(9, 30))):
            running_pnl += trade.profit_loss
            if running_pnl > peak_pnl:
                peak_pnl = running_pnl
            drawdown = peak_pnl - running_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Calculate additional metrics
        largest_win = max(winners) if winners else 0
        largest_loss = min(losers) if losers else 0
        
        # Update backtest object
        backtest.total_trades = total_trades
        backtest.winning_trades = winning_trades
        backtest.losing_trades = losing_trades
        backtest.win_percentage = round(win_percentage, 2)
        backtest.total_pnl = round(total_pnl, 2)
        backtest.total_pnl_ticks = round(total_pnl_ticks, 1)
        backtest.average_win = round(avg_win, 2)
        backtest.average_loss = round(avg_loss, 2)
        backtest.profit_factor = round(profit_factor, 2)
        backtest.avg_trade_pnl = round(avg_trade_pnl, 2)
        backtest.max_drawdown = round(-max_drawdown, 2)  # Store as negative
        backtest.largest_win = round(largest_win, 2)
        backtest.largest_loss = round(largest_loss, 2)
        backtest.avg_mae = round(sum(t.mae_ticks for t in trades if t.mae_ticks) / total_trades, 2)
        backtest.avg_mfe = round(sum(t.mfe_ticks for t in trades if t.mfe_ticks) / total_trades, 2)

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


def run_complete_bootstrap():
    """Complete bootstrap process with all data generation."""
    manager = EnhancedBootstrapManager()

    try:
        print("🚀 Starting Enhanced Database Bootstrap...")

        # Initialize application and database
        manager.initialize_app()

        with manager.app.app_context():
            print("\n🔧 Phase 1: Core System Setup")
            manager.create_admin_user()
            manager.create_test_users()
            manager.create_user_groups()
            manager.create_sample_password_resets()

            print("\n🔧 Phase 2: Trading Framework")
            manager.create_default_tags()
            manager.create_instruments()
            manager.create_p12_scenarios()
            manager.create_trading_models()
            manager.create_news_events()
            manager.create_account_settings()

            print("\n🔧 Phase 3: Trading Data Generation")
            manager.generate_realistic_trades(10000)
            manager.create_trade_images()
            manager.create_daily_journals()
            manager.create_weekly_journals()
            manager.create_backtesting_data()

            print("\n🔧 Phase 4: System Activity & Files")
            manager.create_activity_logs()
            manager.create_sample_files()

            print("\n🔧 Phase 5: Final Statistics")
            manager.print_comprehensive_statistics()

            print("\n🎉 BOOTSTRAP COMPLETE!")
            print("=" * 60)
            print("Ready to run: python run.py")
            print("Admin login: admin / admin123")
            print("Test user login: testuser1 / testuser1")

    except Exception as e:
        print(f"❌ Bootstrap failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True


def create_backtesting_data_only():
    """Create only backtesting data - useful for adding backtests to existing database."""
    print("🧪 Creating Backtesting Data Only...")
    manager = EnhancedBootstrapManager()
    
    try:
        manager.initialize_app()
        
        with manager.app.app_context():
            manager.create_backtesting_data()
            print("\n✅ Backtesting data creation completed successfully!")
            return True
            
    except Exception as e:
        print(f"\n❌ Backtesting data creation failed: {e}")
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import sys
    
    # Check if user wants to create only backtesting data
    if len(sys.argv) > 1 and sys.argv[1] == '--backtesting-only':
        success = create_backtesting_data_only()
    else:
        success = run_complete_bootstrap()
    
    if not success:
        print("\n❌ Operation failed. Check the errors above.")
        sys.exit(1)
    else:
        print("\n✅ Operation completed successfully!")