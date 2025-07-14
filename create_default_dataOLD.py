#!/usr/bin/env python3
"""
Complete Database Bootstrap Script - FIXED VERSION
==================================================
Creates a fresh trading journal database with everything needed to start trading
according to Random's (Matt Mickey) methodology.

This script sets up:
- Admin user account
- Default system tags based on Random's teachings
- Core instruments (ES, NQ, YM, RTY) with proper field mapping
- Random's 6 trading models (0930, HOD/LOD, Captain Backtest, P12, Quarterly, Midnight Open)
- Sample realistic trades (~250) with proper P&L calculations
- Daily journal entries using Four Steps methodology
- News events and account settings
- All necessary relationships and data integrity

FIXED ISSUES:
- User model field mapping (name instead of first_name/last_name)
- Instrument model with all required fields (exchange, asset_class, etc.)
- Proper P&L calculation calls

Usage: python bootstrap_database.py
"""

import os
import sys
import random
from datetime import datetime, date, time, timedelta
from collections import defaultdict
from decimal import Decimal

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import (
    User, UserRole, TradingModel, Trade, EntryPoint, ExitPoint,
    Instrument, Tag, TagCategory, NewsEventItem, AccountSetting,
    DailyJournal, Settings, Activity, P12Scenario
)


class BootstrapManager:
    """Manages the complete database bootstrap process."""

    def __init__(self):
        self.app = None
        self.admin_user = None
        self.instruments = {}
        self.trading_models = []
        self.tags = []
        self.trades = []

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
        """Create the admin user account."""
        print("\n👤 Creating admin user...")

        admin_data = {
            'username': 'admin',
            'email': 'admin@tradingjournal.local',
            'name': 'System Administrator',  # Use single 'name' field instead of first_name/last_name
            'role': UserRole.ADMIN,
            'is_active': True,
            'is_email_verified': True,
            'bio': 'System administrator for the trading journal application.'
        }

        admin = User(**admin_data)
        admin.set_password('admin123')  # Change this in production!

        db.session.add(admin)
        db.session.commit()

        # Create default settings for admin
        settings = Settings(user_id=admin.id)
        db.session.add(settings)
        db.session.commit()

        self.admin_user = admin
        print(f"✅ Admin user created: {admin.username} (ID: {admin.id})")
        print(f"🔑 Default password: admin123 (CHANGE THIS!)")

    def create_test_user(self):
        """Create the test user account."""
        print("\n👤 Creating test user...")

        test_user_data = {
            'username': 'testuser',
            'email': 'smitty1021@gmail.com',
            'name': 'Test User',
            'role': UserRole.USER,
            'is_active': True,
            'is_email_verified': True,
            'bio': 'Test user account for trading journal application.'
        }

        test_user = User(**test_user_data)
        test_user.set_password('testuser1')

        db.session.add(test_user)
        db.session.commit()

        # Create default settings for test user
        settings = Settings(user_id=test_user.id)
        db.session.add(settings)
        db.session.commit()

        self.test_user = test_user
        print(f"✅ Test user created: {test_user.username} (ID: {test_user.id})")
        print(f"🔑 Password: testuser1")

    def create_default_tags(self):
        """Create default tags based on Random's methodology."""
        print("\n🏷️  Creating default tags...")

        # Tags based on Random's Four Steps and trading methodology
        tags_data = [
            # Setup & Strategy tags
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


            # Market Conditions based on Random's classification
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

            # Execution & Management
            ("Front Run", TagCategory.EXECUTION_MANAGEMENT, "good"),  # Good execution
            ("Confirmation", TagCategory.EXECUTION_MANAGEMENT, "good"),  # Good execution
            ("Retest", TagCategory.EXECUTION_MANAGEMENT, "good"),  # Good execution
            ("Chased Entry", TagCategory.EXECUTION_MANAGEMENT, "bad"),  # Poor execution
            ("Late Entry", TagCategory.EXECUTION_MANAGEMENT, "bad"),  # Poor execution
            ("Proper Stop", TagCategory.EXECUTION_MANAGEMENT, "good"),  # Good risk management
            ("Moved Stop", TagCategory.EXECUTION_MANAGEMENT, "bad"),  # Poor risk management
            ("Cut Short", TagCategory.EXECUTION_MANAGEMENT, "bad"),  # Poor management
            ("Let Run", TagCategory.EXECUTION_MANAGEMENT, "good"),  # Good management
            ("Partial Profit", TagCategory.EXECUTION_MANAGEMENT, "good"),  # Good management
            ("Limit Order", TagCategory.EXECUTION_MANAGEMENT, "neutral"),  # Order type (neutral)
            ("Market Order", TagCategory.EXECUTION_MANAGEMENT, "neutral"),  # Order type (neutral)

            # Psychological & Emotional
            ("Disciplined", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "good"),  # Positive psychology
            ("Patient", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "good"),  # Positive psychology
            ("Calm", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "good"),  # Positive psychology
            ("Confident", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "good"),  # Positive psychology
            ("Followed Plan", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "good"),  # Positive psychology
            ("FOMO", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),  # Negative psychology
            ("Revenge Trading", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),  # Negative psychology
            ("Impulsive", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),  # Negative psychology
            ("Anxious", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),  # Negative psychology
            ("Broke Rules", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),  # Negative psychology
            ("Overconfident", TagCategory.PSYCHOLOGICAL_EMOTIONAL, "bad"),  # Negative psychology
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
        """Create core trading instruments."""
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

    def _get_random_p12_scenario(self):
        """Get a random P12 scenario for the daily journal."""
        # Get all P12 scenarios from database
        scenarios = P12Scenario.query.filter_by(is_active=True).all()
        if scenarios:
            return random.choice(scenarios)
        return None

    def _generate_random_p12_levels(self, instrument_symbol='ES'):
        """Generate realistic P12 High/Mid/Low levels based on instrument."""
        if instrument_symbol == 'ES':
            base_price = random.uniform(4200, 4700)
            range_size = random.uniform(15, 45)  # 15-45 point range
        elif instrument_symbol == 'NQ':
            base_price = random.uniform(13000, 15500)
            range_size = random.uniform(50, 150)  # 50-150 point range
        else:
            base_price = random.uniform(4200, 4700)  # Default to ES-like
            range_size = random.uniform(15, 45)

        # P12 Mid is the base, High and Low are above/below
        p12_mid = round(base_price, 2)
        p12_high = round(p12_mid + (range_size / 2), 2)
        p12_low = round(p12_mid - (range_size / 2), 2)

        return p12_high, p12_mid, p12_low

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
        """Create default news events."""
        print("\n📰 Creating news events...")

        events_data = [
            ('FOMC Meeting', time(14, 0)),
            ('FOMC Statement', time(14, 0)),
            ('CPI Release', time(8, 30)),
            ('NFP Release', time(8, 30)),
            ('JOLTS Report', time(10, 0)),
            ('GDP Data', time(8, 30)),
            ('Retail Sales', time(8, 30)),
            ('PPI Data', time(8, 30)),
            ('Powell Speech', None),
            ('OPEC Meeting', None),
            ('Earnings Season', None),
            ('Geopolitical Event', None),
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
        print(f"✅ Created {len(created_events)} news events")

    def create_account_settings(self):
        """Create default account settings."""
        print("\n⚙️  Creating account settings...")

        settings_data = [
            ('current_account_size', '100000'),
            ('default_risk_per_trade', '2.5'),
            ('max_daily_loss', '5'),
            ('max_weekly_loss', '10'),
            ('preferred_instrument', 'NQ'),
            ('timezone', 'EST'),
            ('currency', 'USD')
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
        print(f"✅ Created {len(created_settings)} account settings")

    def generate_realistic_trades(self, num_trades=10000):
        """Generate realistic trades with proper P&L calculations."""
        print(f"\n📊 Generating {num_trades} realistic trades...")

        # Trade outcome distributions (based on typical prop trading stats)
        win_rate = 0.65  # 65% win rate
        breakeven_rate = 0.05  # 5% breakeven

        # R-multiple distributions for winners and losers
        winner_r_multiples = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
        winner_weights = [0.15, 0.20, 0.25, 0.15, 0.10, 0.08, 0.04, 0.02, 0.008, 0.002]

        loser_r_multiples = [-1.0, -0.8, -0.6, -0.4, -0.3, -0.15]
        loser_weights = [0.40, 0.25, 0.15, 0.10, 0.07, 0.03]

        # Time ranges for different models
        model_time_ranges = {
            '0930 Opening Range': [(9, 30), (9, 44)],
            'HOD/LOD Reversal': [(10, 0), (15, 30)],
            'Captain Backtest': [(10, 0), (15, 0)],
            'P12 Scenario-Based': [(9, 30), (16, 0)],
            'Quarterly Theory & 05 Boxes': [(9, 30), (16, 0)],
            'Midnight Open Retracement': [(8, 0), (11, 15)]
        }

        # Realistic price ranges
        price_ranges = {
            'ES': (4000, 4800),
            'NQ': (12000, 16000),
            'YM': (33000, 38000),
            'RTY': (1800, 2200)
        }

        # Contract size distributions
        contract_sizes = {
            'ES': [1, 2, 3, 4, 5],
            'NQ': [1, 2, 3, 4, 5, 6, 8, 10],
            'YM': [1, 2, 3, 4, 5],
            'RTY': [1, 2, 3]
        }

        created_trades = []
        start_date = date.today() - timedelta(days=3650)

        for i in range(num_trades):
            # Random date within the last 6 months, weekdays only
            days_back = random.randint(0, 3650)
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

            # Generate direction
            direction = random.choice(['Long', 'Short'])

            # Generate entry time based on model
            time_range = model_time_ranges.get(model.name, [(9, 30), (16, 0)])
            start_hour, start_min = time_range[0]
            end_hour, end_min = time_range[1] if len(time_range) > 1 else (16, 0)

            entry_hour = random.randint(start_hour, end_hour)
            entry_minute = random.randint(0 if entry_hour > start_hour else start_min,
                                          59 if entry_hour < end_hour else end_min)

            # Generate realistic prices
            price_range = price_ranges[instrument.symbol]
            base_price = random.uniform(price_range[0], price_range[1])
            tick_size = instrument.tick_size

            # Entry price (rounded to tick size)
            entry_price = round(base_price + random.uniform(-5, 5), 2)
            entry_price = round(entry_price / tick_size) * tick_size

            # Stop loss distance (realistic for each instrument)
            if instrument.symbol == 'ES':
                stop_distance_ticks = random.randint(10, 40)
            elif instrument.symbol == 'NQ':
                stop_distance_ticks = random.randint(20, 80)
            elif instrument.symbol == 'YM':
                stop_distance_ticks = random.randint(50, 200)
            else:  # RTY
                stop_distance_ticks = random.randint(8, 30)

            stop_distance = stop_distance_ticks * tick_size

            # Calculate stop loss
            if direction == 'Long':
                stop_loss = entry_price - stop_distance
            else:
                stop_loss = entry_price + stop_distance

            # Calculate target based on R-multiple
            risk_per_share = abs(entry_price - stop_loss)
            target_distance = abs(r_multiple) * risk_per_share

            if outcome == 'win':
                if direction == 'Long':
                    exit_price = entry_price + target_distance
                else:
                    exit_price = entry_price - target_distance
            elif outcome == 'breakeven':
                exit_price = entry_price
            else:  # loss
                exit_price = stop_loss + random.uniform(-0.5, 0.5) * tick_size

            # Contract size
            contracts = random.choice(contract_sizes[instrument.symbol])

            # Exit time (some time after entry)
            exit_minutes_later = random.randint(5, 180)  # 5 minutes to 3 hours
            exit_time = datetime.combine(trade_date, time(entry_hour, entry_minute)) + timedelta(
                minutes=exit_minutes_later)

            # Ensure exit time is within market hours
            if exit_time.hour >= 16:
                exit_time = exit_time.replace(hour=15, minute=random.randint(45, 59))

            # Generate ratings (1-5 scale)
            base_rating = 4 if outcome == 'win' else random.choice([2, 3, 3, 4])
            ratings_variance = 1

            # Assign trades: 100 to admin, rest to test user
            if i < 100:
                assigned_user_id = self.admin_user.id
            else:
                assigned_user_id = self.test_user.id

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
                rules_rating=max(1, min(5, base_rating + random.randint(-ratings_variance, ratings_variance))),
                management_rating=max(1, min(5, base_rating + random.randint(-ratings_variance, ratings_variance))),
                target_rating=max(1, min(5, base_rating + random.randint(-ratings_variance, ratings_variance))),
                entry_rating=max(1, min(5, base_rating + random.randint(-ratings_variance, ratings_variance))),
                preparation_rating=max(1, min(5, base_rating + random.randint(-ratings_variance, ratings_variance))),
                trade_notes=self._get_trade_note(model.name, outcome),
                trading_model_id=model.id,
                user_id=assigned_user_id  # Use the assigned user ID
            )

            db.session.add(trade)
            db.session.flush()  # Get trade ID

            # Create entry point
            entry = EntryPoint(
                trade_id=trade.id,
                entry_time=time(entry_hour, entry_minute),
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

            # Calculate and store P&L
            trade.calculate_and_store_pnl()

            # Assign random tags
            self._assign_tags_to_trade(trade, outcome)

            created_trades.append(trade)

            if (i + 1) % 50 == 0:
                print(f"  📝 Generated {i + 1}/{num_trades} trades...")

        db.session.commit()
        self.trades = created_trades
        print(f"✅ Created {len(created_trades)} realistic trades with P&L calculations")

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
        events = [
            'FOMC Meeting', 'NFP Release', 'CPI Data', 'JOLTS Report',
            'GDP Data', 'Retail Sales', 'PPI Data', 'Powell Speech',
            'OPEC Meeting', 'Earnings Season', 'Geopolitical Event'
        ]
        return random.choice(events)

    def _get_trade_note(self, model_name, outcome):
        """Generate realistic trade notes based on Random's methodology."""
        notes_by_model = {
            '0930 Opening Range': [
                "Clean snap pattern identified at open. {}",
                "VWAP rejection provided good RTV entry. {}",
                "Strong volume confirmation at break. {}",
                "Daily classification supported directional bias. {}",
                "Time stop at 09:44 as planned. {}"
            ],
            'HOD/LOD Reversal': [
                "Perfect HOD rejection with 059 box confirmation. {}",
                "Hourly momentum change signaled reversal. {}",
                "Dashboard logic correctly identified zone. {}",
                "Patient wait for confirmation paid off. {}",
                "Mean reversion to P12 mid as expected. {}"
            ],
            'Captain Backtest': [
                "H4 range break with clean pullback setup. {}",
                "Front-ran NY2 session successfully. {}",
                "Daily profile supported trending move. {}",
                "Extended target to HOD as planned. {}",
                "Momentum carried through to 15:00. {}"
            ],
            'P12 Scenario-Based': [
                "Scenario 5B played out perfectly. {}",
                "Price above mid, targeted high breakout. {}",
                "Quarter level entry provided precision. {}",
                "P12 structure held as expected. {}",
                "Scenario analysis gave clear bias. {}"
            ],
            'Quarterly Theory & 05 Boxes': [
                "059 box provided perfect entry signal. {}",
                "Quarter level reaction as expected. {}",
                "Volume spike confirmed direction. {}",
                "Scaled out at statistical targets. {}",
                "Hourly structure respected. {}"
            ],
            'Midnight Open Retracement': [
                "Clean retracement to midnight open. {}",
                "Hourly footprint provided entry. {}",
                "Distribution extreme reached. {}",
                "Asia range context supported trade. {}",
                "Statistical target achieved. {}"
            ]
        }

        outcome_modifiers = {
            'win': "Executed according to plan.",
            'loss': "Stop loss hit, followed rules.",
            'breakeven': "Scratched for small gain/loss."
        }

        base_notes = notes_by_model.get(model_name, ["Standard setup executed. {}"])
        note_template = random.choice(base_notes)
        modifier = outcome_modifiers.get(outcome, "Trade completed.")

        return note_template.format(modifier)

    def _assign_tags_to_trade(self, trade, outcome):
        """Assign random tags to trades based on outcome."""
        # Categorize tags for easier selection
        good_tags = [tag for tag in self.tags if tag.color_category == 'good']
        bad_tags = [tag for tag in self.tags if tag.color_category == 'bad']
        neutral_tags = [tag for tag in self.tags if tag.color_category == 'neutral']

        selected_tags = []

        # Always add 1-2 neutral tags (market conditions, setup type)
        neutral_count = random.randint(1, 2)
        selected_tags.extend(random.sample(neutral_tags, min(neutral_count, len(neutral_tags))))

        if outcome == 'win':
            # Add 2-4 good tags
            good_count = random.randint(2, 4)
            selected_tags.extend(random.sample(good_tags, min(good_count, len(good_tags))))

            # Maybe add 1 bad tag (even good trades can have issues)
            if random.random() < 0.2:
                selected_tags.append(random.choice(bad_tags))

        elif outcome == 'loss':
            # Add 1-3 bad tags
            bad_count = random.randint(1, 3)
            selected_tags.extend(random.sample(bad_tags, min(bad_count, len(bad_tags))))

            # Maybe add 1 good tag (even bad trades can have good elements)
            if random.random() < 0.3:
                selected_tags.append(random.choice(good_tags))

        else:  # breakeven
            # Add mix of good and bad
            if random.random() < 0.5:
                selected_tags.append(random.choice(good_tags))
            if random.random() < 0.5:
                selected_tags.append(random.choice(bad_tags))

        # Remove duplicates and assign
        unique_tags = list(set(selected_tags))
        trade.tags = unique_tags

    def create_daily_journals(self):
        """Create daily journal entries for trade days using Random's Four Steps."""
        print("\n📖 Creating daily journal entries...")

        # Group trades by date
        trade_days = defaultdict(list)
        for trade in self.trades:
            trade_days[trade.trade_date].append(trade)

        created_journals = []
        for trade_date, trades_for_day in trade_days.items():
            journal = self._create_daily_journal_entry(trade_date, trades_for_day)
            created_journals.append(journal)

        db.session.commit()
        print(f"✅ Created {len(created_journals)} daily journal entries")

    def _create_daily_journal_entry(self, trade_date, trades_for_day):
        """Create a comprehensive daily journal entry."""

        # Calculate performance metrics
        performance = self._calculate_daily_performance(trades_for_day)

        # Generate daily classification and session behavior
        daily_classification = self._get_daily_classification()
        session_behavior = self._get_session_behavior()

        p12_scenario = self._get_random_p12_scenario()

        # Get primary instrument for the day (from trades)
        primary_instrument = 'ES'  # Default
        if trades_for_day:
            primary_instrument = trades_for_day[0].instrument  # Remove .symbol here

        # Generate P12 levels
        p12_high, p12_mid, p12_low = self._generate_random_p12_levels(primary_instrument)

        # Store P12 scenario for reference in analysis
        self._current_p12_scenario = p12_scenario

        # Generate psychology ratings
        psych_ratings = self._generate_psych_ratings(performance)

        # Count unique models used
        unique_models = len(set([t.trading_model.name for t in trades_for_day if t.trading_model]))

        # Determine which user the journal belongs to based on trades
        journal_user_id = trades_for_day[0].user_id if trades_for_day else self.admin_user.id

        journal = DailyJournal(
            user_id=journal_user_id,
            journal_date=trade_date,

            # ADD P12 scenario data
            p12_scenario_id=p12_scenario.id if p12_scenario else None,
            p12_high=p12_high,
            p12_mid=p12_mid,
            p12_low=p12_low,
            p12_notes=f"P12 Analysis: {p12_scenario.scenario_name if p12_scenario else 'No scenario selected'}. Range: {p12_high - p12_low:.1f} points.",

            # Pre-market section using Random's Four Steps
            p12_expected_outcomes=self._generate_four_steps_analysis(daily_classification, session_behavior,
                                                                     trades_for_day),
            realistic_expectance_notes=self._generate_premarket_analysis(daily_classification, session_behavior),
            engagement_structure_notes=self._generate_trade_plan(daily_classification, trades_for_day),
            key_levels_notes=self._generate_execution_notes(trades_for_day, performance),

            # Mental state ratings
            mental_feeling_rating=psych_ratings.get('energy', 3),
            mental_mind_rating=psych_ratings.get('mind', 3),
            mental_energy_rating=psych_ratings.get('energy', 3),
            mental_motivation_rating=psych_ratings.get('motivation', 3),

            # Post-market analysis
            market_observations=self._generate_eod_review(performance, daily_classification),
            self_observations="Executed trades according to plan. " + (
                "Performance exceeded expectations." if performance[
                                                            'total_pnl'] > 0 else "Room for improvement in execution."),

            # Daily reflection
            did_well_today="Applied Four Steps methodology consistently. " + (
                "Good risk management and trade execution." if performance[
                                                                   'win_rate'] >= 60 else "Maintained discipline despite challenging conditions."),
            did_not_go_well_today="Minor timing issues on entries." if performance[
                                                                           'win_rate'] < 60 else "No major execution issues identified.",
            learned_today=random.choice([
                "Patience at key levels continues to pay off.",
                "Model selection alignment with daily bias is crucial.",
                "Risk management discipline prevents larger losses.",
                "P12 analysis provides excellent structural guidance."
            ]),
            improve_action_next_day=random.choice([
                "Focus on tighter entry timing using quarter levels.",
                "Review daily classification criteria for better accuracy.",
                "Implement stricter model activation requirements.",
                "Enhance position sizing based on setup quality."
            ]),

            # Psychology ratings (1-5 scale)
            review_psych_discipline_rating=psych_ratings['discipline'],
            review_psych_motivation_rating=psych_ratings['motivation'],
            review_psych_focus_rating=psych_ratings['focus'],
            review_psych_mastery_rating=psych_ratings['mastery'],
            review_psych_composure_rating=psych_ratings['composure'],
            review_psych_resilience_rating=psych_ratings['resilience'],
            review_psych_mind_rating=psych_ratings['mind'],
            review_psych_energy_rating=psych_ratings['energy'],

            # Key events
            key_events_today="Traded {0} times using {1} models. Daily classification: {2}. Session behavior: {3}.".format(
                performance['total_trades'], unique_models, daily_classification[0], session_behavior[0])
        )

        db.session.add(journal)
        return journal

    def _calculate_daily_performance(self, trades_for_day):
        """Calculate performance metrics for a specific day."""
        total_pnl = 0
        winning_trades = 0
        losing_trades = 0
        total_volume = 0

        for trade in trades_for_day:
            if trade.pnl:
                total_pnl += trade.pnl
                if trade.pnl > 0:
                    winning_trades += 1
                elif trade.pnl < 0:
                    losing_trades += 1

            entries = list(trade.entries)
            if entries:
                total_volume += entries[0].contracts

        return {
            'total_pnl': total_pnl,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'total_trades': len(trades_for_day),
            'total_volume': total_volume,
            'win_rate': (winning_trades / len(trades_for_day)) * 100 if trades_for_day else 0
        }

    def _get_daily_classification(self):
        """Get a random daily classification based on Random's methodology."""
        classifications = [
            ('DWP', 'Down With Purpose - Trending down day'),
            ('DNP', 'Down With No Purpose - Trending up day'),  # Note: DNP actually means up in Random's system
            ('Range 1', 'Range day - price returns to 9:30 mean'),
            ('Range 2', 'Range day - extended range but contained')
        ]
        return random.choice(classifications)

    def _get_session_behavior(self):
        """Get random session behavior based on Random's analysis."""
        behaviors = [
            ('Asia True', 'Asia session respected structure'),
            ('Asia False', 'Asia session broke structure'),
            ('London True', 'London session respected structure'),
            ('London False', 'London session broke structure'),
            ('Asia/London Broken', 'Both sessions broke key levels')
        ]
        return random.choice(behaviors)

    def _generate_four_steps_analysis(self, daily_classification, session_behavior, trades_for_day):
        """Generate Four Steps analysis based on Random's methodology."""
        classification, class_desc = daily_classification
        session, session_desc = session_behavior

        # Get the P12 scenario if available
        p12_scenario_text = ""
        if hasattr(self, '_current_p12_scenario') and self._current_p12_scenario:
            p12_scenario_text = f" P12 Scenario {self._current_p12_scenario.scenario_number} identified: {self._current_p12_scenario.short_description}."

        # Step 1: Define HOD/LOD
        step1_templates = [
            "Dashboard analysis shows {0} bias. {1} - expecting HOD around 15:00, LOD likely already in from overnight session.",
            "% move from 18:00 open suggests {0} structure. {1} Daily range potential assessed at 1.2-1.8% based on ADR10.",
            "P12 analysis indicates {0} formation. {1} Time zone analysis shows clear directional bias for RTH session.",
            "Globex range and overnight action point to {0} day. {1} HOD/LOD zones identified using dashboard logic."
        ]
        step1 = random.choice(step1_templates).format(classification, session_desc, p12_scenario_text)

        # Step 2: Incorporate Variables
        rvol = random.randint(80, 180)
        adr_remaining = random.randint(60, 120)
        step2_templates = [
            "Session behavior: {0}. RVOL running {1}% of normal. ADR suggests {2}% available range remaining for RTH.",
            "Variables aligned: {0} with {1}% RVOL confirmation. Model activation criteria met for trending setups.",
            "{0} session behavior supports bias. Volatility and volume parameters within normal ranges for execution.",
            "Key variables: {0} and elevated RVOL at {1}%. Market structure supportive of chosen trading models."
        ]
        step2 = random.choice(step2_templates).format(session_desc, rvol, adr_remaining)

        # Step 3: Set Realistic Expectance
        range_target = random.uniform(0.8, 2.2)
        completion = random.randint(40, 85)
        extension_phase = random.choice(['early extension phase', 'mid-day consolidation', 'late extension potential'])
        step3_templates = [
            "Expectance set for {0} day with {1:.1f}% range target. Early/late extension assessment: {2}.",
            "Daily range median comparison shows {1}% completion. Adjusting position sizes and targets accordingly.",
            "Historical {0} days show {1}% median performance. Setting conservative targets given current range utilization.",
            "Range analysis: {1:.1f}% of ADR10 used. Expectance calibrated for {0} day structure."
        ]
        step3 = random.choice(step3_templates).format(classification, range_target, extension_phase)

        # Step 4: Engage at Highest Statistical Structure
        models_used = list(set([trade.trading_model.name for trade in trades_for_day if trade.trading_model]))
        models_str = ', '.join(models_used) if models_used else 'Standard setups'
        step4_templates = [
            "Engaged using {0} model(s). Price clouds and statistical levels provided optimal entry structure.",
            "Highest probability setups identified: {0}. Front-run and confirmation entries executed per plan.",
            "Statistical structure engagement: {0} models activated. Entry quality rated high based on confluence.",
            "Execution at key levels using {0}. Risk/reward alignment with daily bias maintained throughout."
        ]
        step4 = random.choice(step4_templates).format(models_str)

        return "Step 1 - Define HOD/LOD: {0}\n\nStep 2 - Incorporate Variables: {1}\n\nStep 3 - Set Realistic Expectance: {2}\n\nStep 4 - Engage at Highest Statistical Structure: {3}".format(
            step1, step2, step3, step4)

    def _generate_premarket_analysis(self, daily_classification, session_behavior):
        """Generate pre-market analysis following Random's methodology."""
        classification, _ = daily_classification
        session, _ = session_behavior

        templates = [
            "Globex review: {0} session behavior with clear {1} bias developing. P12 levels defined: High {2}, Mid {3}, Low {4}. Key reaction levels identified for RTH session.",
            "Overnight structure analysis shows {0} formation. {1} Range: {2:.1f}% from 18:00 open. Dashboard logic suggests {3} bias for NY session with HOD/LOD timing estimates.",
            "Pre-market assessment: {0} day classification based on session behavior and P12 analysis. Key levels: Previous day high/low, settlement, and overnight range boundaries. Expect {1} behavior.",
            "European session showed {0} characteristics. Asia range: {1} handles. P12 scenario analysis points to {2} setup with statistical edge for RTH execution.",
            "Overnight range analysis: {0:.1f}% move from midnight open. {1} session confirms daily bias. Risk assessment: normal to elevated based on upcoming economic data."
        ]

        p12_high = random.randint(4200, 4600) if classification in ['DNP', 'Range 2'] else random.randint(4150, 4400)
        p12_mid = p12_high - random.randint(15, 35)
        p12_low = p12_mid - random.randint(15, 35)
        overnight_move = random.uniform(0.3, 1.8)
        asia_range = random.randint(25, 85)

        template = random.choice(templates)

        # Handle different template formats
        if 'P12 levels defined' in template:
            return template.format(session, classification, p12_high, p12_mid, p12_low)
        elif 'Range:' in template and 'Dashboard logic' in template:
            return template.format(classification, session, overnight_move, classification)
        elif 'Asia range:' in template:
            return template.format(session, asia_range, classification)
        elif 'move from midnight' in template:
            return template.format(overnight_move, session)
        else:
            return template.format(classification, session, classification)

    def _generate_trade_plan(self, daily_classification, trades_for_day):
        """Generate trade plan based on daily classification and actual trades."""
        classification, _ = daily_classification
        models_used = list(set([trade.trading_model.name for trade in trades_for_day if trade.trading_model]))

        plan_templates = {
            'DWP': [
                "Plan: Target short entries on {} models. Expecting breakdown and continuation lower. Risk management: tight stops above key levels, targets at daily lows.",
                "Strategy: Activate trend-following models ({}) for downside capture. Avoid counter-trend trades. Position sizing: moderate to aggressive on A+ setups.",
                "Execution plan: Wait for proper displacement lower, then front-run continuation. Models in play: {}. Target daily extremes with scaled exits."
            ],
            'DNP': [
                "Plan: Focus on long entries via {} models. Trending upside expected with momentum continuation. Risk: structured stops below key supports.",
                "Strategy: Deploy trend models ({}) for upside participation. Avoid fading strength. Sizing: standard to large on confirmed breakouts.",
                "Execution: Target breakout continuation using {}. Plan for extended targets if momentum sustains. Partial scaling at statistical levels."
            ],
            'Range 1': [
                "Plan: Scalping focused using {} models. Expect return to 9:30 mean. Quick in/out trades with tight risk management parameters.",
                "Strategy: Range-bound approach with {} setups. Target reversals at extremes, quick profit-taking. Conservative sizing due to chop risk.",
                "Execution: Deploy mean reversion models ({}). Fast exits priority over large targets. Risk management: smaller stops, frequent reassessment."
            ],
            'Range 2': [
                "Plan: Extended range day approach using {} models. Larger range than R1 but still contained. Target range extremes with patience.",
                "Strategy: Combination approach - trend models ({}) at breaks, reversal models at extremes. Medium-term holds acceptable.",
                "Execution: Flexible model deployment ({}). Adjust targets based on range development. Standard risk parameters with range-based adjustments."
            ]
        }

        templates = plan_templates.get(classification, plan_templates['Range 1'])
        models_str = ', '.join(models_used) if models_used else 'standard setups'

        return random.choice(templates).format(models_str)

    def _generate_execution_notes(self, trades_for_day, performance):
        """Generate execution notes based on actual trades and performance."""
        models_executed = [trade.trading_model.name for trade in trades_for_day if trade.trading_model]
        directions = [trade.direction for trade in trades_for_day]

        # Count longs vs shorts
        long_count = directions.count('Long')
        short_count = directions.count('Short')

        base_notes = []

        # Trade execution summary
        if performance['total_trades'] == 1:
            base_notes.append(
                "Single trade execution: {0}. ".format(models_executed[0] if models_executed else 'Standard setup'))
        else:
            base_notes.append(
                "Executed {0} trades: {1} longs, {2} shorts. ".format(performance['total_trades'], long_count,
                                                                      short_count))

        # Model usage
        if models_executed:
            unique_models = list(set(models_executed))
            if len(unique_models) == 1:
                base_notes.append("Focused on {0} model throughout session. ".format(unique_models[0]))
            else:
                base_notes.append("Multiple models deployed: {0}. ".format(', '.join(unique_models)))

        # Performance assessment
        if performance['win_rate'] >= 70:
            base_notes.append("Execution quality: excellent. Rules followed consistently. ")
        elif performance['win_rate'] >= 50:
            base_notes.append("Execution quality: good. Minor timing improvements identified. ")
        else:
            base_notes.append("Execution quality: needs improvement. Rule adherence review required. ")

        # P&L context
        if performance['total_pnl'] > 500:
            base_notes.append(
                "Strong P&L day: ${0:.0f}. Target achievement exceeded expectations. ".format(performance['total_pnl']))
        elif performance['total_pnl'] > 0:
            base_notes.append("Positive P&L: ${0:.0f}. Consistent with daily goals. ".format(performance['total_pnl']))
        elif performance['total_pnl'] > -200:
            base_notes.append(
                "Small loss: ${0:.0f}. Within acceptable daily risk parameters. ".format(performance['total_pnl']))
        else:
            base_notes.append(
                "Significant loss: ${0:.0f}. Risk management review required. ".format(performance['total_pnl']))

        # Add specific execution details
        execution_details = [
            "Entry timing aligned with planned levels. Stop placement followed model requirements.",
            "Risk management executed per plan. Position sizing appropriate for setup quality.",
            "Trade management smooth - moved stops to breakeven as planned.",
            "Scaling executed at statistical targets. Runner management according to model rules.",
            "Exit timing optimal given market conditions. No premature stops or late exits."
        ]

        base_notes.append(random.choice(execution_details))

        return ' '.join(base_notes)

    def _generate_eod_review(self, performance, daily_classification):
        """Generate end-of-day review following Random's framework."""
        classification, _ = daily_classification

        review_sections = []

        # Performance summary
        if performance['total_pnl'] > 0:
            review_sections.append(
                "Day result: +${0:.0f} ({1:.0f}% win rate). Daily classification ({2}) played out as expected.".format(
                    performance['total_pnl'], performance['win_rate'], classification))
        else:
            review_sections.append(
                "Day result: ${0:.0f} ({1:.0f}% win rate). Daily classification ({2}) assessment needs refinement.".format(
                    performance['total_pnl'], performance['win_rate'], classification))

        # What worked well
        worked_well = [
            "Four Steps analysis provided clear daily bias and execution framework.",
            "Model selection aligned perfectly with market conditions and daily classification.",
            "Risk management parameters kept losses controlled and let winners run appropriately.",
            "Entry timing and patience at statistical levels resulted in high-quality setups.",
            "P12 analysis and scenario mapping gave excellent structural guidance."
        ]

        if performance['win_rate'] >= 60:
            review_sections.append("What worked: " + random.choice(worked_well))

        # Areas for improvement
        improvements = [
            "Could improve entry precision using quarter level analysis for better risk/reward.",
            "Position sizing could be optimized - missed opportunity for larger size on A+ setups.",
            "Trade management could be enhanced - earlier breakeven moves on strong setups.",
            "Daily classification assessment needs refinement - mixed signals caused hesitation.",
            "Model activation criteria should be stricter - avoided some marginal setups."
        ]

        review_sections.append("Improvement areas: " + random.choice(improvements))

        # Lessons learned
        lessons = [
            "Patience at key levels continues to be rewarded with high-quality entries.",
            "Daily bias from Four Steps framework remains essential for trade direction confidence.",
            "Risk management discipline prevents small losses from becoming large ones.",
            "Model-specific execution rules provide consistency and remove emotional decisions.",
            "Market structure recognition improving - better at identifying trending vs ranging conditions."
        ]

        review_sections.append("Key lesson: " + random.choice(lessons))

        # Tomorrow's preparation
        tomorrow_prep = [
            "Review overnight action and update P12 levels for tomorrow's analysis.",
            "Check economic calendar for potential market-moving events during RTH.",
            "Assess daily range utilization and adjust position sizing parameters if needed.",
            "Review model performance and consider any activation criteria adjustments.",
            "Prepare dashboard analysis and update HOD/LOD probability assessments."
        ]

        review_sections.append("Tomorrow's prep: " + random.choice(tomorrow_prep))

        return ' '.join(review_sections)

    def _generate_psych_ratings(self, performance):
        """Generate psychology ratings based on performance."""
        # Base ratings influenced by performance
        base_rating = 4 if performance['total_pnl'] > 0 else 3
        if performance['win_rate'] >= 75:
            base_rating = 5
        elif performance['total_pnl'] < -300:
            base_rating = 2

        # Add some variance
        variance = 1

        ratings = {}
        psych_factors = [
            'discipline', 'motivation', 'focus', 'mastery',
            'composure', 'resilience', 'mind', 'energy'
        ]

        for factor in psych_factors:
            # Some factors might be different based on specific performance aspects
            if factor == 'discipline':
                # Higher discipline rating if followed rules (good win rate or small losses)
                rating = base_rating + (
                    1 if performance['win_rate'] >= 60 or abs(performance['total_pnl']) < 200 else -1)
            elif factor == 'composure':
                # Higher composure if managed losses well
                rating = base_rating + (1 if performance['total_pnl'] > -200 else -1)
            elif factor == 'energy':
                # Random variance for energy
                rating = base_rating + random.randint(-1, 1)
            else:
                rating = base_rating + random.randint(-variance, variance)

            # Ensure ratings stay within 1-5 range
            ratings[factor] = max(1, min(5, rating))

        return ratings

    def create_p12_scenarios(self):
        """Create Random's 5 P12 scenarios with model recommendations."""
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
                'scenario_number': '2A',
                'scenario_name': 'Scenario 2A: Look Above P12 High and Fail (Bullish Reversal)',
                'short_description': 'Price looks above P12 High then fails, expect low in and reversal up',
                'detailed_description': 'Price initially moves above P12 High but fails to hold and gets sucked back into the P12 range. Low of Day likely set by this false breakout, expect reversal to upside.',
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
                'scenario_number': '2B',
                'scenario_name': 'Scenario 2B: Look Below P12 Low and Fail (Bearish Reversal)',
                'short_description': 'Price looks below P12 Low then fails, expect high in and reversal down',
                'detailed_description': 'Price initially moves below P12 Low but fails to hold and gets sucked back into the P12 range. High of Day likely set by this false breakdown, expect reversal to downside.',
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
        print(f"✅ Created {len(created_scenarios)} P12 scenarios")

    def print_statistics(self):
        """Print comprehensive statistics about the generated data."""
        print("\n" + "=" * 80)
        print("📊 BOOTSTRAP COMPLETE - DATABASE STATISTICS")
        print("=" * 80)

        # User and basic setup
        print(f"\n👤 Users Created:")
        print(f"   • Admin: {self.admin_user.username} (ID: {self.admin_user.id})")
        print(f"   • Test User: {self.test_user.username} (ID: {self.test_user.id})")
        print(f"   • Email: {self.admin_user.email}")
        print(f"   • Role: {self.admin_user.role.value}")

        # Instruments
        print(f"\n📊 Instruments Created: {len(self.instruments)}")
        for symbol, instrument in self.instruments.items():
            print(f"   • {symbol}: {instrument.name} (${instrument.point_value}/point)")

        # Trading Models
        print(f"\n📋 Trading Models Created: {len(self.trading_models)}")
        for model in self.trading_models:
            print(f"   • {model.name} v{model.version}")

        # P12 Scenarios
        with self.app.app_context():
            p12_count = P12Scenario.query.count()
            print(f"\n📊 P12 Scenarios Created: {p12_count}")
            scenarios = P12Scenario.query.order_by(P12Scenario.scenario_number).all()
            for scenario in scenarios:
                scenario_display = f"Scenario {scenario.scenario_number}"
                if "1A" in scenario.scenario_name or "1B" in scenario.scenario_name:
                    scenario_display = "1A/1B"
                elif "2A" in scenario.scenario_name or "2B" in scenario.scenario_name:
                    scenario_display = "2A/2B"
                elif "3A" in scenario.scenario_name or "3B" in scenario.scenario_name:
                    scenario_display = "3A/3B"
                elif "4A" in scenario.scenario_name or "4B" in scenario.scenario_name:
                    scenario_display = "4A/4B"
                elif "Scenario 5" in scenario.scenario_name:
                    scenario_display = "5"
                print(f"   • {scenario_display}: {scenario.scenario_name}")

        # Tags
        print(f"\n🏷️  Tags Created: {len(self.tags)}")
        good_tags = len([t for t in self.tags if t.color_category == 'good'])
        bad_tags = len([t for t in self.tags if t.color_category == 'bad'])
        neutral_tags = len([t for t in self.tags if t.color_category == 'neutral'])
        print(f"   • Good tags: {good_tags}")
        print(f"   • Bad tags: {bad_tags}")
        print(f"   • Neutral tags: {neutral_tags}")

        # Trades statistics
        print(f"\n📈 Trades Generated: {len(self.trades)}")

        # Trade distribution by model
        model_counts = {}
        for trade in self.trades:
            model_name = trade.trading_model.name if trade.trading_model else 'Unknown'
            model_counts[model_name] = model_counts.get(model_name, 0) + 1

        print(f"\n📊 Trade Distribution by Model:")
        for model_name, count in model_counts.items():
            percentage = (count / len(self.trades)) * 100
            print(f"   • {model_name}: {count} trades ({percentage:.1f}%)")

        # Instrument distribution
        instrument_counts = {}
        for trade in self.trades:
            symbol = trade.instrument
            instrument_counts[symbol] = instrument_counts.get(symbol, 0) + 1

        print(f"\n🎯 Trade Distribution by Instrument:")
        for symbol, count in instrument_counts.items():
            percentage = (count / len(self.trades)) * 100
            print(f"   • {symbol}: {count} trades ({percentage:.1f}%)")

        # Direction distribution
        long_trades = sum(1 for trade in self.trades if trade.direction == 'Long')
        short_trades = len(self.trades) - long_trades

        print(f"\n📊 Direction Distribution:")
        print(f"   • Long: {long_trades} trades ({(long_trades / len(self.trades) * 100):.1f}%)")
        print(f"   • Short: {short_trades} trades ({(short_trades / len(self.trades) * 100):.1f}%)")

        # Performance statistics
        total_pnl = sum(trade.pnl for trade in self.trades if trade.pnl)
        winning_trades = sum(1 for trade in self.trades if trade.pnl and trade.pnl > 0)
        losing_trades = sum(1 for trade in self.trades if trade.pnl and trade.pnl < 0)
        breakeven_trades = sum(1 for trade in self.trades if trade.pnl and trade.pnl == 0)

        win_rate = (winning_trades / len(self.trades)) * 100 if self.trades else 0

        print(f"\n💰 Performance Statistics:")
        print(f"   • Total P&L: ${total_pnl:,.2f}")
        print(f"   • Win Rate: {win_rate:.1f}% ({winning_trades}/{len(self.trades)})")
        print(f"   • Losing Trades: {losing_trades}")
        print(f"   • Breakeven Trades: {breakeven_trades}")
        print(f"   • Average P&L per Trade: ${total_pnl / len(self.trades):,.2f}")

        # Date range
        if self.trades:
            min_date = min(trade.trade_date for trade in self.trades)
            max_date = max(trade.trade_date for trade in self.trades)
            print(f"\n📅 Trade Date Range:")
            print(f"   • From: {min_date.strftime('%Y-%m-%d')}")
            print(f"   • To: {max_date.strftime('%Y-%m-%d')}")

        # Database configuration
        print(f"\n🔧 Database Configuration:")
        print(f"   • Database: SQLite (app.db)")
        print(f"   • Location: instance/app.db")
        print(f"   • Tables: All models created successfully")

        print("\n" + "=" * 80)
        print("✅ BOOTSTRAP COMPLETE!")
        print("=" * 80)
        print("\nYour trading journal is now fully populated with:")
        print("• Complete admin user setup")
        print("• Random's 6 core trading models")
        print("• Comprehensive tag system")
        print("• Realistic trade data with P&L calculations")
        print("• Daily journal entries using Four Steps methodology")
        print("• News events and account settings")
        print("\nYou can now:")
        print("1. Login with admin/admin123")
        print("2. Test all trading journal features")
        print("3. View realistic performance analytics")
        print("4. Explore Random's methodology in action")
        print("\n🚨 SECURITY: Change the admin password immediately!")

    def run_bootstrap(self):
        """Execute the complete bootstrap process."""
        print("🚀 TRADING JOURNAL DATABASE BOOTSTRAP")
        print("=" * 60)
        print("Creating a complete trading journal database from scratch...")
        print("Based on Random's (Matt Mickey) trading methodology")
        print("=" * 60)

        try:
            self.initialize_app()

            with self.app.app_context():
                self.create_admin_user()
                self.create_test_user()
                self.create_default_tags()
                self.create_instruments()
                self.create_trading_models()
                self.create_p12_scenarios()
                self.create_news_events()
                self.create_account_settings()
                self.generate_realistic_trades()
                self.create_daily_journals()

                self.print_statistics()

        except Exception as e:
            print(f"\n❌ BOOTSTRAP FAILED: {e}")
            print("Rolling back all changes...")
            if self.app:
                with self.app.app_context():
                    db.session.rollback()
            raise


def main():
    """Main execution function."""
    print("🎯 COMPLETE TRADING JOURNAL BOOTSTRAP")
    print("=" * 50)
    print("This script will create a fresh database with:")
    print("• Admin user (admin/admin123)")
    print("• Random's 6 trading models")
    print("• Comprehensive tag system")
    print("• ~250 realistic trades")
    print("• Daily journal entries")
    print("• All supporting data")
    print("=" * 50)

    # Get user confirmation
    confirm = input("\nDo you want to proceed? This will DELETE existing data! (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Operation cancelled.")
        return

    try:
        bootstrap = BootstrapManager()
        bootstrap.run_bootstrap()

        print(f"\n🎉 SUCCESS! Trading journal database created successfully!")
        print(f"🔐 Login: admin / admin123")
        print(f"⚠️  CHANGE THE PASSWORD IMMEDIATELY!")

    except Exception as e:
        print(f"\n💥 BOOTSTRAP FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())