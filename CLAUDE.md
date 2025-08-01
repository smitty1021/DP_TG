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
- Standardized pagination controls with enterprise styling

**JavaScript Architecture:**
- `enterprise-base.js` - Core enterprise functionality
- `custom-modals.js` - Modal system for confirmations
- `notifications.js` - Toast notification system
- `unsaved-changes.js` - Form change detection
- `enterprise-search.js` - Search functionality

**CRITICAL: Enterprise Unsaved Changes System Guidelines:**
The application uses a centralized unsaved changes detection system. NEVER create duplicate or competing unsaved changes systems.

**✅ CORRECT Approach:**
- Rely on the global `unsaved-changes.js` system for ALL forms
- It automatically provides 3-button modal (Save Changes, Discard Changes, Cancel)
- No page-specific beforeunload handlers needed
- Only add `window.imageChanged = true` for image upload tracking if needed

**🚫 NEVER DO:**
- Add `window.addEventListener('beforeunload', ...)` in templates
- Create custom unsaved changes detection in individual pages
- Set `window.onbeforeunload = ...` anywhere
- Add duplicate form monitoring systems
- Create competing modal systems for unsaved changes

**Debug Mode (For Troubleshooting Only):**
```javascript
// Enable debug mode in browser console
window.__enableBeforeUnloadDebug = true
// Get comprehensive reports
__reportBeforeUnloadAttempts()
__debugBeforeUnload()
```

**CSS Framework:**
- `enterprise-all.css` - Consolidated CSS imports for optimal performance
- `enterprise-textarea-utilities.css` - Textarea height utilities with maximum specificity
- Uses consolidated CSS loading pattern for better performance

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

## ENTERPRISE TEMPLATE STANDARDS - USERS.HTML REFERENCE

**CRITICAL:** The `app/templates/admin/users.html` page is the GOLD STANDARD template. ALL future page modifications with similar components MUST follow this exact layout, styling, and functionality. Reference this page for:

### **Executive Header Pattern (MANDATORY)**
```html
<div class="executive-header">
    <div class="d-flex justify-content-between align-items-center">
        <div class="header-content">
            <h1 class="executive-title">
                <i class="fas fa-[icon] executive-icon"></i>
                {{ title }}
            </h1>
            <div class="executive-subtitle">
                [Descriptive subtitle using enterprise terminology]
            </div>
        </div>
        <div class="btn-group">
            <!-- Action buttons using btn-outline-secondary btn-sm -->
        </div>
    </div>
</div>
```

### **KPI Cards Section (MANDATORY)**
```html
<div class="kpi-section">
    <div class="grid grid-cols-6 gap-4">
        <div class="col-span-1">
            <div class="kpi-card">
                <div class="kpi-content">
                    <div class="kpi-header">
                        <span class="kpi-label">[Label]</span>
                        <i class="fas fa-[icon] kpi-icon"></i>
                    </div>
                    <div class="kpi-value">{{ value }}</div>
                    <div class="kpi-trend">
                        <span class="trend-indicator positive">[Description]</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
```

### **Module Header with Integrated Controls (NEW STANDARD)**
```html
<div class="module-header" style="position: relative; display: flex; align-items: center; padding: 1rem;">
    <!-- Left: Title with inline summary -->
    <div style="flex: 1;">
        <div class="module-title">
            <i class="fas fa-[icon] module-icon"></i>
            [Module Title]
            <span style="font-weight: 400; color: var(--enterprise-text-muted); margin-left: 1rem; font-size: 0.875rem;">
                {{ records_summary }}
            </span>
        </div>
    </div>
    
    <!-- Center: Pagination Controls (Absolutely Centered) -->
    <div class="btn-group" style="position: absolute; left: 50%; transform: translateX(-50%);">
        <!-- Pagination buttons using pagination-arrow-borderless class -->
    </div>
    
    <!-- Right: Records per Page + Action Buttons -->
    <div class="d-flex align-items-center gap-3" style="flex: 1; justify-content: flex-end;">
        <div class="d-flex align-items-center gap-2">
            <span style="font-size: 0.875rem;">Records per Page:</span>
            <select class="form-select form-select-sm" style="width: auto;">...</select>
        </div>
        <div class="btn-group">
            <!-- Action buttons (search, bulk ops, etc.) -->
        </div>
    </div>
</div>
```

### **Data Table with Sticky Headers (MANDATORY)**
```html
<div class="table-responsive" style="max-height: 600px; overflow-y: auto;">
    <table class="table table-striped table-hover table-sm mb-0">
        <thead class="table-dark sticky-top">
            <tr>
                <th class="sortable text-start" data-sort="[field]" role="columnheader" tabindex="0">
                    [Column Header]
                </th>
            </tr>
        </thead>
        <tbody>
            <!-- Table rows -->
        </tbody>
    </table>
</div>
```

