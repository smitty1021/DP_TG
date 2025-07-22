/**
 * ===============================================================================
 * FORTUNE 500 ENTERPRISE UNSAVED CHANGES DETECTION SYSTEM
 * Global solution for consistent behavior across all pages
 * ===============================================================================
 */

class EnterpriseUnsavedChangesHandler {
    constructor(options = {}) {
        this.formSelector = options.formSelector || 'form';
        this.excludeInputs = options.excludeInputs || ['input[type="hidden"]', 'input[name="csrf_token"]'];
        this.hasUnsavedChanges = false;
        this.isSubmitting = false;
        this.originalFormData = new Map();
        this.form = null;
        this.warningShown = false;
        
        // Corporate messaging
        this.messages = {
            beforeUnload: 'Configuration changes are pending. Continue without saving?',
            navigationWarning: 'Unsaved Configuration Changes',
            navigationMessage: 'You have unsaved configuration changes that will be lost. Proceed without saving?',
            reloadWarning: 'Confirm Page Reload',
            reloadMessage: 'Configuration changes are pending and will be lost if you reload the page. Proceed with reload?'
        };

        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupDetection());
        } else {
            this.setupDetection();
        }
    }

    setupDetection() {
        this.form = document.querySelector(this.formSelector);
        if (!this.form) {
            console.warn('Enterprise Unsaved Changes: No form found with selector:', this.formSelector);
            return;
        }

        this.captureOriginalState();
        this.attachEventListeners();
        this.setupNavigationInterception();
        this.setupReloadInterception();
    }

    captureOriginalState() {
        const inputs = this.form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (!this.isExcludedInput(input)) {
                const key = input.name || input.id;
                if (key) {
                    if (input.type === 'checkbox' || input.type === 'radio') {
                        this.originalFormData.set(key, input.checked);
                    } else if (input.type === 'file') {
                        this.originalFormData.set(key, input.files);
                    } else {
                        this.originalFormData.set(key, input.value);
                    }
                }
            }
        });
    }

    isExcludedInput(input) {
        return this.excludeInputs.some(selector => input.matches(selector));
    }

    attachEventListeners() {
        const inputs = this.form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            if (!this.isExcludedInput(input)) {
                input.addEventListener('input', () => this.checkForChanges());
                input.addEventListener('change', () => this.checkForChanges());
            }
        });

        // Handle form submission
        this.form.addEventListener('submit', (e) => {
            this.isSubmitting = true;
            this.hasUnsavedChanges = false;
        });

        // Browser beforeunload (cannot be completely overridden for security)
        window.addEventListener('beforeunload', (e) => this.handleBeforeUnload(e));
    }

    checkForChanges() {
        this.hasUnsavedChanges = false;
        
        const inputs = this.form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (!this.isExcludedInput(input)) {
                const key = input.name || input.id;
                if (key && this.originalFormData.has(key)) {
                    let currentValue;
                    let originalValue = this.originalFormData.get(key);

                    if (input.type === 'checkbox' || input.type === 'radio') {
                        currentValue = input.checked;
                    } else if (input.type === 'file') {
                        currentValue = input.files;
                        // File comparison is complex, so we'll mark as changed if files are selected
                        if (input.files.length > 0) {
                            this.hasUnsavedChanges = true;
                            return;
                        }
                    } else {
                        currentValue = input.value;
                    }

                    if (this.normalizeValue(currentValue) !== this.normalizeValue(originalValue)) {
                        this.hasUnsavedChanges = true;
                    }
                }
            }
        });

        this.updateVisualIndicators();
    }

    normalizeValue(value) {
        if (value === undefined || value === null) return '';
        return String(value).trim();
    }

    updateVisualIndicators() {
        // Update unsaved changes indicator if it exists
        const indicators = document.querySelectorAll('#unsaved-indicator, #unsaved-changes-indicator, .unsaved-changes-indicator');
        indicators.forEach(indicator => {
            indicator.style.display = this.hasUnsavedChanges ? 'block' : 'none';
        });
    }

    handleBeforeUnload(e) {
        // This is the ONLY way to show a dialog on page reload/close
        // Custom modals cannot intercept this for security reasons
        if (this.hasUnsavedChanges && !this.isSubmitting) {
            // Modern browsers ignore custom messages and show their own
            e.preventDefault();
            e.returnValue = this.messages.beforeUnload;
            return this.messages.beforeUnload;
        }
    }

    setupNavigationInterception() {
        // Intercept navigation clicks (but NOT reload/close)
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href]');
            if (link && this.hasUnsavedChanges && !this.isSubmitting) {
                const href = link.getAttribute('href');
                if (this.shouldInterceptNavigation(href)) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.showNavigationWarning(href);
                }
            }
        });

        // Intercept form submissions to other endpoints
        document.addEventListener('submit', (e) => {
            if (e.target !== this.form && this.hasUnsavedChanges && !this.isSubmitting) {
                e.preventDefault();
                this.showNavigationWarning(e.target.action || window.location.href);
            }
        });
    }

    setupReloadInterception() {
        // Intercept manual reload attempts via buttons
        document.addEventListener('click', (e) => {
            const button = e.target.closest('button');
            if (button && this.hasUnsavedChanges && !this.isSubmitting) {
                const onclick = button.getAttribute('onclick');
                if (onclick && (onclick.includes('location.reload') || onclick.includes('window.location.reload'))) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.showReloadWarning();
                }
            }
        });

        // Intercept keyboard shortcuts (Ctrl+R, F5)
        document.addEventListener('keydown', (e) => {
            if (this.hasUnsavedChanges && !this.isSubmitting) {
                // F5 or Ctrl+R
                if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
                    // Cannot prevent these - browser will show native dialog
                    // But we can try to show our custom modal first
                    if (!this.warningShown) {
                        e.preventDefault();
                        this.showReloadWarning();
                    }
                }
            }
        });
    }

    shouldInterceptNavigation(href) {
        if (!href) return false;
        if (href.startsWith('#')) return false;
        if (href.startsWith('javascript:')) return false;
        if (href.startsWith('mailto:')) return false;
        if (href.startsWith('tel:')) return false;
        return true;
    }

    showNavigationWarning(targetUrl) {
        if (typeof showCustomConfirmation === 'function') {
            showCustomConfirmation({
                title: this.messages.navigationWarning,
                message: this.messages.navigationMessage,
                confirmText: 'Leave Page',
                cancelText: 'Stay on Page',
                confirmClass: 'btn-warning',
                icon: 'exclamation-triangle',
                onConfirm: () => {
                    this.isSubmitting = true;
                    this.hasUnsavedChanges = false;
                    window.location.href = targetUrl;
                },
                onCancel: () => {
                    // Stay on page - no action needed
                }
            });
        } else {
            // Fallback to browser confirm
            if (confirm(this.messages.navigationMessage)) {
                this.isSubmitting = true;
                this.hasUnsavedChanges = false;
                window.location.href = targetUrl;
            }
        }
    }

    showReloadWarning() {
        this.warningShown = true;
        
        if (typeof showCustomConfirmation === 'function') {
            showCustomConfirmation({
                title: this.messages.reloadWarning,
                message: this.messages.reloadMessage,
                confirmText: 'Reload Page',
                cancelText: 'Cancel',
                confirmClass: 'btn-warning',
                icon: 'sync-alt',
                onConfirm: () => {
                    this.isSubmitting = true;
                    this.hasUnsavedChanges = false;
                    location.reload();
                },
                onCancel: () => {
                    this.warningShown = false;
                }
            });
        } else {
            // Fallback to browser confirm
            if (confirm(this.messages.reloadMessage)) {
                this.isSubmitting = true;
                this.hasUnsavedChanges = false;
                location.reload();
            } else {
                this.warningShown = false;
            }
        }
    }

    // Public methods for external control
    markAsSaved() {
        this.hasUnsavedChanges = false;
        this.isSubmitting = false;
        this.updateVisualIndicators();
        this.captureOriginalState(); // Reset the baseline
    }

    markAsSubmitting() {
        this.isSubmitting = true;
        this.hasUnsavedChanges = false;
        this.updateVisualIndicators();
    }

    reset() {
        this.hasUnsavedChanges = false;
        this.isSubmitting = false;
        this.warningShown = false;
        this.captureOriginalState();
        this.updateVisualIndicators();
    }

    destroy() {
        window.removeEventListener('beforeunload', this.handleBeforeUnload);
        // Note: Cannot remove document event listeners easily without references
        // This is acceptable as the class should persist for the page lifecycle
    }
}

