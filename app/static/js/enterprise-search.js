/**
 * ========================================================================
 * ENTERPRISE SEARCH & FILTER UTILITIES
 * Global JavaScript for Fortune 500 Enterprise Applications
 * ========================================================================
 *
 * Provides reusable search, filter, and sorting functionality across
 * all administration forms and data tables.
 *
 * File: app/static/js/enterprise-search.js
 * ========================================================================
 */

// Global namespace for enterprise search functionality
window.EnterpriseSearch = (function() {
    'use strict';

    // Configuration defaults
    const DEFAULT_CONFIG = {
        searchDelay: 500,           // Debounce delay in milliseconds
        minSearchLength: 3,         // Minimum characters before auto-search
        autoSubmit: true,           // Auto-submit on search input
        sortIndicatorClass: 'fas fa-sort',
        sortAscClass: 'fas fa-sort-up',
        sortDescClass: 'fas fa-sort-down'
    };

    // Internal state management
    let activeInstances = new Map();
    let searchTimeouts = new Map();

    /**
     * Initialize search functionality for a form
     * @param {Object} options - Configuration options
     * @param {string} options.formId - ID of the search form
     * @param {string} options.searchInputId - ID of the search input field
     * @param {string} options.clearButtonId - ID of the clear search button (optional)
     * @param {Function} options.onSearch - Custom search handler (optional)
     * @param {Function} options.onClear - Custom clear handler (optional)
     * @param {Object} options.config - Override default configuration
     */
    function initializeSearch(options = {}) {
        const config = { ...DEFAULT_CONFIG, ...options.config };
        const instanceId = options.formId || 'default';

        // Validate required elements
        const form = document.getElementById(options.formId);
        const searchInput = document.getElementById(options.searchInputId);

        if (!form || !searchInput) {
            console.error('EnterpriseSearch: Required form or search input not found', {
                formId: options.formId,
                searchInputId: options.searchInputId
            });
            return false;
        }

        // Create instance object
        const instance = {
            form,
            searchInput,
            config,
            options,
            clearButton: options.clearButtonId ? document.getElementById(options.clearButtonId) : null
        };

        // Setup search input event listeners
        setupSearchInput(instance, instanceId);

        // Setup clear button if provided
        if (instance.clearButton) {
            setupClearButton(instance);
        }

        // Store instance for cleanup
        activeInstances.set(instanceId, instance);

        console.log(`✅ EnterpriseSearch initialized for: ${instanceId}`);
        return instance;
    }

    /**
     * Setup search input with debounced auto-submit
     */
    function setupSearchInput(instance, instanceId) {
        const { searchInput, form, config, options } = instance;

        // Clear any existing timeout for this instance
        if (searchTimeouts.has(instanceId)) {
            clearTimeout(searchTimeouts.get(instanceId));
        }

        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.trim();

            // Clear existing timeout
            if (searchTimeouts.has(instanceId)) {
                clearTimeout(searchTimeouts.get(instanceId));
            }

            // Custom search handler
            if (options.onSearch && typeof options.onSearch === 'function') {
                const timeout = setTimeout(() => {
                    options.onSearch(searchTerm, e, instance);
                }, config.searchDelay);
                searchTimeouts.set(instanceId, timeout);
                return;
            }

            // Default auto-submit behavior
            if (config.autoSubmit) {
                const timeout = setTimeout(() => {
                    // Only submit if empty or meets minimum length
                    if (searchTerm.length === 0 || searchTerm.length >= config.minSearchLength) {
                        console.log(`🔍 Auto-submitting search: "${searchTerm}"`);
                        form.submit();
                    }
                }, config.searchDelay);

                searchTimeouts.set(instanceId, timeout);
            }
        });

        // Handle Enter key
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();

                // Clear timeout and submit immediately
                if (searchTimeouts.has(instanceId)) {
                    clearTimeout(searchTimeouts.get(instanceId));
                    searchTimeouts.delete(instanceId);
                }

                if (options.onSearch && typeof options.onSearch === 'function') {
                    options.onSearch(e.target.value.trim(), e, instance);
                } else {
                    form.submit();
                }
            }
        });
    }

    /**
     * Setup clear button functionality
     */
    function setupClearButton(instance) {
        const { clearButton, searchInput, form, options } = instance;

        clearButton.addEventListener('click', function(e) {
            e.preventDefault();

            // Clear search input
            searchInput.value = '';
            searchInput.focus();

            // Custom clear handler
            if (options.onClear && typeof options.onClear === 'function') {
                options.onClear(e, instance);
                return;
            }

            // Default clear behavior - submit form to clear filters
            console.log('🧹 Clearing search filters');
            form.submit();
        });
    }

    /**
     * Initialize sortable table headers
     * @param {Object} options - Configuration options
     * @param {string} options.tableId - ID of the table
     * @param {string} options.sortableClass - Class name for sortable headers (default: 'sortable')
     * @param {Function} options.onSort - Custom sort handler (optional)
     */
    function initializeSorting(options = {}) {
        const table = document.getElementById(options.tableId);
        const sortableClass = options.sortableClass || 'sortable';

        if (!table) {
            console.error('EnterpriseSearch: Table not found', options.tableId);
            return false;
        }

        const sortableHeaders = table.querySelectorAll(`.${sortableClass}`);

        sortableHeaders.forEach(header => {
            header.style.cursor = 'pointer';
            header.setAttribute('role', 'columnheader');
            header.setAttribute('tabindex', '0');

            // Add click handler
            header.addEventListener('click', function(e) {
                handleSort(this, options);
            });

            // Add keyboard support
            header.addEventListener('keypress', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSort(this, options);
                }
            });
        });

        console.log(`✅ EnterpriseSearch sorting initialized for table: ${options.tableId}`);
        return true;
    }

    /**
     * Handle sort functionality
     */
    function handleSort(header, options) {
        if (header.classList.contains('sorting')) {
            return; // Prevent multiple rapid clicks
        }

        const sortField = header.getAttribute('data-sort');
        if (!sortField) {
            console.warn('EnterpriseSearch: No data-sort attribute found');
            return;
        }

        // Add loading state
        header.classList.add('sorting');

        // Custom sort handler
        if (options.onSort && typeof options.onSort === 'function') {
            options.onSort(sortField, header, options);
            header.classList.remove('sorting');
            return;
        }

        // Default URL-based sorting
        const currentUrl = new URL(window.location);
        const params = currentUrl.searchParams;

        const currentSort = params.get('sort');
        const currentOrder = params.get('order');

        // Determine new sort order
        let newOrder = 'asc';
        if (currentSort === sortField && currentOrder === 'asc') {
            newOrder = 'desc';
        }

        // Update URL parameters
        params.set('sort', sortField);
        params.set('order', newOrder);
        params.set('page', '1'); // Reset to first page

        // Update sort indicators
        updateSortIndicators(header, newOrder);

        // Navigate to sorted URL
        window.location.href = currentUrl.toString();
    }

    /**
     * Update visual sort indicators
     */
    function updateSortIndicators(activeHeader, order) {
        const table = activeHeader.closest('table');
        if (!table) return;

        // Reset all sort indicators
        const allHeaders = table.querySelectorAll('.sortable .sort-icon');
        allHeaders.forEach(icon => {
            icon.className = DEFAULT_CONFIG.sortIndicatorClass + ' sort-icon';
        });

        // Update active header indicator
        const activeIcon = activeHeader.querySelector('.sort-icon');
        if (activeIcon) {
            activeIcon.className = (order === 'asc' ? DEFAULT_CONFIG.sortAscClass : DEFAULT_CONFIG.sortDescClass) + ' sort-icon';
        }
    }

    /**
     * Initialize pagination controls
     * @param {Object} options - Configuration options
     * @param {string} options.pageSizeSelectId - ID of the page size selector
     * @param {Function} options.onPageSizeChange - Custom handler (optional)
     */
    function initializePagination(options = {}) {
        const pageSizeSelect = document.getElementById(options.pageSizeSelectId);

        if (!pageSizeSelect) {
            console.warn('EnterpriseSearch: Page size selector not found', options.pageSizeSelectId);
            return false;
        }

        pageSizeSelect.addEventListener('change', function(e) {
            const newSize = e.target.value;

            // Custom handler
            if (options.onPageSizeChange && typeof options.onPageSizeChange === 'function') {
                options.onPageSizeChange(newSize, e);
                return;
            }

            // Default behavior
            changePageSize(newSize);
        });

        console.log(`✅ EnterpriseSearch pagination initialized`);
        return true;
    }

    /**
     * Change page size and refresh
     */
    function changePageSize(size) {
        const params = new URLSearchParams(window.location.search);
        params.set('per_page', size);
        params.set('page', '1'); // Reset to first page

        const newUrl = `${window.location.pathname}?${params.toString()}`;
        console.log(`📄 Changing page size to: ${size}`);
        window.location.href = newUrl;
    }

    /**
     * Initialize filter dropdown auto-submit
     * @param {Object} options - Configuration options
     * @param {Array} options.filterIds - Array of filter element IDs
     * @param {string} options.formId - Form to submit
     * @param {Function} options.onFilterChange - Custom handler (optional)
     */
    function initializeFilters(options = {}) {
        const form = document.getElementById(options.formId);
        const filterIds = options.filterIds || [];

        if (!form || filterIds.length === 0) {
            console.warn('EnterpriseSearch: Invalid filter configuration');
            return false;
        }

        filterIds.forEach(filterId => {
            const filterElement = document.getElementById(filterId);
            if (filterElement) {
                filterElement.addEventListener('change', function(e) {
                    // Custom handler
                    if (options.onFilterChange && typeof options.onFilterChange === 'function') {
                        options.onFilterChange(e.target.value, e.target.id, e);
                        return;
                    }

                    // Default behavior - submit form
                    console.log(`🔽 Filter changed: ${e.target.id} = ${e.target.value}`);
                    form.submit();
                });
            }
        });

        console.log(`✅ EnterpriseSearch filters initialized: ${filterIds.join(', ')}`);
        return true;
    }

    /**
     * Initialize complete search suite for a standard admin list page
     * @param {Object} options - Configuration options
     */
    function initializeStandardAdminList(options = {}) {
        const defaults = {
            formId: 'search-filter-form',
            searchInputId: 'search',
            clearButtonId: 'search-clear',
            tableId: 'data-table',
            pageSizeSelectId: 'page-size',
            filterIds: ['role_filter', 'status_filter', 'verified_filter']
        };

        const config = { ...defaults, ...options };

        console.log('🚀 Initializing standard admin list search suite...');

        // Initialize all components
        const searchResult = initializeSearch({
            formId: config.formId,
            searchInputId: config.searchInputId,
            clearButtonId: config.clearButtonId
        });

        const sortResult = initializeSorting({
            tableId: config.tableId
        });

        const paginationResult = initializePagination({
            pageSizeSelectId: config.pageSizeSelectId
        });

        const filterResult = initializeFilters({
            formId: config.formId,
            filterIds: config.filterIds
        });

        const success = searchResult && sortResult && paginationResult && filterResult;

        if (success) {
            console.log('✅ Standard admin list search suite initialized successfully');
        } else {
            console.warn('⚠️ Some components failed to initialize');
        }

        return success;
    }

    /**
     * Cleanup function to remove event listeners and clear timeouts
     */
    function cleanup(instanceId = null) {
        if (instanceId) {
            // Cleanup specific instance
            if (searchTimeouts.has(instanceId)) {
                clearTimeout(searchTimeouts.get(instanceId));
                searchTimeouts.delete(instanceId);
            }
            activeInstances.delete(instanceId);
        } else {
            // Cleanup all instances
            searchTimeouts.forEach(timeout => clearTimeout(timeout));
            searchTimeouts.clear();
            activeInstances.clear();
        }
    }

    /**
     * Utility function to clear all search and filter values
     */
    function clearAllFilters(formId) {
        const form = document.getElementById(formId);
        if (!form) return false;

        // Clear text inputs
        const textInputs = form.querySelectorAll('input[type="text"], input[type="search"]');
        textInputs.forEach(input => input.value = '');

        // Reset select elements
        const selects = form.querySelectorAll('select');
        selects.forEach(select => select.selectedIndex = 0);

        // Submit form
        form.submit();
        return true;
    }

    // Public API
    return {
        // Main initialization functions
        initializeSearch,
        initializeSorting,
        initializePagination,
        initializeFilters,
        initializeStandardAdminList,

        // Utility functions
        changePageSize,
        clearAllFilters,
        cleanup,

        // Configuration
        DEFAULT_CONFIG,

        // Version info
        version: '1.0.0'
    };

})();