### **Status Badge System (MANDATORY)**
```css
.status-badge {
    padding: 0.25rem 0.75rem;
    border-radius: var(--enterprise-radius);
    font-size: var(--enterprise-font-size-sm);
    font-weight: 600;
    text-align: center;
    display: inline-block;
    border: 1px solid transparent;
}

.status-badge.operational {
    background: rgba(0, 112, 192, 0.1);
    color: var(--enterprise-success);
    border: 1px solid rgba(0, 112, 192, 0.2);
}

.status-badge.suspended {
    background: rgba(209, 52, 56, 0.1);
    color: var(--enterprise-danger);
    border: 1px solid rgba(209, 52, 56, 0.2);
}
```

### **Search & Filter Modules (HIDDEN BY DEFAULT)**
```html
<div class="col-12 mt-3" id="search-filter-module" style="display: none;">
    <div class="enterprise-module">
        <div class="module-header">
            <div class="module-title">
                <i class="fas fa-filter module-icon"></i>
                Search & Filter Operations
            </div>
        </div>
        <div class="module-content">
            <!-- Search form with align-items-end for horizontal alignment -->
        </div>
    </div>
</div>
```

### **Active Filters Indicator**
```html
<div class="d-flex align-items-center justify-content-between py-2 px-3 mb-2" 
     style="background-color: rgba(13, 110, 253, 0.08); border: 1px solid rgba(13, 110, 253, 0.2); border-radius: 0.375rem;">
    <div class="d-flex align-items-center gap-2">
        <i class="fas fa-filter text-primary"></i>
        <span class="fw-semibold text-primary">Resource Database Filtered by:</span>
        <span class="badge bg-primary text-white">{{ filter }}</span>
    </div>
    <a href="[clear_url]" class="btn btn-outline-primary btn-sm">Clear Filters</a>
</div>
```

### **Spacing Standards (MANDATORY)**
- **Module spacing**: `mt-3` between all major sections
- **Card spacing**: `mb-3` on all cards and modules
- **Flex gaps**: `gap-3` (1rem) for consistent spacing
- **Form alignment**: `align-items-end` for horizontal form control alignment
- **Table container**: `max-height: 600px; overflow-y: auto` for scrollable tables

### **Textarea Height Utilities (MANDATORY)**
**CRITICAL:** Use the enterprise textarea height utility classes for consistent textarea sizing across all forms. These classes use maximum CSS specificity to override framework defaults.

#### **Available Textarea Height Classes:**
```html
<!-- Available textarea height classes (apply to textarea elements) -->
<textarea class="form-control textarea-1">...</textarea>  <!-- ~80px height -->
<textarea class="form-control textarea-3">...</textarea>  <!-- ~160px height -->
<textarea class="form-control textarea-4">...</textarea>  <!-- ~200px height -->
<textarea class="form-control textarea-7">...</textarea>  <!-- ~280px height -->
<textarea class="form-control textarea-15">...</textarea> <!-- ~320px height -->
```

#### **Implementation Pattern:**
```html
<!-- CORRECT: Use enterprise textarea utilities -->
{{ form.field_name(class="form-control textarea-7" + (" is-invalid" if form.field_name.errors else "")) }}

<!-- INCORRECT: Never use inline styles or rows attribute -->
<textarea style="height: 200px;">...</textarea>
<textarea rows="10">...</textarea>
```

#### **Technical Details:**
- Classes are defined in `enterprise-textarea-utilities.css`
- Uses maximum specificity selector: `html body .enterprise-container-fluid form .form-control.textarea-X`
- Includes `!important` declarations to override framework defaults
- All textareas have `resize: vertical` enabled for user flexibility
- Height utilities work across all enterprise form layouts

### **Color Consistency**
- **Primary Enterprise Blue**: `#0066cc` (buttons, links, highlights)
- **Success Green**: `#0070c0` (positive indicators)
- **Danger Red**: `#d13438` (warnings, errors, suspended status)
- **Muted Text**: `var(--enterprise-text-muted)` for secondary information
- **Background**: `var(--enterprise-gray-50)` for module headers

### **Interactive Elements**
- **Pagination**: `pagination-arrow-borderless` class for navigation buttons
- **Action Buttons**: `btn-outline-secondary btn-sm` for standard actions
- **Sortable Headers**: Include `sortable` class with ARIA labels
- **Selection**: Checkbox-based with master select functionality
- **Modals**: Use `custom-modals.js` instead of browser alerts

### **Unsaved Changes Notification System (MANDATORY)**
**CRITICAL:** ALL form-based pages MUST implement the unsaved changes detection and notification system as demonstrated in `edit_user.html` and `create_user.html`.

