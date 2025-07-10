// Add this JavaScript to your P12 scenario list template or a separate JS file

// Global image upload function for P12 scenarios
function uploadP12Image(scenarioId, fileInput, scenarioName) {
    if (!fileInput.files || !fileInput.files[0]) {
        alert('Please select an image file');
        return;
    }

    const formData = new FormData();
    formData.append('image', fileInput.files[0]);
    formData.append('caption', `P12 Scenario ${scenarioName} Example`);
    formData.append('replace_existing', 'true'); // Replace existing image

    // Get CSRF token
    const csrfToken = document.querySelector('meta[name=csrf-token]')?.content ||
                     document.querySelector('input[name=csrf_token]')?.value;

    // Show loading state
    const uploadButton = document.querySelector(`#upload-btn-${scenarioId}`);
    if (uploadButton) {
        const originalText = uploadButton.innerHTML;
        uploadButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
        uploadButton.disabled = true;
    }

    fetch(`/admin/p12-scenarios/upload-image/${scenarioId}`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Image uploaded:', data.image_url);

            // Update the UI - refresh the page or update the image preview
            location.reload(); // Simple approach

            // OR update the UI dynamically:
            // updateImagePreview(scenarioId, data.image_url, data.thumbnail_url);

        } else {
            console.error('Upload failed:', data.error);
            alert('Upload failed: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error uploading image:', error);
        alert('Error uploading image: ' + error.message);
    })
    .finally(() => {
        // Restore button state
        if (uploadButton) {
            uploadButton.innerHTML = '<i class="fas fa-upload"></i>';
            uploadButton.disabled = false;
        }
    });
}

// Function to show image upload modal/dialog
function showImageUploadDialog(scenarioId, scenarioName) {
    // Create or show upload modal
    const modalHtml = `
        <div class="modal fade" id="uploadModal${scenarioId}" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Upload Image for ${scenarioName}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="uploadForm${scenarioId}">
                            <div class="mb-3">
                                <label class="form-label">Select Image</label>
                                <input type="file" class="form-control" id="imageFile${scenarioId}" 
                                       accept="image/*" required>
                                <div class="form-text">Supported formats: PNG, JPG, JPEG, GIF, WebP (Max 5MB)</div>
                            </div>
                            <div id="imagePreview${scenarioId}" class="mb-3" style="display: none;">
                                <img id="previewImg${scenarioId}" src="" alt="Preview" 
                                     style="max-width: 100%; max-height: 200px;">
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="upload-btn-${scenarioId}"
                                onclick="uploadP12ImageFromModal(${scenarioId}, '${scenarioName}')">
                            <i class="fas fa-upload"></i> Upload Image
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById(`uploadModal${scenarioId}`);
    if (existingModal) {
        existingModal.remove();
    }

    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Setup file preview
    const fileInput = document.getElementById(`imageFile${scenarioId}`);
    fileInput.addEventListener('change', function() {
        previewImage(this, `previewImg${scenarioId}`, `imagePreview${scenarioId}`);
    });

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById(`uploadModal${scenarioId}`));
    modal.show();
}

// Function to upload from modal
function uploadP12ImageFromModal(scenarioId, scenarioName) {
    const fileInput = document.getElementById(`imageFile${scenarioId}`);
    uploadP12Image(scenarioId, fileInput, scenarioName);
}

// Function to preview selected image
function previewImage(input, previewImgId, previewContainerId) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById(previewImgId).src = e.target.result;
            document.getElementById(previewContainerId).style.display = 'block';
        };
        reader.readAsDataURL(input.files[0]);
    }
}

// Global function to show image modal
function showImageModal(imageUrl, title) {
    document.getElementById('imageModalTitle').textContent = title;
    document.getElementById('imageModalImg').src = imageUrl;
    const modal = new bootstrap.Modal(document.getElementById('imageModal'));
    modal.show();
}

// Function to delete P12 scenario image
function deleteP12Image(scenarioId, scenarioName) {
    if (!confirm(`Delete the image for "${scenarioName}"? This action cannot be undone.`)) {
        return;
    }

    const csrfToken = document.querySelector('meta[name=csrf-token]')?.content ||
                     document.querySelector('input[name=csrf_token]')?.value;

    fetch(`/admin/p12-scenarios/delete-image/${scenarioId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload(); // Refresh to show updated state
        } else {
            alert('Error deleting image: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        alert('Error deleting image: ' + error.message);
    });
}

// Function to update image preview in the UI (alternative to page reload)
function updateImagePreview(scenarioId, imageUrl, thumbnailUrl) {
    // Update the image preview in the scenario list
    const imageContainer = document.querySelector(`#scenario-${scenarioId} .image-preview`);
    if (imageContainer) {
        imageContainer.innerHTML = `
            <img src="${thumbnailUrl || imageUrl}" 
                 alt="Scenario ${scenarioId} Preview"
                 class="scenario-image-preview"
                 onclick="showImageModal('${imageUrl}', 'Scenario ${scenarioId}')">
            <div class="image-badge has-image">
                <i class="fas fa-check"></i>
            </div>
        `;
    }

    // Update action buttons
    const actionContainer = document.querySelector(`#scenario-${scenarioId} .image-actions`);
    if (actionContainer) {
        actionContainer.innerHTML = `
            <button class="btn btn-sm btn-outline-primary" 
                    onclick="showImageUploadDialog(${scenarioId}, 'Scenario ${scenarioId}')"
                    title="Replace Image">
                <i class="fas fa-edit fa-xs"></i>
            </button>
            <button class="btn btn-sm btn-outline-danger ms-1" 
                    onclick="deleteP12Image(${scenarioId}, 'Scenario ${scenarioId}')"
                    title="Delete Image">
                <i class="fas fa-trash fa-xs"></i>
            </button>
        `;
    }
}

// Bulk upload function for P12 scenarios
function uploadBulkP12Images() {
    const fileInput = document.getElementById('bulkP12Files');
    if (!fileInput.files || fileInput.files.length === 0) {
        alert('Please select images to upload');
        return;
    }

    const formData = new FormData();

    // Add all selected files
    Array.from(fileInput.files).forEach(file => {
        formData.append('images', file);
    });

    formData.append('naming_pattern', 'p12_scenario');
    formData.append('overwrite_existing', 'true');

    const csrfToken = document.querySelector('meta[name=csrf-token]')?.content ||
                     document.querySelector('input[name=csrf_token]')?.value;

    // Show loading state
    const uploadBtn = document.getElementById('bulkUploadBtn');
    const originalText = uploadBtn.innerHTML;
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
    uploadBtn.disabled = true;

    fetch('/images/bulk-upload/p12_scenario', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`Successfully uploaded ${data.uploaded_count} images!`);
            location.reload();
        } else {
            alert('Error uploading images: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        alert('Error uploading images: ' + error.message);
    })
    .finally(() => {
        uploadBtn.innerHTML = originalText;
        uploadBtn.disabled = false;
    });
}

// Initialize event listeners when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Add CSRF token to meta tag if not already present
    if (!document.querySelector('meta[name=csrf-token]')) {
        const csrfInput = document.querySelector('input[name=csrf_token]');
        if (csrfInput) {
            const metaTag = document.createElement('meta');
            metaTag.name = 'csrf-token';
            metaTag.content = csrfInput.value;
            document.head.appendChild(metaTag);
        }
    }
});