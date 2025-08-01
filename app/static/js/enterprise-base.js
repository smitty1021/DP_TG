/**
 * Enterprise Base Template JavaScript
 * Core functionality for the base.html template
 * Part of Fortune 500 Enterprise Framework
 */

// Global flag to prevent duplicate flash message processing
let flashMessagesProcessed = false;

// Global unsaved changes management system
let globalBeforeUnloadHandler = null;
let beforeUnloadBypass = false;

// Enterprise notification system initialization
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 Enterprise base initialization starting...');

    // Initialize Flask flash message system (with deduplication)
    initializeFlashMessages();

    // Initialize sidebar functionality
    initializeSidebar();

    // Initialize modal focus management
    initializeModalFocusManagement();

    // Initialize mobile menu toggle
    initializeMobileMenu();

    // Initialize media preview system
    initializeMediaPreviewSystem();

    // Initialize global unsaved changes system
    initializeGlobalUnsavedChangesSystem();

    console.log('✅ Enterprise base initialization complete');
});

/**
 * Initialize Flask flash messages with enterprise notifications
 * Includes deduplication to prevent double processing
 */
function initializeFlashMessages() {
    // DEDUPLICATION: Prevent multiple processing of the same messages
    if (flashMessagesProcessed) {
        console.log('⚠️ Flash messages already processed, skipping duplicate call');
        return;
    }

    const flaskMessages = document.querySelectorAll('#flask-flash-data > div');
    console.log(`🔔 Processing ${flaskMessages.length} flash messages...`);

    if (flaskMessages.length === 0) {
        console.log('ℹ️ No flash messages to process');
        return;
    }

    flaskMessages.forEach((msg, index) => {
        let category = msg.dataset.category;
        const message = msg.dataset.message;

        if (category === 'error') {
            category = 'danger';
        }

        if (message) {
            console.log(`📨 Processing flash message ${index + 1}: [${category}] ${message.substring(0, 50)}...`);
            showNotification(message, category);

            // Mark the message as processed by adding a class
            msg.classList.add('flash-processed');
        }
    });

    // Set the global flag to prevent duplicate processing
    flashMessagesProcessed = true;
    console.log('✅ Flash message processing completed and locked');

    // Clear the flash data container after processing to prevent any future conflicts
    setTimeout(() => {
        const flashContainer = document.getElementById('flask-flash-data');
        if (flashContainer) {
            flashContainer.innerHTML = '';
            console.log('🧹 Flash data container cleared');
        }
    }, 100);
}

/**
 * Initialize enterprise sidebar functionality
 */
function initializeSidebar() {
    const sidebar = document.querySelector('.sidebar');

    // Function to close all sidebar submenus
    function closeSidebarSubmenus() {
        document.querySelectorAll('.sidebar-nav .has-submenu').forEach(function(item) {
            item.classList.remove('open');
        });
    }

    // Initialize sidebar with all dropdowns collapsed on page load
    function initializeSidebarState() {
        document.querySelectorAll('.sidebar-nav .has-submenu').forEach(function(item) {
            item.classList.remove('open');
        });
    }

    // Initialize sidebar state on page load
    initializeSidebarState();

    // Sidebar dropdown toggle functionality
    document.querySelectorAll('.sidebar-nav .has-submenu > a').forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const parentLi = this.parentElement;

            // Toggle current submenu
            parentLi.classList.toggle('open');

            // Close other submenus
            document.querySelectorAll('.sidebar-nav .has-submenu').forEach(function(item) {
                if (item !== parentLi) {
                    item.classList.remove('open');
                }
            });
        });
    });

    // Close sidebar when clicking outside (mobile)
    document.addEventListener('click', function(e) {
        if (sidebar && !sidebar.contains(e.target)) {
            closeSidebarSubmenus();
        }
    });
}

/**
 * Initialize mobile menu functionality
 */
function initializeMobileMenu() {
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.querySelector('.sidebar');

    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
    }

    // Close mobile sidebar when clicking outside
    document.addEventListener('click', function(e) {
        const menuToggle = document.getElementById('menuToggle');

        if (sidebar && menuToggle &&
            !sidebar.contains(e.target) &&
            !menuToggle.contains(e.target) &&
            sidebar.classList.contains('show')) {
            sidebar.classList.remove('show');
            // Close submenus as well
            document.querySelectorAll('.sidebar-nav .has-submenu').forEach(function(item) {
                item.classList.remove('open');
            });
        }
    });
}

/**
 * Initialize enterprise modal focus management system
 */
function initializeModalFocusManagement() {
    document.querySelectorAll('.modal').forEach(function(modal) {
        modal.addEventListener('hide.bs.modal', function() {
            const focusedElement = modal.querySelector(':focus');
            if (focusedElement) {
                focusedElement.blur();
            }
        });

        modal.addEventListener('hidden.bs.modal', function() {
            document.body.focus();
        });
    });
}

/**
 * Initialize media preview system
 */
function initializeMediaPreviewSystem() {
    // Functions are already defined globally in the template
    // This ensures they're available after DOM loads
}

/**
 * Enterprise media preview system functions
 */
function showImagePreview(imageUrl, title) {
    document.getElementById('imagePreviewTitle').textContent = title;
    document.getElementById('imagePreviewImg').src = imageUrl;
    document.getElementById('imagePreviewModal').show();
}

function downloadCurrentImage() {
    const imageElement = document.getElementById('imageModalImg');
    const imageUrl = imageElement ? imageElement.src : null;
    
    if (imageUrl && imageUrl !== '') {
        // Create a temporary link element to trigger download
        const link = document.createElement('a');
        link.href = imageUrl;
        
        // Extract filename from title or use default
        const titleElement = document.getElementById('imageModalTitle');
        const title = titleElement ? titleElement.textContent : 'enterprise-media-asset';
        const filename = title.replace(/[^a-z0-9]/gi, '_').toLowerCase() + '.png';
        
        link.download = filename;
        link.target = '_blank';
        
        // Trigger download
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        console.log('Download triggered for:', filename);
    } else {
        console.warn('No image available for download');
        if (typeof showErrorMessage === 'function') {
            showErrorMessage('No image available for download');
        } else {
            alert('No image available for download');
        }
    }
}

/**
 * Initialize global unsaved changes management system
 * Provides centralized control over beforeunload events
 */
function initializeGlobalUnsavedChangesSystem() {
    console.log('🔧 Initializing global unsaved changes system...');
    
    // No global beforeunload handler - individual pages handle unsaved changes via click interception
    console.log('✅ Global unsaved changes system initialized');
}

/**
 * Globally disable beforeunload prompts
 * Call this before programmatic navigation to prevent double prompts
 */
window.disableBeforeUnloadPrompts = function() {
    console.log('🔒 Disabling beforeunload prompts globally');
    beforeUnloadBypass = true;
    
    // Automatically re-enable after a short delay to prevent permanent bypass
    setTimeout(function() {
        beforeUnloadBypass = false;
        console.log('🔓 Re-enabled beforeunload prompts');
    }, 1000);
};

/**
 * Force navigation without any beforeunload prompts
 * Safer alternative to direct window.location changes
 */
window.safeNavigate = function(url) {
    console.log('🧭 Safe navigation to:', url);
    window.disableBeforeUnloadPrompts();
    
    // Small delay to ensure bypass is active
    setTimeout(function() {
        window.location.href = url;
    }, 50);
};