#### **Required Components:**
```html
<!-- Unsaved Changes Indicator (place after main content grid start) -->
<div id="unsaved-indicator" class="alert alert-warning alert-dismissible fade show mb-3" role="alert" style="display: none;">
    <i class="fas fa-exclamation-triangle me-2"></i>
    <strong>Unsaved Changes:</strong> You have [context-specific message] that have not been saved yet.
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
</div>
```

#### **Required JavaScript Implementation:**
**CRITICAL:** For proper custom modal functionality, unsaved changes detection MUST be implemented in the `head_extra` block as inline JavaScript, NOT in the document body. This ensures script loading order and function availability.

```html
{% block head_extra %}
<meta name="csrf-token" content="{{ csrf_token() }}">
<input type="hidden" id="js-csrf-token" value="{{ csrf_token() }}">
<script src="{{ url_for('static', filename='js/notifications.js') }}"></script>
<script src="{{ url_for('static', filename='js/custom-modals.js') }}"></script>
<script>
// Unsaved changes detection - MANDATORY for all forms
let hasUnsavedChanges = false;
let originalFormData = {};
let isSubmitting = false;

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('[form-id]'); // Use specific form ID
    const inputs = form.querySelectorAll('input, select, textarea');

    // Store original form data
    inputs.forEach(input => {
        if (input.type === 'checkbox') {
            originalFormData[input.name] = input.checked;
        } else {
            originalFormData[input.name] = input.value || '';
        }
    });

    // Monitor form changes and show/hide indicator
    inputs.forEach(input => {
        input.addEventListener('change', checkForChanges);
        input.addEventListener('input', checkForChanges);
    });

    // Check if form has changes
    function checkForChanges() {
        hasUnsavedChanges = false;
        inputs.forEach(input => {
            let currentValue = (input.type === 'checkbox') ? input.checked : input.value;
            let originalValue = (input.type === 'checkbox') ? originalFormData[input.name] : originalFormData[input.name] || '';
            if (currentValue !== originalValue) {
                hasUnsavedChanges = true;
            }
        });

        // Show/hide unsaved changes indicator
        const indicator = document.getElementById('unsaved-indicator');
        if (indicator) {
            indicator.style.display = hasUnsavedChanges ? 'block' : 'none';
        }
    }

    // Implementation continues with beforeUnloadHandler, navigation handler, etc.
});
</script>
{% endblock %}
```

#### **Required Scripts:**
```html
<script src="{{ url_for('static', filename='js/notifications.js') }}"></script>
<script src="{{ url_for('static', filename='js/custom-modals.js') }}"></script>
```

#### **Context-Specific Messages:**
- **Create Forms**: "You have entered [entity] data that has not been saved yet."
- **Edit Forms**: "You have made changes that have not been saved yet."
- **Navigation Warnings**: "[Entity] data will be lost if you navigate away."

#### **Field Mapping Requirements:**
Each form MUST define appropriate field mappings for user feedback:
```javascript
const fieldMappings = {
    'username': 'Username',
    'email': 'Email Address',
    'name': 'Full Name',
    // ... context-specific fields
};
```

#### **Double Popup Prevention (CRITICAL):**
To prevent both custom modal AND browser beforeunload from firing, implement this reset function:
```javascript
function resetFormToOriginalState() {
    console.log('🔄 Resetting form to original state...');
    
    // FIRST: Remove local beforeunload handler
    window.removeEventListener('beforeunload', beforeUnloadHandler);
    
    // SECOND: Disable the global enterprise unsaved changes handler
    if (window.enterpriseUnsavedChanges) {
        window.enterpriseUnsavedChanges.hasUnsavedChanges = false;
        window.enterpriseUnsavedChanges.isSubmitting = true;
        window.enterpriseUnsavedChanges.markAsSubmitting();
    }
    
    // THIRD: Nuclear option for any other handlers
    window.onbeforeunload = null;
    
    // Reset form inputs and state flags
    hasUnsavedChanges = false;
    isSubmitting = true;
    
    // Hide indicator and reset inputs to original values
}
```

#### **Navigation Handler Pattern (MANDATORY):**
```javascript
// Must use NAMED function (not anonymous) for beforeUnloadHandler
function beforeUnloadHandler(e) {
    if (hasUnsavedChanges && !isSubmitting) {
        const message = '[Context-specific warning message]';
        e.preventDefault();
        e.returnValue = message;
        return message;
    }
}
window.addEventListener('beforeunload', beforeUnloadHandler);
```

### **Side-by-Side Card Layout System**

