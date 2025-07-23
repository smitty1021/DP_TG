// Global notification function that mimics Flask's flash message system
function showNotification(message, category = 'success', title = null, duration = 4000) {
    // Find or create the flash message container
    let container = document.getElementById('dynamic-notification-container');

    if (!container) {
        container = document.createElement('div');
        container.id = 'dynamic-notification-container';
        // Also apply the same class for positioning
        container.className = 'flash-message-container';
        document.body.appendChild(container);
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${category} alert-dismissible fade show`;

    // FIXED: Use CSS transitions instead of conflicting animations
    notification.style.cssText = `
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border: none;
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.4s ease-out;
    `;

    // Build the notification content
    let iconClass = '';
    switch(category) {
        case 'success':
            iconClass = 'fas fa-check-circle';
            break;
        case 'danger':
        case 'error':
            iconClass = 'fas fa-exclamation-triangle';
            break;
        case 'warning':
            iconClass = 'fas fa-exclamation-circle';
            break;
        case 'info':
            iconClass = 'fas fa-info-circle';
            break;
        default:
            iconClass = 'fas fa-bell';
    }

    notification.innerHTML = `
        <i class="${iconClass} me-2"></i>
        ${title ? `<strong>${title}:</strong> ` : ''}${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    // Add to container (at the top, so new notifications appear above older ones)
    container.insertBefore(notification, container.firstChild);

    // FIXED: Use requestAnimationFrame for proper timing
    requestAnimationFrame(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateY(0)';
    });

    // Auto-remove after specified duration
    const removalTimeout = setTimeout(() => {
        if (notification.parentNode) {
            // FIXED: Single smooth exit animation
            notification.style.transition = 'all 0.3s ease-in';
            notification.style.opacity = '0';
            notification.style.transform = 'translateY(-20px)';

            // Remove from DOM after animation completes
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    }, duration);

    // Handle manual close button
    const closeButton = notification.querySelector('.btn-close');
    if (closeButton) {
        closeButton.addEventListener('click', () => {
            clearTimeout(removalTimeout);
            if (notification.parentNode) {
                notification.style.transition = 'all 0.2s ease-in';
                notification.style.opacity = '0';
                notification.style.transform = 'translateY(-10px)';

                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 200);
            }
        });
    }
}

// Convenience functions for different notification types
function showSuccess(message, title = 'Success') {
    showNotification(message, 'success', title);
}

function showError(message, title = 'Error') {
    showNotification(message, 'danger', title);
}

function showWarning(message, title = 'Warning') {
    showNotification(message, 'warning', title);
}

function showInfo(message, title = 'Info') {
    showNotification(message, 'info', title);
}

// Export functions if using modules (optional)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showNotification,
        showSuccess,
        showError,
        showWarning,
        showInfo
    };
}