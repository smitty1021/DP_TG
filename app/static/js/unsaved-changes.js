class UnsavedChangesDetector {
    constructor(formSelector) {
        this.form = document.querySelector(formSelector);
        if (!this.form) return;

        this.originalFormData = new FormData(this.form);
        this.originalValues = this.serializeFormData(this.originalFormData);
        this.hasUnsavedChanges = false;
        this.isSubmitting = false;
        this.warningElement = document.getElementById('unsaved-warning');

        this.init();
    }

    init() {
        this.form.addEventListener('input', () => this.checkForChanges());
        this.form.addEventListener('change', () => this.checkForChanges());
        this.form.addEventListener('submit', (e) => {
            this.isSubmitting = true;
            this.hasUnsavedChanges = false;
        });

        window.addEventListener('beforeunload', (e) => this.handleBeforeUnload(e));
        this.attachNavigationWarnings();
    }

    serializeFormData(formData) {
        const data = {};
        for (let [key, value] of formData.entries()) {
            if (data[key]) {
                if (Array.isArray(data[key])) {
                    data[key].push(value);
                } else {
                    data[key] = [data[key], value];
                }
            } else {
                data[key] = value;
            }
        }
        return data;
    }

    getCurrentFormData() {
        const currentFormData = new FormData(this.form);
        return this.serializeFormData(currentFormData);
    }

    checkForChanges() {
        if (this.isSubmitting) return;

        const currentValues = this.getCurrentFormData();
        const hasChanges = this.compareFormData(this.originalValues, currentValues);

        // Optional: Add debugging to see what's being compared
        if (console && typeof console.log === 'function') {
            console.log('🔍 Form change check:', {
                hasChanges,
                original: this.originalValues,
                current: currentValues
            });
        }

        // Just track the state, don't show any header warning
        this.hasUnsavedChanges = hasChanges;
    }

    compareFormData(original, current) {
        const allKeys = new Set([...Object.keys(original), ...Object.keys(current)]);

        for (let key of allKeys) {
            const originalValue = original[key];
            const currentValue = current[key];

            // Handle arrays (multi-select values)
            if (Array.isArray(originalValue) || Array.isArray(currentValue)) {
                const origArray = Array.isArray(originalValue) ? originalValue.sort() : (originalValue ? [originalValue] : []);
                const currArray = Array.isArray(currentValue) ? currentValue.sort() : (currentValue ? [currentValue] : []);

                if (origArray.length !== currArray.length ||
                    !origArray.every((val, index) => val === currArray[index])) {
                    return true;
                }
            } else {
                // Normalize values for comparison
                const normalizedOriginal = this.normalizeValue(originalValue);
                const normalizedCurrent = this.normalizeValue(currentValue);

                if (normalizedOriginal !== normalizedCurrent) {
                    return true;
                }
            }
        }

        return false;
    }

    normalizeValue(value) {
        // Handle undefined, null, and empty string as equivalent
        if (value === undefined || value === null || value === '') {
            return '';
        }

        // Convert to string and trim whitespace
        return String(value).trim();
    }

    handleBeforeUnload(e) {
        if (this.hasUnsavedChanges && !this.isSubmitting) {
            // Only use browser's beforeunload for page refresh/close
            const message = 'You have unsaved changes. Are you sure you want to leave?';
            e.preventDefault();
            e.returnValue = message;
            return message;
        }
    }

    attachNavigationWarnings() {
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href]');
            if (link && this.hasUnsavedChanges && !this.isSubmitting) {
                const href = link.getAttribute('href');
                if (href && !href.startsWith('#') && !href.startsWith('javascript:')) {
                    e.preventDefault();

                    // Use your custom modal instead of browser confirm
                    if (typeof showCustomConfirmation === 'function') {
                        showCustomConfirmation({
                            title: 'Unsaved Changes',
                            message: 'You have unsaved changes that will be lost if you leave this page. Are you sure you want to continue?',
                            confirmText: 'Leave Page',
                            cancelText: 'Stay on Page',
                            confirmClass: 'btn-warning',
                            icon: 'exclamation-triangle',
                            onConfirm: () => {
                                this.isSubmitting = true; // Prevent double warning
                                window.location.href = href;
                            }
                        });
                    } else {
                        // Fallback to browser confirm if custom modal not available
                        if (confirm('You have unsaved changes. Are you sure you want to leave this page?')) {
                            this.isSubmitting = true;
                            window.location.href = href;
                        }
                    }
                    return false;
                }
            }
        });
    }

    markAsSaved() {
        this.originalFormData = new FormData(this.form);
        this.originalValues = this.serializeFormData(this.originalFormData);
        this.hasUnsavedChanges = false;
        // Remove hideWarning() call
    }

    resetFormState() {
        this.originalFormData = new FormData(this.form);
        this.originalValues = this.serializeFormData(this.originalFormData);
        this.hasUnsavedChanges = false;
        // Remove hideWarning() call
    }
}

// Global initialization function
window.initUnsavedChangesDetector = function(formSelector = 'form') {
    return new UnsavedChangesDetector(formSelector);
};