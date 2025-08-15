# CLAUDE.md

This file provides essential guidance to Claude Code (claude.ai/code) when working with this Flask trading journal application.

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
```

### Database Management
```bash
# Database migrations
flask db migrate -m "Description of changes"
flask db upgrade
flask db downgrade
```

## High-Level Architecture

### Flask Application Structure
This is a **Flask-based trading journal application** using Random's Four Steps methodology. The application follows a modular blueprint architecture with comprehensive user management and trading analytics.

### Core Framework Components
- **Flask** with SQLAlchemy ORM and Flask-Migrate for database management
- **Flask-Login** for authentication and session management
- **Flask-WTF** for form handling and CSRF protection
- **Enterprise CSS Framework** for consistent UI styling

### Blueprint Architecture
The application is organized into functional blueprints:
- `main_bp` - Dashboard and primary user interface
- `auth_bp` - User authentication (login/register/profile)
- `admin_bp` - Administrative functions and user management
- `trades_bp` - Trade entry, editing, and management
- `journal_bp` - Daily journal entries and P12 analysis
- `analytics_bp` - Performance analytics and reporting
- `files_bp` - File upload/download management
- `settings_bp` - User preferences and configuration

## CRITICAL: ENTERPRISE TEMPLATE STANDARDS

**MANDATORY:** The `app/templates/trades/add_trade.html` page is the **GOLD STANDARD** template for all future form-based pages. ALL form modifications MUST follow this exact pattern.

### **Reference Template: `add_trade.html`**
This template is the perfect implementation of:

#### **1. Image Management System (MANDATORY)**
```html
<!-- User Instructions for Multiple Images -->
<div class="alert alert-info py-2 px-3 mb-2" style="border-left: 4px solid #0066cc;">
    <div class="d-flex align-items-center">
        <i class="fas fa-info-circle text-primary me-2"></i>
        <small class="mb-0">
            <strong>Multiple Images:</strong> Hold <kbd>Ctrl</kbd> (Windows) or <kbd>Cmd</kbd> (Mac) while clicking to select multiple images.
        </small>
    </div>
</div>

<!-- Image Preview with Perfect Layout -->
<div class="col-md-3 col-sm-4 col-6" id="existing-image-{{ image.id }}">
    <div class="card h-100">
        <img src="{{ url_for('images.serve_trade_image', image_id=image.id) }}"
             class="card-img-top mt-3"
             style="height: 200px; object-fit: contain; cursor: pointer;">
        <div class="card-body p-2">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <small class="text-muted">{{ image.filename }}</small>
                    <br>
                    <small class="text-muted">{{ filesize }} KB</small>
                </div>
                <button type="button" class="btn btn-outline-danger btn-sm" 
                        onclick="deleteExistingImage({{ image.id }})" title="Delete Image">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>
        </div>
    </div>
</div>
```

**Key Requirements:**
- `mt-3` spacing above images
- `object-fit: contain` for full image visibility
- Delete button inline with filename using flexbox
- `MultipleFileField` for multiple image uploads
- User instruction alerts with keyboard shortcuts

#### **2. Sticky Submit Buttons (MANDATORY)**
```html
<!-- Sticky Submit Section -->
<div class="sticky-submit-section">
    <div class="enterprise-container-fluid">
        <div class="d-flex justify-content-between align-items-center">
            <div class="d-flex align-items-center">
                <div class="me-3">
                    <span class="text-muted small">All changes are automatically validated</span>
                </div>
            </div>
            <div class="btn-group">
                <a href="{{ url_for('trades.view_trades_list') }}" 
                   class="btn btn-outline-secondary" id="cancel-btn">
                    <i class="fas fa-times me-1"></i>Cancel
                </a>
                <button type="submit" class="btn btn-primary" id="save-btn">
                    <i class="fas fa-save me-1"></i>
                    {% if trade %}Update Trade{% else %}Create Trade{% endif %}
                </button>
            </div>
        </div>
    </div>