/**
 * ===============================================================================
 * GLOBAL INITIALIZATION AND UTILITY FUNCTIONS
 * ===============================================================================
 */

// Global instance holder
window.enterpriseUnsavedChanges = null;

// Initialize function for easy use in templates
window.initEnterpriseUnsavedChanges = function(options = {}) {
    if (window.enterpriseUnsavedChanges) {
        window.enterpriseUnsavedChanges.destroy();
    }
    
    window.enterpriseUnsavedChanges = new EnterpriseUnsavedChangesHandler(options);
    return window.enterpriseUnsavedChanges;
};

// Backward compatibility with existing code
window.UnsavedChangesDetector = EnterpriseUnsavedChangesHandler;
window.initUnsavedChangesDetector = window.initEnterpriseUnsavedChanges;

/**
 * ===============================================================================
 * AUTO-INITIALIZATION FOR STANDARD CASES
 * ===============================================================================
 */

// Auto-initialize on DOM ready if a form is present
document.addEventListener('DOMContentLoaded', function() {
    // Only auto-initialize if not already initialized and forms are present
    if (!window.enterpriseUnsavedChanges && document.querySelector('form')) {
        // Check if this is likely an interactive form (not just login/simple forms)
        const interactiveForms = document.querySelectorAll('form input[type="text"], form input[type="email"], form textarea, form select');
        if (interactiveForms.length > 2) { // More than just username/password
            window.initEnterpriseUnsavedChanges();
        }
    }
});

/**
 * ===============================================================================
 * ENTERPRISE STANDARDS NOTES
 * ===============================================================================
 * 
 * IMPORTANT: Browser Security Limitations
 * - Page reload/close dialogs MUST use native browser dialogs for security
 * - Custom modals can only intercept navigation clicks, not reload/close
 * - This is a browser security feature and cannot be overridden
 * 
 * Best Practices:
 * 1. Use this class consistently across all pages
 * 2. Always include custom-modals.js before this script
 * 3. Provide visual indicators for unsaved changes
 * 4. Test both navigation and reload scenarios
 * 
 * Corporate Messaging:
 * - All messages use professional, enterprise-appropriate language
 * - Consistent terminology: "Configuration changes" not "changes"
 * - Clear action options: "Leave Page" / "Stay on Page"
 */