/**
 * ========================================================================
 * BACKWARD COMPATIBILITY & GLOBAL FUNCTIONS
 * ========================================================================
 * These functions maintain compatibility with existing templates
 */

// Global helper functions for backward compatibility
window.clearSearch = function() {
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.value = '';
        const form = searchInput.closest('form');
        if (form) {
            form.submit();
        }
    }
};

window.changePageSize = function(size) {
    EnterpriseSearch.changePageSize(size);
};

// Auto-initialize on DOM ready for standard admin pages
document.addEventListener('DOMContentLoaded', function() {
    // Auto-detect and initialize if standard elements are present
    const hasStandardElements = document.getElementById('search-filter-form') &&
                               document.getElementById('search');

    if (hasStandardElements) {
        console.log('🎯 Auto-initializing enterprise search for standard admin page...');
        EnterpriseSearch.initializeStandardAdminList();
    }
});

/**
 * ========================================================================
 * CONSOLE BRANDING
 * ========================================================================
 */
console.log(`
%c┌─────────────────────────────────────────────────────────────┐
│  🏢 ENTERPRISE SEARCH & FILTER UTILITIES                   │
│  Fortune 500 Grade JavaScript Framework                    │
│  Version: 1.0.0                                            │
└─────────────────────────────────────────────────────────────┘`,
'color: #0066cc; font-family: monospace; font-weight: bold;'
);