</div>
```

#### **3. Unsaved Changes Detection (MANDATORY)**
**CRITICAL:** Use the exact pattern from `add_trade.html` for unsaved changes detection:

```html
{% block head_extra %}
<meta name="csrf-token" content="{{ csrf_token() }}">
<input type="hidden" id="js-csrf-token" value="{{ csrf_token() }}">
<script src="{{ url_for('static', filename='js/notifications.js') }}"></script>
<script src="{{ url_for('static', filename='js/custom-modals.js') }}"></script>
<script>
// MANDATORY: Proper CSRF token retrieval
function getCSRFToken() {
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfInput = document.querySelector('#js-csrf-token');
    return csrfMeta?.getAttribute('content') || csrfInput?.value || '';
}

// MANDATORY: Enterprise unsaved changes integration
document.addEventListener('DOMContentLoaded', function() {
    // Register dynamic inputs with enterprise system
    function registerNewInputsWithEnterprise() {
        if (window.enterpriseUnsavedChanges) {
            window.enterpriseUnsavedChanges.reinitialize();
        }
    }
    
    // Call after adding dynamic form elements
    registerNewInputsWithEnterprise();
});
</script>
{% endblock %}
```

#### **4. Form Layout Standards (MANDATORY)**
- Use `enterprise-module` for all form sections
- Grid layout: `grid grid-cols-X gap-4`
- Module headers with icons: `<i class="fas fa-icon module-icon"></i>`
- Consistent button styling: `btn-outline-secondary btn-sm`

### **CSS Framework Standards**

#### **Enterprise CSS Loading (MANDATORY)**
```html
<link rel="stylesheet" href="/static/css/enterprise-all.css">
```

#### **Textarea Height Utilities (MANDATORY)**
```html
<!-- Use enterprise textarea classes for consistent sizing -->
{{ form.field_name(class="form-control textarea-7" + (" is-invalid" if form.field_name.errors else "")) }}
```

Available classes: `textarea-1`, `textarea-3`, `textarea-4`, `textarea-7`, `textarea-15`

### **JavaScript Patterns (MANDATORY)**

#### **Image Deletion API Calls**
```javascript
function deleteExistingImage(imageId) {
    showCustomConfirmation({
        title: 'Delete Image',
        message: 'Are you sure you want to delete this image?',
        confirmText: 'Delete Image',
        confirmClass: 'btn-danger',
        icon: 'trash',
        onConfirm: function() {
            const csrfToken = getCSRFToken();
            const deleteUrl = `/trades/image/${imageId}/delete`;
            
            fetch(deleteUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        throw new Error(`HTTP ${response.status}: ${text}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Remove with animation
                    imageContainer.style.transition = 'all 0.3s ease';
                    imageContainer.style.transform = 'scale(0)';
                    setTimeout(() => imageContainer.remove(), 300);
                    
                    if (window.showNotification) {
                        showNotification('success', 'Image deleted successfully');
                    }
                }
            })
            .catch(error => {
                if (window.showNotification) {
                    showNotification('error', 'Failed to delete image');
                }
            });
        }
    });
}
```

## Default Credentials

- **Admin User:** `admin` / `admin123`
- **Test Users:** `testuser1` / `testuser1` through `testuser100` / `testuser100`

## Important Implementation Notes

### **For ALL Form Pages:**
1. **ALWAYS** reference `add_trade.html` as the template standard
2. **NEVER** create competing unsaved changes systems
3. **ALWAYS** use enterprise CSS framework classes
4. **ALWAYS** implement proper CSRF token handling
5. **ALWAYS** use sticky submit buttons for forms
6. **ALWAYS** include user guidance for complex interactions

### **Image Management:**
- Use `MultipleFileField` for file uploads
- Implement inline delete buttons with flexbox layout
- Add `mt-3` spacing above images
- Use `object-fit: contain` for proper image display
- Include user instruction alerts

### **Enterprise Standards:**
- Follow Fortune 500 terminology throughout interface
- Use professional confirmation dialogs (no browser alerts)
- Implement comprehensive form validation
- Maintain consistent spacing and layout patterns

The `add_trade.html` template represents the PERFECT implementation of enterprise-grade form interfaces with comprehensive user experience features, proper error handling, and professional appearance.