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

// Add this to your notifications.js file



function showVerificationRequired(userEmail = '') {
    // Remove any existing verification notification
    const existing = document.getElementById('verification-notification');
    if (existing) {
        existing.remove();
    }

    // Create a completely independent notification
    const notification = document.createElement('div');
    notification.id = 'verification-notification';
    notification.style.cssText = `
        position: fixed;
        top: 1rem;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        width: calc(100vw - 2rem);
        max-width: 700px;
        min-width: 400px;
        background-color: #fff3cd;
        color: #664d03;
        border: 1px solid #ffecb5;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
        font-size: 14px;
        opacity: 0;
        transition: all 0.3s ease-out;
        pointer-events: auto;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
    `;

    // Create the content
    notification.innerHTML = `
        <div style="display: flex; align-items: center; flex: 1; min-width: 0;">
            <i class="fas fa-exclamation-circle" style="color: #664d03; margin-right: 8px; flex-shrink: 0;"></i>
            <span style="flex: 1; min-width: 0;">Email verification required. Check your inbox or</span>
        </div>
        <button type="button" id="resendVerificationBtn" style="
            background-color: #0d6efd;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 13px;
            cursor: pointer;
            flex-shrink: 0;
            white-space: nowrap;
            transition: background-color 0.2s ease;
        ">
            <i class="fas fa-paper-plane" style="margin-right: 4px;"></i>Resend Email
        </button>
        <button type="button" id="closeVerificationBtn" style="
            background: none;
            border: none;
            color: #664d03;
            font-size: 16px;
            cursor: pointer;
            padding: 0;
            margin-left: 8px;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        ">×</button>
    `;

    // Add to body (not to the container)
    document.body.appendChild(notification);

    // Add hover effect for button
    const resendBtn = notification.querySelector('#resendVerificationBtn');
    resendBtn.addEventListener('mouseenter', () => {
        resendBtn.style.backgroundColor = '#0b5ed7';
    });
    resendBtn.addEventListener('mouseleave', () => {
        resendBtn.style.backgroundColor = '#0d6efd';
    });

    // Animate in
    requestAnimationFrame(() => {
        notification.style.opacity = '1';
    });

    // Add click handler for resend button
    resendBtn.addEventListener('click', function() {
        // Show loading state
        this.innerHTML = '<i class="fas fa-spinner fa-spin" style="margin-right: 4px;"></i>Sending...';
        this.disabled = true;
        this.style.backgroundColor = '#6c757d';
        this.style.cursor = 'not-allowed';

        // Redirect to resend page
        setTimeout(() => {
            window.location.href = '/auth/resend_verification';
        }, 500);
    });

    // Add click handler for close button
    const closeBtn = notification.querySelector('#closeVerificationBtn');
    closeBtn.addEventListener('click', () => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(-50%) translateY(-10px)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    });

    // Auto-remove after 12 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(-50%) translateY(-10px)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    }, 12000);
}

// Make sure this function is available globally
window.showVerificationRequired = showVerificationRequired;