/**
 * Enterprise Base Template JavaScript
 * Core functionality for the base.html template
 * Part of Fortune 500 Enterprise Framework
 */

// Enterprise notification system initialization
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Flask flash message system
    initializeFlashMessages();

    // Initialize sidebar functionality
    initializeSidebar();

    // Initialize modal focus management
    initializeModalFocusManagement();

    // Initialize mobile menu toggle
    initializeMobileMenu();

    // Initialize media preview system
    initializeMediaPreviewSystem();
});

/**
 * Initialize Flask flash messages with enterprise notifications
 */
function initializeFlashMessages() {
    const flaskMessages = document.querySelectorAll('#flask-flash-data > div');
    flaskMessages.forEach(msg => {
        let category = msg.dataset.category;
        const message = msg.dataset.message;

        if (category === 'error') {
            category = 'danger';
        }

        if (message) {
            showNotification(message, category);
        }
    });
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
            const isOpen = parentLi.classList.contains('open');

            // Close all other submenus
            document.querySelectorAll('.sidebar-nav .has-submenu').forEach(function(item) {
                if (item !== parentLi) {
                    item.classList.remove('open');
                }
            });

            // Toggle current submenu
            if (!isOpen) {
                parentLi.classList.add('open');
            } else {
                parentLi.classList.remove('open');
            }
        });
    });

    // Enhanced sidebar dropdown management on navigation
    document.querySelectorAll('.sidebar-nav a[href]').forEach(function(link) {
        // Skip dropdown toggle links (they don't have actual hrefs)
        if (link.getAttribute('href') !== '#') {
            link.addEventListener('click', function() {
                // Close all dropdowns when navigating to a new page
                closeSidebarSubmenus();
            });
        }
    });

    // Close sidebar dropdowns when sidebar collapses to icon-only mode
    if (sidebar) {
        sidebar.addEventListener('mouseleave', function() {
            // Wait a short delay to ensure sidebar has collapsed
            setTimeout(function() {
                if (!sidebar.matches(':hover')) {
                    closeSidebarSubmenus();
                }
            }, 100);
        });
    }

    // Close all sidebar dropdowns when clicking outside sidebar
    document.addEventListener('click', function(e) {
        const isClickInsideSidebar = sidebar && sidebar.contains(e.target);

        if (!isClickInsideSidebar) {
            closeSidebarSubmenus();
        }
    });

    // Close dropdowns when sidebar loses focus
    document.addEventListener('focusin', function(e) {
        const isClickInsideSidebar = sidebar && sidebar.contains(e.target);

        if (!isClickInsideSidebar) {
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
    document.getElementById('imagePreviewCard').style.display = 'block';

    document.getElementById('imagePreviewCard').scrollIntoView({
        behavior: 'smooth',
        block: 'center'
    });
}

function closeImagePreview() {
    document.getElementById('imagePreviewCard').style.display = 'none';
}

function downloadCurrentImage() {
    const imageUrl = document.getElementById('imageModalImg').src;
    const title = document.getElementById('imageModalTitle').textContent;

    const filename = title.replace(/[^a-z0-9\s]/gi, '_').replace(/\s+/g, '_').toLowerCase() + '.png';

    try {
        const link = document.createElement('a');
        link.href = imageUrl;
        link.download = filename;
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Show success notification
        showSuccess('Media Asset Download Initiated');
    } catch (error) {
        console.error('Direct download failed:', error);

        fetch(imageUrl)
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);

                // Show success notification
                showSuccess('Media Asset Download Completed');
            })
            .catch(error => {
                console.error('Fetch download failed:', error);
                window.open(imageUrl, '_blank');

                // Show info notification
                showInfo('Media Asset Opened in New Tab');
            });
    }
}