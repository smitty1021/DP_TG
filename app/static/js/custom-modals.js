function showCustomConfirmation(options) {
    const {
        title = 'Confirm Action',
        message = 'Are you sure?',
        confirmText = 'Confirm',
        cancelText = 'Cancel',
        confirmClass = 'btn-primary',
        icon = null,
        iconClass = '',
        onConfirm = null,
        onCancel = null
    } = options;

    // Determine theme based on confirmClass
    let headerClass = '';
    let modalClass = '';

    if (confirmClass.includes('btn-danger')) {
        headerClass = 'bg-danger text-white';
        modalClass = 'border-danger';
    } else if (confirmClass.includes('btn-warning')) {
        headerClass = 'bg-warning text-dark';
        modalClass = 'border-warning';
    } else if (confirmClass.includes('btn-success')) {
        headerClass = 'bg-success text-white';
        modalClass = 'border-success';
    } else if (confirmClass.includes('btn-info')) {
        headerClass = 'bg-info text-white';
        modalClass = 'border-info';
    } else {
        headerClass = 'bg-primary text-white';
        modalClass = 'border-primary';
    }

    // Build icon HTML if provided
    const iconHtml = icon ? `<i class="fas fa-${icon} me-2"></i>` : '';

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
                        <p class="mb-0">${message}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${cancelText}</button>
                        <button type="button" class="btn ${confirmClass}" id="customConfirmBtn">${confirmText}</button>
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
    };

    // Handle cancel (modal close)
    //... (rest of the function)
    document.getElementById('customConfirmModal').addEventListener('hidden.bs.modal', function() {
        if (onCancel) onCancel();
        this.remove();
    });
}

