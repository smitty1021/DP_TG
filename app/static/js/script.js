document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.querySelector('.sidebar');
    const menuToggle = document.getElementById('menuToggle');
    // NOTE: Theme handling and other logic can remain if you have it,
    // but the core sidebar logic is simplified below.

    // --- Sidebar Logic ---
    if (sidebar && menuToggle) {
        // Since the menuToggle button is now only visible on smaller screens,
        // we only need to handle the mobile overlay functionality.
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('mobile-open');
        });

        // Add back the logic to collapse submenus on mouse leave
        sidebar.addEventListener('mouseleave', function() {
            if (sidebar.classList.contains('desktop-icon-only')) {
                 const openSubmenus = sidebar.querySelectorAll('.submenu.open');
                 openSubmenus.forEach(submenu => {
                     submenu.classList.remove('open');
                     const parentLink = submenu.parentElement.querySelector('a');
                     if (parentLink) {
                        const arrowIcon = parentLink.querySelector('.arrow .fas');
                        if (arrowIcon) {
                            arrowIcon.classList.remove('fa-chevron-down');
                            arrowIcon.classList.add('fa-chevron-right');
                        }
                     }
                 });
            }
        });

        // --- Submenu Toggle ---
        const submenuToggles = document.querySelectorAll('.sidebar-nav .has-submenu > a');
        submenuToggles.forEach(toggle => {
            toggle.addEventListener('click', function(event) {
                event.preventDefault();
                const submenu = this.parentElement.querySelector('.submenu');
                const arrowIcon = this.querySelector('.arrow .fas');
                submenu.classList.toggle('open');
                if(arrowIcon) {
                    arrowIcon.classList.toggle('fa-chevron-right');
                    arrowIcon.classList.toggle('fa-chevron-down');
                }
            });
        });
    }

});