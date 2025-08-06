function showCustomConfirmation(titleOrOptions, message, confirmClass, icon) {
    // Support both new object-based syntax and legacy parameter-based syntax
    let options;
    
    if (typeof titleOrOptions === 'object') {
        // New object-based syntax
        options = titleOrOptions;
    } else {
        // Legacy parameter-based syntax - convert to object
        options = {
            title: titleOrOptions || 'Confirm Action',
            message: message || 'Are you sure?',
            confirmClass: confirmClass || 'btn-primary',
            icon: icon || null
        };
    }
    
    const {
        title = 'Confirm Action',
        message: msg = 'Are you sure?',
        confirmText = 'Confirm',
        cancelText = 'Cancel',
        confirmClass: btnClass = 'btn-primary',
        icon: iconName = null,
        iconClass = '',
        onConfirm = null,
        onCancel = null
    } = options;

    // Determine theme based on confirmClass
    let headerClass = '';
    let modalClass = '';

    if (btnClass.includes('btn-danger')) {
        headerClass = 'bg-danger text-white';
        modalClass = 'border-danger';
    } else if (btnClass.includes('btn-warning')) {
        headerClass = 'bg-warning text-dark';
        modalClass = 'border-warning';
    } else if (btnClass.includes('btn-success')) {
        headerClass = 'bg-success text-white';
        modalClass = 'border-success';
    } else if (btnClass.includes('btn-info')) {
        headerClass = 'bg-info text-white';
        modalClass = 'border-info';
    } else {
        headerClass = 'bg-primary text-white';
        modalClass = 'border-primary';
    }

    // Build icon HTML if provided
    const iconHtml = iconName ? `<i class="fas fa-${iconName} me-2"></i>` : '';
    
    // Create promise for legacy support
    return new Promise((resolve, reject) => {

    // Create modal HTML with themed colors
    const modalHtml = `
        <div class="modal fade" id="customConfirmModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content ${modalClass}">
                    <div class="modal-header ${headerClass}">
                        <h5 class="modal-title">${iconHtml}${title}</h5>
                        <button type="button" class="btn-close ${headerClass.includes('text-white') ? 'btn-close-white' : ''}" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p class="mb-0">${msg}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${cancelText}</button>
                        <button type="button" class="btn ${btnClass}" id="customConfirmBtn">${confirmText}</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if present
    const existingModal = document.getElementById('customConfirmModal');
    if (existingModal) existingModal.remove();

    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('customConfirmModal'));
    modal.show();

        // Handle confirm click
        document.getElementById('customConfirmBtn').onclick = function() {
            modal.hide();
            if (onConfirm) onConfirm();
            resolve(true); // Resolve promise with true for confirm
        };

        // Handle cancel (modal close)
        document.getElementById('customConfirmModal').addEventListener('hidden.bs.modal', function() {
            if (onCancel) onCancel();
            resolve(false); // Resolve promise with false for cancel
            this.remove();
        });
    });
}

