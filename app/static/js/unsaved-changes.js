/**
 * ===============================================================================
 * FORTUNE 500 ENTERPRISE UNSAVED CHANGES DETECTION SYSTEM
 * Global solution for consistent behavior across all pages
 * 
 * Features:
 * - 3-button modal (Save Changes, Discard Changes, Cancel)
 * - Comprehensive beforeunload protection system
 * - File input change detection
 * - Form reset capability
 * 
 * Debug Mode:
 * - Enable: window.__enableBeforeUnloadDebug = true
 * - Reports: __reportBeforeUnloadAttempts()
 * - Debug info: __debugBeforeUnload()
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
        this.allInputs = [];
        this.warningShown = false;
        this.beforeUnloadDisabled = false;
        
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

        // Set up the unsaved changes detection system
        this.captureOriginalState();
        this.attachEventListeners();
        this.setupNavigationInterception();
        this.setupReloadInterception();
        
        if (window.__enableBeforeUnloadDebug) {
            console.log('Enterprise Unsaved Changes: Setup complete. Original form data captured:', this.originalFormData.size, 'fields');
        }
    }

    captureOriginalState() {
        // Get ALL inputs on the page, not just those in the main form
        this.allInputs = this.getAllFormInputs();
        
        this.allInputs.forEach(input => {
            if (!this.isExcludedInput(input)) {
                const key = this.getInputKey(input);
                if (key) {
                    if (input.type === 'checkbox' || input.type === 'radio') {
                        this.originalFormData.set(key, input.checked);
                    } else if (input.type === 'file') {
                        this.originalFormData.set(key, input.files ? input.files.length : 0);
                    } else {
                        this.originalFormData.set(key, input.value);
                    }
                    
                    if (window.__enableBeforeUnloadDebug) {
                        console.log(`Captured original state for ${key}: ${input.type} = ${this.originalFormData.get(key)}`);
                    }
                }
            }
        });
        
        console.log(`🔧 Enterprise Unsaved Changes: Captured ${this.originalFormData.size} fields from ${this.allInputs.length} total inputs`);
    }

    getAllFormInputs() {
        // Get inputs from main form
        const formInputs = this.form ? Array.from(this.form.querySelectorAll('input, select, textarea, [contenteditable="true"]')) : [];
        
        // Get inputs that are associated with forms via form attribute
        const allForms = document.querySelectorAll('form');
        const associatedInputs = [];
        
        allForms.forEach(form => {
            const formId = form.id;
            if (formId) {
                const associated = Array.from(document.querySelectorAll(`[form="${formId}"]`));
                associatedInputs.push(...associated);
            }
        });
        
        // Get any other inputs not captured above
        const otherInputs = Array.from(document.querySelectorAll('input, select, textarea')).filter(input => {
            return !formInputs.includes(input) && !associatedInputs.includes(input) && !input.form;
        });
        
        // Combine all inputs and remove duplicates
        const allInputs = [...new Set([...formInputs, ...associatedInputs, ...otherInputs])];
        
        console.log(`🔍 Found inputs: ${formInputs.length} in forms, ${associatedInputs.length} associated, ${otherInputs.length} standalone`);
        
        return allInputs;
    }

    getInputKey(input) {
        // Create a unique key for each input
        const name = input.name;
        const id = input.id;
        const formId = input.form ? input.form.id : (input.getAttribute('form') || 'no-form');
        
        if (name) {
            return `${formId}:${name}`;
        } else if (id) {
            return `${formId}:${id}`;
        }
        return null;
    }

    isExcludedInput(input) {
        return this.excludeInputs.some(selector => input.matches(selector));
    }

    attachEventListeners() {
        this.allInputs.forEach(input => {
            if (!this.isExcludedInput(input)) {
                input.addEventListener('input', () => this.checkForChanges());
                input.addEventListener('change', () => this.checkForChanges());
                
                // Special handling for file inputs
                if (input.type === 'file') {
                    input.addEventListener('change', () => {
                        console.log(`📎 File input changed: ${input.name || input.id}`);
                        this.checkForChanges();
                    });
                }
                
                if (window.__enableBeforeUnloadDebug) {
                    console.log(`🎧 Attached listeners to: ${this.getInputKey(input)}`);
                }
            }
        });

        // Handle form submission
        this.form.addEventListener('submit', (e) => {
            this.isSubmitting = true;
            this.hasUnsavedChanges = false;
        });

        // Completely disable beforeunload events globally
        this.disableAllBeforeUnloadEvents();
    }

    checkForChanges() {
        this.hasUnsavedChanges = false;
        const changedFields = [];
        
        this.allInputs.forEach(input => {
            if (!this.isExcludedInput(input)) {
                const key = this.getInputKey(input);
                if (key && this.originalFormData.has(key)) {
                    let currentValue;
                    let originalValue = this.originalFormData.get(key);
                    let fieldChanged = false;

                    if (input.type === 'checkbox' || input.type === 'radio') {
                        currentValue = input.checked;
                        fieldChanged = currentValue !== originalValue;
                    } else if (input.type === 'file') {
                        const originalFileCount = originalValue;
                        const currentFileCount = input.files ? input.files.length : 0;
                        fieldChanged = originalFileCount !== currentFileCount;
                        if (fieldChanged) {
                            console.log(`📎 File input change detected: ${key} (${originalFileCount} → ${currentFileCount} files)`);
                        }
                    } else {
                        currentValue = input.value;
                        fieldChanged = this.normalizeValue(currentValue) !== this.normalizeValue(originalValue);
                    }

                    if (fieldChanged) {
                        this.hasUnsavedChanges = true;
                        changedFields.push({
                            key: key,
                            name: input.name || input.id || 'unnamed field',
                            type: input.type,
                            original: originalValue,
                            current: input.type === 'file' ? `${input.files ? input.files.length : 0} files` : currentValue
                        });
                        
                        if (window.__enableBeforeUnloadDebug) {
                            console.log(`🔄 Change detected: ${key} (${input.type}) from [${originalValue}] to [${currentValue}]`);
                        }
                    }
                }
            }
        });

        if (window.__enableBeforeUnloadDebug) {
            console.log(`🔍 Unsaved changes check: ${this.hasUnsavedChanges} (${changedFields.length} changed fields)`);
        }
        
        this.updateVisualIndicators(changedFields);
    }

    normalizeValue(value) {
        if (value === undefined || value === null) return '';
        return String(value).trim();
    }

    getChangedFields() {
        const changedFields = [];
        
        if (!this.form) return changedFields;
        
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
                        // File inputs - only consider changed if file selection state changed
                        const originalHadFiles = this.originalFormData.get(key) && this.originalFormData.get(key).length > 0;
                        const currentHasFiles = input.files && input.files.length > 0;
                        
                        if (originalHadFiles !== currentHasFiles) {
                            const fieldName = this.getFieldDisplayName(input);
                            changedFields.push(fieldName);
                        }
                        return; // Skip the rest for file inputs
                    } else {
                        currentValue = input.value;
                    }

                    if (this.normalizeValue(currentValue) !== this.normalizeValue(originalValue)) {
                        // Get a human-readable field name
                        const fieldName = this.getFieldDisplayName(input);
                        changedFields.push(fieldName);
                    }
                }
            }
        });
        
        return changedFields;
    }

    getFieldDisplayName(input) {
        // Try to get a human-readable name for the field
        const label = input.labels && input.labels[0] ? input.labels[0].textContent.trim() : null;
        if (label) return label.replace('*', '').trim(); // Remove required asterisk
        
        // Try data attributes
        if (input.dataset.displayName) return input.dataset.displayName;
        
        // Try placeholder
        if (input.placeholder) return input.placeholder;
        
        // Convert field name to readable format
        const name = input.name || input.id || 'Unknown Field';
        return name.replace(/_/g, ' ').replace(/([A-Z])/g, ' $1').trim()
                   .split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
    }

    updateVisualIndicators(changedFields = []) {
        // Store detailed changed fields info for modal use
        this.changedFields = changedFields;
        
        // Update global unsaved changes indicator from base.html (simple message only)
        if (typeof showUnsavedChangesIndicator === 'function' && typeof hideUnsavedChangesIndicator === 'function') {
            if (this.hasUnsavedChanges && !this.isSubmitting) {
                showUnsavedChangesIndicator(); // No detailed message in the bar
            } else {
                hideUnsavedChangesIndicator();
            }
        }
        
        // Also update any legacy indicators for backward compatibility
        const legacyIndicators = document.querySelectorAll('#unsaved-indicator, #unsaved-changes-indicator, .unsaved-changes-indicator');
        legacyIndicators.forEach(indicator => {
            indicator.style.display = this.hasUnsavedChanges ? 'block' : 'none';
        });
    }


    setupNavigationInterception() {
        // Intercept navigation clicks (but NOT reload/close) - use capture phase to catch early
        document.addEventListener('click', (e) => {
            if (window.__enableBeforeUnloadDebug) {
                console.log('Click event detected on:', e.target);
            }
            
            // First check for buttons that might have navigation in their original onclick or other attributes
            const target = e.target.closest('button') || e.target.closest('a');
            if (target && this.hasUnsavedChanges && !this.isSubmitting) {
                // Check for navigation patterns in various attributes
                const title = target.getAttribute('title') || '';
                const onclick = target.getAttribute('onclick') || '';
                const originalOnclick = target.dataset.originalOnclick || '';
                
                // Look for navigation indicators
                const isNavigationButton = 
                    title.includes('Go') || title.includes('Back') || title.includes('Dashboard') || title.includes('Administration') ||
                    onclick.includes('location') || onclick.includes('history') || onclick.includes('href') ||
                    originalOnclick.includes('location') || originalOnclick.includes('history') ||
                    target.href;
                
                if (isNavigationButton) {
                    if (window.__enableBeforeUnloadDebug) {
                        console.log('Detected navigation button via attributes:', target);
                    }
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    
                    // Extract target URL
                    let targetUrl = target.href;
                    if (!targetUrl && onclick.includes('location.href')) {
                        const match = onclick.match(/location\.href\s*=\s*['"`]([^'"`]+)['"`]/);
                        if (match) targetUrl = match[1];
                    }
                    if (!targetUrl && onclick.includes('history.back')) {
                        targetUrl = 'previous page';
                    }
                    if (!targetUrl) {
                        targetUrl = 'unknown destination';
                    }
                    
                    this.showNavigationWarning(targetUrl);
                    return false;
                }
            }
            
            // Original link detection logic
            const link = e.target.closest('a[href]') || e.target.closest('[onclick*="location"]') || e.target.closest('[onclick*="href"]') || e.target.closest('[onclick*="history"]');
            if (link) {
                let href = link.getAttribute('href');
                let isNavigation = false;
                
                if (href && href !== window.location.href && !href.startsWith('#')) {
                    isNavigation = true;
                } else if (link.onclick) {
                    // Try to extract URL from onclick handlers or detect navigation methods
                    const onclickStr = link.onclick.toString();
                    console.log('Analyzing onclick:', onclickStr);
                    
                    if (onclickStr.includes('location') || onclickStr.includes('href') || onclickStr.includes('window.open') ||
                        onclickStr.includes('history.back') || onclickStr.includes('history.forward') || onclickStr.includes('history.go')) {
                        isNavigation = true;
                        
                        const urlMatch = onclickStr.match(/(?:location\.href|window\.location)\s*=\s*['"`]([^'"`]+)['"`]/);
                        if (urlMatch) {
                            href = urlMatch[1];
                        } else if (onclickStr.includes('history.back')) {
                            href = 'previous page';
                        } else if (onclickStr.includes('history.forward')) {
                            href = 'next page';
                        } else if (onclickStr.includes('history.go')) {
                            href = 'history navigation';
                        } else {
                            href = 'unknown destination';
                        }
                        
                        console.log('Detected navigation from onclick, href set to:', href);
                    } else {
                        console.log('No navigation detected in onclick');
                    }
                }
                
                console.log('Navigation click detected:', href, 'isNavigation:', isNavigation, 'hasUnsavedChanges:', this.hasUnsavedChanges, 'isSubmitting:', this.isSubmitting);
                
                if (this.hasUnsavedChanges && !this.isSubmitting && isNavigation) {
                    console.log('Intercepting navigation to:', href);
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    this.showNavigationWarning(href || 'unknown destination');
                    return false;
                }
            }
        }, true); // Use capture phase to intercept early

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
        
        // Allow our special navigation cases
        if (href === 'previous page' || href === 'next page' || href === 'history navigation' || href === 'unknown destination') {
            return true;
        }
        
        return true;
    }

    showNavigationWarning(targetUrl) {
        // Get the detailed message with changed fields
        const detailedMessage = this.getDetailedChangedFieldsMessage();
        
        // Convert newlines to HTML breaks for display in modal
        const enhancedMessage = detailedMessage.replace(/\n/g, '<br>');
        
        // Always try to use the enhanced modal first
        this.showEnhancedUnsavedChangesModal({
            title: this.messages.navigationWarning,
            message: enhancedMessage,
            targetUrl: targetUrl,
            onSave: () => {
                // Save the form and then navigate
                this.saveAndThenNavigate(targetUrl);
            },
            onDiscard: () => {
                // Reset form to original state and then navigate
                this.discardAndThenNavigate(targetUrl);
            },
            onCancel: () => {
                // Stay on page - no action needed
            }
        });
    }

    showReloadWarning() {
        this.warningShown = true;
        
        // Get the detailed message with changed fields
        const detailedMessage = this.getDetailedChangedFieldsMessage();
        
        // Convert newlines to HTML breaks for display in modal
        const enhancedMessage = detailedMessage.replace(/\n/g, '<br>');
        
        // Always try to use the enhanced modal first
        this.showEnhancedUnsavedChangesModal({
            title: this.messages.reloadWarning,
            message: enhancedMessage,
            onSave: () => {
                // Save the form and then reload
                this.saveAndThenReload();
            },
            onDiscard: () => {
                // Reset form to original state and reload
                this.discardAndThenReload();
            },
            onCancel: () => {
                this.warningShown = false;
            }
        });
    }

    // Enhanced modal method - embedded within the class
    showEnhancedUnsavedChangesModal(options) {
        const {
            title = 'Unsaved Configuration Changes',
            message = 'You have unsaved configuration changes that will be lost. What would you like to do?',
            onSave = null,
            onDiscard = null,
            onCancel = null,
            targetUrl = null
        } = options;

        // Generate unique IDs to avoid conflicts
        const modalId = 'enhancedUnsavedChangesModal_' + Date.now();
        const saveButtonId = 'enhancedSaveBtn_' + Date.now();
        const discardButtonId = 'enhancedDiscardBtn_' + Date.now();

        // Create enhanced modal HTML with 3 buttons
        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content border-warning">
                        <div class="modal-header bg-warning text-dark">
                            <h5 class="modal-title">
                                <i class="fas fa-exclamation-triangle me-2"></i>${title}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p class="mb-3">${message}</p>
                            <div class="alert alert-info mb-0">
                                <i class="fas fa-info-circle me-2"></i>
                                <strong>Save Changes:</strong> Save your current work and continue<br>
                                <strong>Discard Changes:</strong> Abandon your changes and continue<br>
                                <strong>Cancel:</strong> Stay on this page to continue editing
                            </div>
                        </div>
                        <div class="modal-footer justify-content-between">
                            <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">
                                <i class="fas fa-times me-1"></i>Cancel
                            </button>
                            <div class="btn-group">
                                <button type="button" class="btn btn-outline-success" id="${saveButtonId}">
                                    <i class="fas fa-save me-1"></i>Save Changes
                                </button>
                                <button type="button" class="btn btn-outline-warning" id="${discardButtonId}">
                                    <i class="fas fa-trash-alt me-1"></i>Discard Changes
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove any existing enhanced modals
        document.querySelectorAll('[id^="enhancedUnsavedChangesModal_"]').forEach(modal => modal.remove());

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById(modalId));
        modal.show();

        // Handle Save Changes click
        document.getElementById(saveButtonId).onclick = function() {
            const btn = this;
            const originalHtml = btn.innerHTML;
            
            // Show loading state
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
            btn.disabled = true;
            
            modal.hide();
            if (onSave) onSave();
        };

        // Handle Discard Changes click
        document.getElementById(discardButtonId).onclick = function() {
            modal.hide();
            if (onDiscard) onDiscard();
        };

        // Handle modal close/cancel
        document.getElementById(modalId).addEventListener('hidden.bs.modal', function(e) {
            // Only trigger onCancel if the modal was closed via the X button or Cancel button
            // Not if it was closed via Save or Discard buttons
            if (e.target === this && !this.classList.contains('manual-close')) {
                if (onCancel) onCancel();
            }
            this.remove();
        });

        // Mark manual close when using action buttons
        document.getElementById(saveButtonId).addEventListener('click', function() {
            document.getElementById(modalId).classList.add('manual-close');
        });
        
        document.getElementById(discardButtonId).addEventListener('click', function() {
            document.getElementById(modalId).classList.add('manual-close');
        });
    }

    // Simplified save and navigate - actually save the form, then navigate
    saveAndThenNavigate(targetUrl) {
        console.log('💾 saveAndThenNavigate called with targetUrl:', targetUrl);
        
        if (this.form) {
            // Set flags to prevent warnings during save
            this.isSubmitting = true;
            this.hasUnsavedChanges = false;
            
            // Submit the form normally - this will save and navigate automatically
            this.form.submit();
        } else {
            // No form to save, just navigate
            this.performNavigation(targetUrl);
        }
    }
    
    // Simplified discard and navigate - reset form to original state, then navigate
    discardAndThenNavigate(targetUrl) {
        console.log('🗑️ discardAndThenNavigate called with targetUrl:', targetUrl);
        
        // Reset all form fields to their original values
        this.resetFormToOriginalState();
        
        // Clear the unsaved changes flags
        this.hasUnsavedChanges = false;
        this.isSubmitting = true;
        
        // Small delay to ensure form reset is processed
        setTimeout(() => {
            this.performNavigation(targetUrl);
        }, 50);
    }
    
    // Reset form to original state to eliminate unsaved changes
    resetFormToOriginalState() {
        console.log('🔄 Resetting form to original state');
        
        if (!this.form) return;
        
        const inputs = this.form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (!this.isExcludedInput(input)) {
                const key = input.name || input.id;
                if (key && this.originalFormData.has(key)) {
                    const originalValue = this.originalFormData.get(key);
                    
                    if (input.type === 'checkbox' || input.type === 'radio') {
                        input.checked = originalValue;
                    } else if (input.type === 'file') {
                        // Can't reset file inputs, but clear them
                        input.value = '';
                    } else {
                        input.value = originalValue;
                    }
                    
                    // Trigger change event for any listeners
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        });
        
        // Update visual indicators
        this.updateVisualIndicators();
        console.log('✅ Form reset complete');
    }

    disableAllBeforeUnloadEvents() {
        // Set up beforeunload protection system (debug mode available via window.__enableBeforeUnloadDebug = true)
        const debugMode = window.__enableBeforeUnloadDebug || false;
        
        // Create a comprehensive debug system to track all beforeunload activity
        this.setupBeforeUnloadDebugging();
        
        // NUCLEAR APPROACH: Override ALL possible ways to set beforeunload handlers
        const originalAddEventListener = window.addEventListener;
        const originalRemoveEventListener = window.removeEventListener;
        
        // Track all beforeunload attempts
        window.beforeunloadAttempts = [];
        
        // Override addEventListener
        window.addEventListener = function(type, listener, options) {
            if (type === 'beforeunload') {
                if (debugMode) {
                    console.log('🚨 ATTEMPTED beforeunload registration - BLOCKED!');
                    console.log('📍 Stack trace:', new Error().stack);
                    console.log('🔍 Listener:', listener.toString().substring(0, 200));
                }
                
                window.beforeunloadAttempts.push({
                    type: 'addEventListener',
                    listener: listener.toString().substring(0, 200),
                    stack: new Error().stack,
                    timestamp: Date.now()
                });
                return; // Block it completely
            }
            return originalAddEventListener.call(this, type, listener, options);
        };
        
        // Override removeEventListener
        window.removeEventListener = function(type, listener, options) {
            if (type === 'beforeunload' && debugMode) {
                console.log('🔍 ATTEMPTED beforeunload removal');
                console.log('📍 Stack trace:', new Error().stack);
            }
            return originalRemoveEventListener.call(this, type, listener, options);
        };
        
        // Override window.onbeforeunload assignment with getter/setter
        let beforeUnloadHandler = null;
        Object.defineProperty(window, 'onbeforeunload', {
            get: function() {
                if (debugMode) console.log('🔍 window.onbeforeunload accessed (GET)');
                return beforeUnloadHandler;
            },
            set: function(handler) {
                if (debugMode) {
                    console.log('🚨 ATTEMPTED onbeforeunload assignment - BLOCKED!');
                    console.log('📍 Stack trace:', new Error().stack);
                    console.log('🔍 Handler:', handler ? handler.toString().substring(0, 200) : 'null');
                }
                
                window.beforeunloadAttempts.push({
                    type: 'onbeforeunload',
                    handler: handler ? handler.toString().substring(0, 200) : 'null',
                    stack: new Error().stack,
                    timestamp: Date.now()
                });
                
                // Don't actually set it
                beforeUnloadHandler = null;
            }
        });
        
        // Add our own beforeunload handler that runs FIRST (capture phase) 
        originalAddEventListener.call(window, 'beforeunload', function(e) {
            if (debugMode) {
                console.log('🔄 OUR FIRST-PHASE beforeunload handler triggered');
                console.log('🔍 Event.returnValue at start:', e.returnValue);
            }
            
            // Immediately override returnValue setter to catch what's setting it
            let returnValueSetAttempts = [];
            const originalDescriptor = Object.getOwnPropertyDescriptor(e, 'returnValue');
            
            Object.defineProperty(e, 'returnValue', {
                get: function() { 
                    return undefined; // Always return undefined
                },
                set: function(value) { 
                    if (debugMode) {
                        console.log('🚨 CAUGHT: Something tried to set returnValue to:', value);
                        console.log('📍 Stack trace of setter:', new Error().stack);
                    }
                    returnValueSetAttempts.push({
                        value: value,
                        stack: new Error().stack,
                        timestamp: Date.now()
                    });
                    // Don't actually set it
                }
            });
            
            // Override preventDefault to catch that too
            const originalPreventDefault = e.preventDefault;
            e.preventDefault = function() {
                if (debugMode) {
                    console.log('🚨 CAUGHT: Something called preventDefault()');
                    console.log('📍 Stack trace of preventDefault:', new Error().stack);
                }
                returnValueSetAttempts.push({
                    value: 'preventDefault called',
                    stack: new Error().stack,
                    timestamp: Date.now()
                });
                // Don't actually call preventDefault
            };
            
            // Store the attempts globally for inspection
            window.returnValueSetAttempts = returnValueSetAttempts;
            
            if (debugMode) console.log('🔍 Returnvalue setter monitoring active');
            return undefined;
        }, true); // Use capture phase to run FIRST
        
        // Add a second handler that runs in bubble phase to clean up
        originalAddEventListener.call(window, 'beforeunload', function(e) {
            if (debugMode) {
                console.log('🔄 OUR CLEANUP beforeunload handler triggered');
                console.log('🔍 Final Event.returnValue:', e.returnValue);
                console.log('🔍 ReturnValue set attempts:', window.returnValueSetAttempts);
            }
            
            // Final nuclear cleanup
            delete e.returnValue;
            e.returnValue = undefined;
            
            return undefined;
        }, false); // Bubble phase to run LAST
        
        // Add global function to report all attempts
        window.__reportBeforeUnloadAttempts = () => {
            console.log('=== BEFOREUNLOAD ATTEMPTS REPORT ===');
            console.log('Total handler registration attempts:', window.beforeunloadAttempts.length);
            window.beforeunloadAttempts.forEach((attempt, index) => {
                console.log(`Attempt ${index + 1}:`, attempt);
            });
            
            if (window.returnValueSetAttempts) {
                console.log('=== RETURNVALUE SET ATTEMPTS ===');
                console.log('Total returnValue set attempts:', window.returnValueSetAttempts.length);
                window.returnValueSetAttempts.forEach((attempt, index) => {
                    console.log(`ReturnValue Attempt ${index + 1}:`, attempt);
                });
            }
            console.log('=== END REPORT ===');
        };
    }
    
    setupBeforeUnloadDebugging() {
        console.log('🔍 Setting up comprehensive beforeunload debugging...');
        
        // Debug all existing event listeners
        this.debugExistingEventListeners();
        
        // Monitor form changes that might trigger beforeunload
        this.debugFormChanges();
        
        // Monitor any window.onbeforeunload access
        this.debugWindowOnBeforeUnload();
        
        // Create a global debug function
        window.__debugBeforeUnload = () => {
            console.log('=== BEFOREUNLOAD DEBUG REPORT ===');
            console.log('🔍 window.onbeforeunload:', window.onbeforeunload);
            console.log('🔍 Our hasUnsavedChanges:', this.hasUnsavedChanges);
            console.log('🔍 Our isSubmitting:', this.isSubmitting);
            console.log('🔍 Form dirty check:', this.checkFormDirty());
            console.log('🔍 Changed fields:', this.getChangedFields());
            this.debugAllScripts();
            console.log('=== END DEBUG REPORT ===');
        };
        
        console.log('✅ Debug system ready. Call __debugBeforeUnload() for detailed report.');
    }
    
    debugExistingEventListeners() {
        console.log('🔍 Scanning for existing beforeunload listeners...');
        
        // Try to access the internal event listeners (browser-specific)
        if (window.getEventListeners) {
            const listeners = window.getEventListeners(window);
            console.log('🔍 Window event listeners:', listeners);
            if (listeners.beforeunload) {
                console.log('⚠️ FOUND existing beforeunload listeners:', listeners.beforeunload);
            }
        }
        
        // Check for common beforeunload patterns
        const scripts = document.querySelectorAll('script');
        scripts.forEach((script, index) => {
            if (script.textContent && script.textContent.includes('beforeunload')) {
                console.log(`⚠️ FOUND beforeunload in script ${index}:`, script.textContent.substring(0, 200));
            }
        });
    }
    
    debugFormChanges() {
        console.log('🔍 Setting up form change monitoring...');
        
        if (this.form) {
            const originalCheckForChanges = this.checkForChanges.bind(this);
            this.checkForChanges = function() {
                console.log('🔍 checkForChanges called');
                const result = originalCheckForChanges();
                console.log('🔍 hasUnsavedChanges result:', this.hasUnsavedChanges);
                return result;
            };
        }
    }
    
    debugWindowOnBeforeUnload() {
        // Monitor any access to window.onbeforeunload
        let currentHandler = window.onbeforeunload;
        Object.defineProperty(window, '__originalOnBeforeUnload', {
            get: function() {
                console.log('🔍 window.onbeforeunload accessed (GET)');
                console.log('📍 Stack trace:', new Error().stack);
                return currentHandler;
            },
            set: function(handler) {
                console.log('🔍 window.onbeforeunload accessed (SET)');
                console.log('📍 Stack trace:', new Error().stack);
                console.log('🔍 New handler:', handler);
                currentHandler = handler;
            }
        });
    }
    
    checkFormDirty() {
        if (!this.form) return false;
        
        let isDirty = false;
        const inputs = this.form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (!this.isExcludedInput(input)) {
                const key = input.name || input.id;
                if (key && this.originalFormData.has(key)) {
                    const originalValue = this.originalFormData.get(key);
                    let currentValue;
                    
                    if (input.type === 'checkbox' || input.type === 'radio') {
                        currentValue = input.checked;
                        if (this.normalizeValue(currentValue) !== this.normalizeValue(originalValue)) {
                            console.log(`🔍 Field ${key} is dirty: "${originalValue}" → "${currentValue}"`);
                            isDirty = true;
                        }
                    } else if (input.type === 'file') {
                        // File inputs - check if file selection state changed
                        const originalHadFiles = originalValue && originalValue.length > 0;
                        const currentHasFiles = input.files && input.files.length > 0;
                        
                        if (originalHadFiles !== currentHasFiles) {
                            console.log(`🔍 File field ${key} is dirty: originalHadFiles=${originalHadFiles}, currentHasFiles=${currentHasFiles}`);
                            isDirty = true;
                        }
                    } else {
                        currentValue = input.value;
                        if (this.normalizeValue(currentValue) !== this.normalizeValue(originalValue)) {
                            console.log(`🔍 Field ${key} is dirty: "${originalValue}" → "${currentValue}"`);
                            isDirty = true;
                        }
                    }
                }
            }
        });
        
        return isDirty;
    }
    
    debugAllScripts() {
        console.log('🔍 Scanning all loaded scripts for beforeunload patterns...');
        
        const scripts = document.querySelectorAll('script[src]');
        scripts.forEach((script, index) => {
            console.log(`📜 Script ${index}: ${script.src}`);
        });
        
        // Check for inline scripts with beforeunload
        const inlineScripts = document.querySelectorAll('script:not([src])');
        inlineScripts.forEach((script, index) => {
            if (script.textContent.includes('beforeunload') || script.textContent.includes('onbeforeunload')) {
                console.log(`⚠️ INLINE SCRIPT ${index} contains beforeunload:`, script.textContent.substring(0, 500));
            }
        });
    }

    performNavigation(targetUrl) {
        if (targetUrl === 'previous page') {
            history.back();
        } else if (targetUrl === 'next page') {
            history.forward();
        } else if (targetUrl === 'history navigation') {
            history.back(); // Default to back for history navigation
        } else if (targetUrl && targetUrl !== 'unknown destination') {
            window.location.href = targetUrl;
        } else {
            // Fallback - go back
            history.back();
        }
    }

    // Simplified save and reload
    saveAndThenReload() {
        console.log('💾 saveAndThenReload called');
        
        if (this.form) {
            // Set flags to prevent warnings during save
            this.isSubmitting = true;
            this.hasUnsavedChanges = false;
            
            // Submit the form - will save and redirect back to same page
            this.form.submit();
        } else {
            // No form to save, just reload
            location.reload();
        }
    }
    
    // Simplified discard and reload
    discardAndThenReload() {
        console.log('🗑️ discardAndThenReload called');
        
        // Reset form to original state
        this.resetFormToOriginalState();
        
        // Clear flags and reload
        this.hasUnsavedChanges = false;
        this.isSubmitting = true;
        
        setTimeout(() => {
            location.reload();
        }, 50);
    }


    // Public method to get detailed changed fields for modals
    getDetailedChangedFieldsMessage() {
        if (!this.changedFields || this.changedFields.length === 0) {
            return 'You have made changes that have not been saved yet.';
        }
        
        // Create a mapping of technical field names to user-friendly labels
        const fieldLabelMap = this.createFieldLabelMapping();
        
        const fieldLabels = this.changedFields.map(field => {
            const friendlyName = fieldLabelMap[field.name] || this.beautifyFieldName(field.name);
            return friendlyName;
        });
        
        let message = 'You have made changes to the following fields that have not been saved yet:\n\n';
        
        if (fieldLabels.length <= 5) {
            message += `• ${fieldLabels.join('\n• ')}`;
        } else {
            message += `• ${fieldLabels.slice(0, 5).join('\n• ')}\n• ... and ${fieldLabels.length - 5} more fields`;
        }
        
        return message;
    }

    // Create field label mapping based on page context and form labels
    createFieldLabelMapping() {
        const mapping = {};
        
        // Try to extract labels from actual form elements on the page
        const inputs = document.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            const fieldName = input.name || input.id;
            if (fieldName) {
                // Look for associated label element
                let label = null;
                
                // Method 1: Find label with 'for' attribute matching field id
                if (input.id) {
                    label = document.querySelector(`label[for="${input.id}"]`);
                }
                
                // Method 2: Find label that contains this input
                if (!label) {
                    label = input.closest('label') || input.parentElement.querySelector('label');
                }
                
                // Method 3: Look for label in parent elements
                if (!label) {
                    let parent = input.parentElement;
                    while (parent && !label) {
                        label = parent.querySelector('label');
                        parent = parent.parentElement;
                    }
                }
                
                if (label && label.textContent.trim()) {
                    // Clean up the label text (remove asterisks, colons, extra whitespace)
                    let labelText = label.textContent.trim()
                        .replace(/[\*:]/g, '')
                        .replace(/\s+/g, ' ')
                        .trim();
                    
                    // If label is too long, use a shorter version
                    if (labelText.length > 50) {
                        labelText = labelText.substring(0, 47) + '...';
                    }
                    
                    if (labelText) {
                        mapping[fieldName] = labelText;
                    }
                }
            }
        });
        
        // Fallback mappings for common field patterns
        const fallbackMappings = {
            'version': 'Version',
            'overview_logic': 'Strategic Approach and Fundamental Reasoning',
            'primary_chart_tf': 'Analysis Timeframe',
            'execution_chart_tf': 'Execution Timeframe',
            'context_chart_tf': 'Context Analysis',
            'scenario_number': 'Configuration ID',
            'scenario_name': 'Strategic Framework Name',
            'short_description': 'Executive Summary',
            'detailed_description': 'Strategic Overview',
            'hod_lod_implication': 'HOD/LOD Market Implications',
            'directional_bias': 'Directional Bias',
            'key_considerations': 'Key Considerations',
            'models_to_activate': 'Recommended Models',
            'models_to_avoid': 'Restricted Models',
            'preferred_timeframes': 'Optimal Timeframes',
            'entry_strategy': 'Entry Strategy',
            'typical_targets': 'Target Objectives',
            'alert_criteria': 'Alert Threshold',
            'confirmation_criteria': 'Confirmation Protocol',
            'stop_loss_guidance': 'Loss Mitigation Protocol',
            'risk_guidance': 'Risk Management Framework',
            'risk_percentage': 'Risk Percentage',
            'is_active': 'Active Status',
            'username': 'Username',
            'email': 'Email Address',
            'name': 'Full Name',
            'role': 'User Role'
        };
        
        // Apply fallback mappings for any missing fields
        Object.keys(fallbackMappings).forEach(key => {
            if (!mapping[key]) {
                mapping[key] = fallbackMappings[key];
            }
        });
        
        return mapping;
    }

    // Beautify field names as a last resort
    beautifyFieldName(fieldName) {
        if (!fieldName) return 'Unknown Field';
        
        return fieldName
            .replace(/_/g, ' ')
            .replace(/([a-z])([A-Z])/g, '$1 $2')
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ');
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
        // No beforeunload handler to remove
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
            console.log('Auto-initializing Enterprise Unsaved Changes for', interactiveForms.length, 'interactive form fields');
            window.initEnterpriseUnsavedChanges();
            
            // Add additional global click interceptor as backup
            setTimeout(() => {
                if (window.enterpriseUnsavedChanges) {
                    setupGlobalNavigationBackup();
                }
            }, 100);
        }
    }
});

// Backup global navigation interceptor
function setupGlobalNavigationBackup() {
    console.log('Setting up global navigation backup interceptor');
    
    document.addEventListener('click', function(e) {
        if (window.enterpriseUnsavedChanges && window.enterpriseUnsavedChanges.hasUnsavedChanges && !window.enterpriseUnsavedChanges.isSubmitting) {
            const target = e.target;
            const link = target.closest('a') || target.closest('[onclick]') || target.closest('button');
            
            if (link) {
                console.log('Global backup interceptor: Click detected on', link);
                
                // Check for navigation patterns
                let willNavigate = false;
                let targetUrl = null;
                
                if (link.href && link.href !== window.location.href && !link.href.startsWith('#')) {
                    willNavigate = true;
                    targetUrl = link.href;
                } else if (link.onclick) {
                    const onclickStr = link.onclick.toString();
                    if (onclickStr.includes('location') || onclickStr.includes('href') || onclickStr.includes('window.open') || 
                        onclickStr.includes('history.back') || onclickStr.includes('history.forward') || onclickStr.includes('history.go')) {
                        willNavigate = true;
                        
                        // Try to extract URL
                        const urlMatch = onclickStr.match(/(?:location\.href|window\.location)\s*=\s*['"`]([^'"`]+)['"`]/);
                        if (urlMatch) {
                            targetUrl = urlMatch[1];
                        } else if (onclickStr.includes('history.back')) {
                            targetUrl = 'previous page';
                        } else if (onclickStr.includes('history.forward')) {
                            targetUrl = 'next page';
                        } else if (onclickStr.includes('history.go')) {
                            targetUrl = 'history navigation';
                        } else {
                            targetUrl = 'unknown destination';
                        }
                    }
                }
                
                if (willNavigate) {
                    console.log('Global backup interceptor: Navigation detected to', targetUrl);
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    
                    // Show the enhanced modal
                    window.enterpriseUnsavedChanges.showNavigationWarning(targetUrl || link.href || window.location.href);
                    return false;
                }
            }
        }
    }, true); // Use capture phase
}


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