#### **Enterprise Grid System for Card Layout:**
```html
<!-- Use enterprise grid system for side-by-side cards -->
<div class="grid grid-cols-2 gap-4 align-items-start">
    <!-- Left Card: Main functionality -->
    <div class="enterprise-module">
        <div class="module-header">
            <div class="module-title">
                <i class="fas fa-[icon] module-icon"></i>
                [Primary Module Title]
            </div>
            <div class="module-meta">
                [Primary Module Description]
            </div>
        </div>
        <div class="module-content mb-3">
            <!-- Main form or content -->
        </div>
    </div>

    <!-- Right Card: Guidelines/supplementary information -->
    <div class="enterprise-module">
        <div class="module-header">
            <div class="module-title">
                <i class="fas fa-info-circle module-icon"></i>
                [Guidelines/Info Title]
            </div>
            <div class="module-meta">
                Strategic Overview
            </div>
        </div>
        <div class="module-content mb-3">
            <!-- Guidelines content using row g-3 pattern -->
            <div class="row g-3">
                <div class="col-12">
                    <div class="d-flex align-items-start">
                        <div class="bg-primary-soft me-3 p-2 rounded">
                            <i class="fas fa-[icon]"></i>
                        </div>
                        <div>
                            <h6 class="mb-1">[Guideline Title]</h6>
                            <p class="text-muted small mb-0">[Guideline Description]</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
```

#### **Card Width Adjustments:**
For narrower side-by-side cards, use Bootstrap column classes within the grid:
```html
<div class="grid grid-cols-2 gap-4 align-items-start">
    <div class="col-lg-6 col-xl-5"> <!-- Slightly narrower left card -->
        <div class="enterprise-module">...</div>
    </div>
    <div class="col-lg-6 col-xl-7"> <!-- Slightly wider right card -->
        <div class="enterprise-module">...</div>
    </div>
</div>
```

### **Password Validation System (MANDATORY)**

#### **Password Strength Meter Implementation:**
Reference `create_user.html` and `edit_user.html` for complete implementation. Key components:
```html
<!-- Password Strength Indicator -->
<div id="password-strength-container" class="mt-2" style="display: none;">
    <div class="d-flex align-items-center mb-2">
        <small class="text-muted me-2">Strength:</small>
        <div class="progress flex-grow-1" style="height: 6px;">
            <div id="password-strength-bar" class="progress-bar" role="progressbar" style="width: 0%"></div>
        </div>
        <small id="password-strength-text" class="text-muted ms-2">Weak</small>
    </div>
    <div id="password-requirements" class="small text-muted">
        <div class="d-flex flex-wrap gap-2">
            <span id="req-length" class="badge bg-secondary">8+ chars</span>
            <span id="req-uppercase" class="badge bg-secondary">A-Z</span>
            <span id="req-lowercase" class="badge bg-secondary">a-z</span>
            <span id="req-number" class="badge bg-secondary">0-9</span>
            <span id="req-special" class="badge bg-secondary">Special</span>
        </div>
    </div>
</div>
```

#### **Password Match Validator:**
```html
<!-- Password Match Indicator -->
<div id="password-match-indicator" class="mt-2" style="display: none;">
    <small id="password-match-text" class="text-muted">
        <i id="password-match-icon" class="fas fa-times me-1"></i>
        Passwords do not match
    </small>
</div>
```

#### **JavaScript Functions (MANDATORY):**
```javascript
// Initialize both systems - MUST be called in DOMContentLoaded
initializePasswordStrengthMeter();
initializePasswordMatchValidator();
```

### **Success Message Flow Pattern**
- **Create pages**: Remove success notification from create page, let it display on destination page after redirect
- **Edit pages**: Success message appears after form submission and page reload
- **Flash message conversion**: Hide flash messages in create forms to prevent duplication

### **CRITICAL IMPLEMENTATION NOTES:**
1. **NEVER deviate** from this layout for pages with similar functionality
2. **Always use** the exact same CSS classes and styling patterns
3. **Always implement** the same JavaScript functionality for pagination, sorting, and selection
4. **Always implement** the unsaved changes notification system for ALL forms
5. **Always implement** proper double popup prevention using resetFormToOriginalState()
6. **Always use** NAMED functions for beforeUnloadHandler (never anonymous)
7. **Always implement** password strength and match validators for password fields
8. **Always use** enterprise grid system for side-by-side card layouts
9. **Always follow** the enterprise terminology and professional appearance
10. **Always test** sticky headers, pagination, responsive behavior, and unsaved changes detection
11. **Reference users.html, edit_user.html, and create_user.html** directly when implementing similar features

This template represents the PERFECT implementation of enterprise-grade administrative interfaces with comprehensive user experience features, proper form handling, and bulletproof popup management.

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