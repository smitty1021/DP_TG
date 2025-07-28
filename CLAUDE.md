# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Basic Application Startup
```bash
# Start the Flask application (development mode)
python run.py

# Initialize database (first time setup)
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Create default data and test users
python create_default_data.py

# Clean up test data (preserves admin user)
python cleanup_test_data.py

# Complete database wipe (nuclear option)
python cleanup_test_data.py --complete
```

### Flask CLI Commands
```bash
# Initialize database and drop existing data
flask init-db

# Seed default instruments if none exist  
flask seed-instruments

# Migrate P12 scenario images to global system
flask migrate-p12-images

# Access Flask shell with models preloaded
flask shell
```

### Database Management
```bash
# Database migrations
flask db migrate -m "Description of changes"
flask db upgrade
flask db downgrade

# Reset database (development)
flask db downgrade
flask db upgrade
```

## High-Level Architecture

### Flask Application Structure
This is a **Flask-based trading journal application** using Random's Four Steps methodology. The application follows a modular blueprint architecture with comprehensive user management and trading analytics.

### Core Framework Components
- **Flask** with SQLAlchemy ORM and Flask-Migrate for database management
- **Flask-Login** for authentication and session management
- **Flask-WTF** for form handling and CSRF protection
- **Flask-Mail** for email functionality
- **Discord integration** for user authentication and notifications
- **P12 scenario system** - central to the trading methodology

### Application Factory Pattern
- Main app created via `create_app()` in `app/__init__.py`
- Extensions initialized through `app/extensions.py`
- Configuration supports development/production environments via environment variables

### Blueprint Architecture
The application is organized into functional blueprints:

**Core Blueprints:**
- `main_bp` - Dashboard and primary user interface
- `auth_bp` - User authentication (login/register/profile)
- `admin_bp` - Administrative functions and user management
- `trades_bp` - Trade entry, editing, and management
- `journal_bp` - Daily journal entries and P12 analysis
- `analytics_bp` - Performance analytics and reporting
- `portfolio_bp` - Portfolio analytics and overview
- `files_bp` - File upload/download management
- `settings_bp` - User preferences and configuration

**Specialized Blueprints:**
- `trading_models_bp` - Trading model management (Random's 6 core models)
- `p12_scenarios_bp` - P12 scenario analysis and management
- `image_bp` - Image upload and management system
- `admin_access_control` - Advanced admin permission system

### Database Models and Relationships

**User Management:**
- `User` - Core user accounts with role-based access (USER/EDITOR/ADMIN)
- `UserRole` - Enum for user permission levels
- `Group` - User groups with many-to-many relationships
- `Settings` - Per-user preferences and configuration
- `ApiKey` - API access tokens for users

**Trading Core:**
- `Trade` - Central trading record with entry/exit points
- `EntryPoint`/`ExitPoint` - Detailed trade execution data
- `TradingModel` - Random's 6 default models + user-created models
- `Instrument` - Tradeable instruments (ES, NQ, YM, etc.)
- `Tag` - Trade categorization system with color coding

**P12 & Journal System:**
- `P12Scenario` - 5 core P12 scenarios with detailed trading logic
- `P12UsageStats` - Tracking P12 scenario usage and outcomes
- `DailyJournal` - Comprehensive daily trading journals with Four Steps analysis
- `WeeklyJournal`/`MonthlyJournal` - Periodic review structures

**Content Management:**
- `TradeImage`/`DailyJournalImage`/`GlobalImage` - Image management
- `File` - File upload system with user association
- `Activity` - System activity logging and audit trails

### Trading Methodology Integration

**Random's Four Steps Framework:**
1. **Define HOD/LOD** - Dashboard logic and timezone analysis
2. **Incorporate Session Variables** - Asia, London, NY1, NY2 session behavior
3. **Set Realistic Expectance** - ADR and session analysis
4. **Engage at Highest Statistical Structure** - Price cloud and level engagement

**Six Default Trading Models:**
- `0930 Opening Range` - Market open momentum capture
- `HOD/LOD Reversal` - Mean reversion at daily extremes
- `Captain Backtest` - Trend following for HOD/LOD capture
- `P12 Scenario-Based` - 12-hour Globex range analysis
- `Quarterly Theory & 05 Boxes` - Precision timing with hourly levels
- `Midnight Open Retracement` - Statistical reversion to midnight levels

### Frontend Architecture

**Enterprise CSS Framework:**
The application uses a custom enterprise-grade CSS framework with strict conventions:
- `enterprise-core.css` - Core styling foundation
- `enterprise-layout.css` - Layout and grid systems
- `enterprise-components.css` - UI component styles
- `enterprise-specialized.css` - Trading-specific components

**Corporate UI Standards:**
- Fortune 500 terminology throughout interface
- Custom modal system (no browser alerts)
- Comprehensive unsaved changes detection
- Professional button groups and navigation

**JavaScript Architecture:**
- `enterprise-base.js` - Core enterprise functionality
- `custom-modals.js` - Modal system for confirmations
- `notifications.js` - Toast notification system
- `unsaved-changes.js` - Form change detection
- `enterprise-search.js` - Search functionality

### Key Configuration Files

**Environment Configuration:**
- Uses `.env` file for secrets and configuration
- `SECRET_KEY`, `DATABASE_URL`, `FLASK_DEBUG` required
- Discord OAuth configuration for authentication
- Email server configuration for notifications

**Important Settings:**
- Default login: `admin` / `admin123`
- Database: SQLite in development (`instance/app.db`)
- File uploads: `instance/uploads/` directory structure
- Session storage: Filesystem sessions in `instance/flask_session/`

### Development Workflow

**Database Development:**
1. Modify models in `app/models.py`
2. Generate migration: `flask db migrate -m "Description"`
3. Apply migration: `flask db upgrade`
4. Use `create_default_data.py` to populate test data

**Testing Data:**
- Creates admin user + 100 test users (testuser1-100)
- Generates ~10,000 realistic trades with proper P&L
- Creates journal entries with Four Steps analysis
- Includes P12 scenario usage statistics

**File Structure Guidelines:**
- Templates follow enterprise HTML framework
- Static files organized by type (css/js/images)
- Upload folders auto-created for different content types
- Migration files track all database schema changes

## Default Credentials

- **Admin User:** `admin` / `admin123`
- **Test Users:** `testuser1` / `testuser1` through `testuser100` / `testuser100`

## Important Notes

- The application implements Random's trading methodology with P12 scenarios and Four Steps analysis
- Enterprise CSS framework must be followed for all frontend modifications  
- Discord integration provides OAuth authentication alongside standard login
- All trading models, P12 scenarios, and methodology are built into the core system
- Comprehensive audit logging tracks all user activities
- File upload system supports trading-related documents and chart images