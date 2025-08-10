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
    // Remove any existing verification notifications
    const existing = document.querySelectorAll('.verification-notification');
    existing.forEach(el => el.remove());

    // Create the notification element
    const notification = document.createElement('div');
    notification.className = 'verification-notification';
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        border: 1px solid #f0ad4e;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15);
        z-index: 10000;
        max-width: 500px;
        width: 90%;
        display: flex;
        align-items: center;
        gap: 12px;
        opacity: 0;
        transform: translateX(-50%) translateY(-10px);
        transition: all 0.3s ease;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    `;

    notification.innerHTML = `
        <div style="
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, #f39c12, #e67e22);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        ">
            <i class="fas fa-envelope" style="color: white; font-size: 14px;"></i>
        </div>
        <div style="flex: 1; color: #664d03; line-height: 1.4;">
            <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px;">
                Email Verification Required
            </div>
            <div style="font-size: 13px;">
                Please verify your email address to access the trading platform.
                ${userEmail ? `Check your inbox at <strong>${userEmail}</strong> or` : 'Check your inbox or'} 
                click below to resend the verification email.
            </div>
        </div>
        <button type="button" id="resendVerificationBtn" style="
            background-color: #0d6efd;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            flex-shrink: 0;
            white-space: nowrap;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(13,110,253,0.2);
        ">
            <i class="fas fa-paper-plane" style="margin-right: 6px;"></i>Resend Email
        </button>
        <button type="button" id="closeVerificationBtn" style="
            background: none;
            border: none;
            color: #664d03;
            font-size: 18px;
            cursor: pointer;
            padding: 4px;
            margin-left: 8px;
            width: 28px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            border-radius: 4px;
            transition: background-color 0.2s ease;
        ">×</button>
    `;

    // Add to body
    document.body.appendChild(notification);

    // Add hover effects
    const resendBtn = notification.querySelector('#resendVerificationBtn');
    const closeBtn = notification.querySelector('#closeVerificationBtn');

    resendBtn.addEventListener('mouseenter', () => {
        resendBtn.style.backgroundColor = '#0b5ed7';
        resendBtn.style.transform = 'translateY(-1px)';
        resendBtn.style.boxShadow = '0 4px 8px rgba(13,110,253,0.3)';
    });
    resendBtn.addEventListener('mouseleave', () => {
        resendBtn.style.backgroundColor = '#0d6efd';
        resendBtn.style.transform = 'translateY(0)';
        resendBtn.style.boxShadow = '0 2px 4px rgba(13,110,253,0.2)';
    });

    closeBtn.addEventListener('mouseenter', () => {
        closeBtn.style.backgroundColor = 'rgba(102, 77, 3, 0.1)';
    });
    closeBtn.addEventListener('mouseleave', () => {
        closeBtn.style.backgroundColor = 'transparent';
    });

    // Animate in
    requestAnimationFrame(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(-50%) translateY(0)';
    });

    // Add click handler for resend button
    resendBtn.addEventListener('click', function() {
        // Show loading state
        this.innerHTML = '<i class="fas fa-spinner fa-spin" style="margin-right: 6px;"></i>Sending...';
        this.disabled = true;
        this.style.backgroundColor = '#6c757d';
        this.style.cursor = 'not-allowed';
        this.style.transform = 'translateY(0)';

        // Redirect to resend page after short delay
        setTimeout(() => {
            window.location.href = '/auth/resend_verification';
        }, 800);
    });

    // Add click handler for close button
    closeBtn.addEventListener('click', () => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(-50%) translateY(-10px)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    });

    // Auto-remove after 15 seconds
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
    }, 15000);
}

// Make sure this function is available globally
window.showVerificationRequired = showVerificationRequired;

// Progress indicator for long-running operations
function showProgressIndicator(title = 'Generating Report', message = 'Please standby while we process your request...', showProgressBar = true) {
    // Remove any existing progress indicators
    const existing = document.querySelectorAll('.progress-indicator-modal');
    existing.forEach(el => el.remove());

    // Create the modal backdrop
    const backdrop = document.createElement('div');
    backdrop.className = 'progress-indicator-modal';
    backdrop.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.6);
        z-index: 10050;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;

    // Create the modal content
    const modal = document.createElement('div');
    modal.style.cssText = `
        background: white;
        border-radius: 12px;
        padding: 2rem;
        min-width: 400px;
        max-width: 500px;
        text-align: center;
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        transform: scale(0.9);
        transition: transform 0.3s ease;
    `;

    // Build modal content
    let progressBarHTML = '';
    if (showProgressBar) {
        progressBarHTML = `
            <div style="margin: 1.5rem 0;">
                <div style="background: #f8f9fa; border-radius: 10px; height: 8px; overflow: hidden; margin-bottom: 0.5rem;">
                    <div id="progress-bar" style="
                        width: 0%;
                        height: 100%;
                        background: linear-gradient(90deg, #0d6efd, #0056b3);
                        border-radius: 10px;
                        transition: width 0.3s ease;
                        animation: progress-shimmer 2s infinite;
                    "></div>
                </div>
                <div id="progress-text" style="font-size: 0.875rem; color: #6c757d; font-weight: 500;">
                    Initializing...
                </div>
            </div>
        `;
    }

    modal.innerHTML = `
        <div style="margin-bottom: 1rem;">
            <div style="
                width: 60px;
                height: 60px;
                margin: 0 auto 1rem;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #0d6efd;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            "></div>
            <h4 style="margin: 0 0 0.5rem 0; color: #212529; font-weight: 600;">${title}</h4>
            <p style="margin: 0; color: #6c757d; font-size: 0.95rem;">${message}</p>
        </div>
        ${progressBarHTML}
        <div style="margin-top: 1.5rem;">
            <button type="button" id="cancel-operation" class="btn btn-outline-secondary btn-sm" style="display: none;">
                <i class="fas fa-times me-1"></i>Cancel
            </button>
        </div>
    `;

    // Add spinner animation styles
    const style = document.createElement('style');
    style.textContent = `
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        @keyframes progress-shimmer {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
    `;
    document.head.appendChild(style);

    backdrop.appendChild(modal);
    document.body.appendChild(backdrop);

    // Animate in
    requestAnimationFrame(() => {
        backdrop.style.opacity = '1';
        modal.style.transform = 'scale(1)';
    });

    // Return control object for updating progress
    return {
        updateProgress: function(percent, text) {
            const progressBar = document.getElementById('progress-bar');
            const progressText = document.getElementById('progress-text');
            if (progressBar) progressBar.style.width = `${percent}%`;
            if (progressText) progressText.textContent = text;
        },
        updateMessage: function(newMessage) {
            const messageEl = modal.querySelector('p');
            if (messageEl) messageEl.textContent = newMessage;
        },
        hide: function() {
            backdrop.style.opacity = '0';
            modal.style.transform = 'scale(0.9)';
            setTimeout(() => {
                if (backdrop.parentNode) {
                    backdrop.remove();
                }
                // Clean up styles
                if (style.parentNode) {
                    style.remove();
                }
            }, 300);
        },
        element: backdrop
    };
}

// Make functions globally available
window.showProgressIndicator = showProgressIndicator;