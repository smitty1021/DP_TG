// enterprise-trades-list.js
// Enterprise Trade List Application for Fortune 500 Trading Journal

console.log('🚀 Loading enterprise trade list functions...');

// Enhanced CSRF token management
window.getCsrfToken = function() {
    // Method 1: From meta tag
    const metaToken = document.querySelector('meta[name="csrf-token"]');
    if (metaToken && metaToken.content) {
        return metaToken.content;
    }

    // Method 2: From window object
    if (window.csrf_token) {
        return window.csrf_token;
    }

    // Method 3: From any form on the page
    const formWithToken = document.querySelector('input[name="csrf_token"]');
    if (formWithToken && formWithToken.value) {
        return formWithToken.value;
    }

    console.error('No CSRF token found anywhere on the page');
    return null;
};

// Global state management
const TradeListApp = {
    isLoading: false,
    customConfirmModal: null,
    visibleCharts: new Set(),
    sortCache: new Map(),

    // Initialize the application
    init() {
        console.log('🎯 Initializing enterprise trade list...');
        try {
            this.setupModals();
            this.setupEventListeners();
            this.setupKeyboardNavigation();
            this.initializeVisibleCharts();
            console.log('✅ Trade list initialization complete');
        } catch (error) {
            console.error('❌ Initialization error:', error);
            this.showError('Failed to initialize trade list');
        }
    },

    // Setup Bootstrap modals with error handling
    setupModals() {
        const modalElement = document.getElementById('customConfirmModal');
        if (modalElement && typeof bootstrap !== 'undefined') {
            this.customConfirmModal = new bootstrap.Modal(modalElement);
            console.log('✅ Custom confirm modal initialized');
        } else {
            console.warn('⚠️ Bootstrap modal not available');
        }
    },

    // Setup event listeners with delegation for better performance
    setupEventListeners() {
        // Sortable headers with debouncing
        document.addEventListener('click', (e) => {
            const sortable = e.target.closest('.sortable');
            if (sortable && !sortable.classList.contains('sorting')) {
                const field = sortable.getAttribute('data-sort');
                if (field) {
                    this.debounce(() => this.sortTable(field), 200)();
                }
            }
        });

        // Trade row clicks with event delegation
        document.addEventListener('click', (e) => {
            const tradeRow = e.target.closest('.trade-row');
            if (tradeRow && !e.target.closest('.action-grid')) {
                const tradeId = tradeRow.getAttribute('data-trade-id');
                if (tradeId) {
                    this.toggleTradeDetails(tradeId);
                }
            }
        });

        // Window resize handler for responsive charts
        window.addEventListener('resize', this.debounce(() => {
            this.refreshVisibleCharts();
        }, 250));
    },

    // Enhanced keyboard navigation
    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName.toLowerCase() === 'input' ||
                e.target.tagName.toLowerCase() === 'textarea') {
                return; // Don't interfere with form inputs
            }

            switch(e.key) {
                case 'j':
                case 'ArrowDown':
                    e.preventDefault();
                    this.navigateToNextTrade();
                    break;
                case 'k':
                case 'ArrowUp':
                    e.preventDefault();
                    this.navigateToPrevTrade();
                    break;
                case ' ':
                    e.preventDefault();
                    this.toggleCurrentTradeDetails();
                    break;
                case 'f':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.openFilterModal();
                    }
                    break;
            }
        });
    },

    // Enhanced URL handling with loading states
    updateUrlAndRedirect(params) {
        if (this.isLoading) return;
        try {
            this.showLoading();
            const currentUrl = new URL(window.location);
            Object.keys(params).forEach(key => {
                const value = params[key];
                if (value !== null && value !== undefined && value !== '') {
                    currentUrl.searchParams.set(key, value);
                } else {
                    currentUrl.searchParams.delete(key);
                }
            });
            const newUrl = currentUrl.pathname + (currentUrl.search || '');
            console.log('🔄 Redirecting to:', newUrl);
            setTimeout(() => {
                window.location.href = newUrl;
            }, 100);
        } catch (error) {
            console.error('❌ URL update error:', error);
            this.hideLoading();
            this.showError('Navigation failed');
        }
    },

    // Enhanced sorting with visual feedback
    sortTable(field) {
        if (this.isLoading) return;
        try {
            console.log('🔄 Sorting by:', field);
            const sortButton = document.querySelector(`[data-sort="${field}"]`);
            if (sortButton) {
                sortButton.classList.add('sorting');
            }
            const params = new URLSearchParams(window.location.search);
            const currentSort = params.get('sort');
            const currentOrder = params.get('order');
            let newOrder = 'asc';
            if (currentSort === field && currentOrder === 'asc') {
                newOrder = 'desc';
            }
            this.updateUrlAndRedirect({
                sort: field,
                order: newOrder,
                page: 1
            });
        } catch (error) {
            console.error('❌ Sort error:', error);
            this.showError('Sorting failed');
            document.querySelectorAll('.sorting').forEach(btn => {
                btn.classList.remove('sorting');
            });
        }
    },

    // Enhanced page size change with validation
    changePageSize(newSize) {
        const validSizes = [25, 50, 100, 250];
        const size = parseInt(newSize);
        if (!validSizes.includes(size)) {
            console.warn('⚠️ Invalid page size:', newSize);
            return;
        }
        console.log('📄 Changing page size to:', size);
        this.updateUrlAndRedirect({
            per_page: size,
            page: 1
        });
    },

    // Keyboard navigation helpers
    navigateToNextTrade() {
        const rows = document.querySelectorAll('.trade-row');
        const current = document.querySelector('.trade-row:focus') || rows[0];
        const currentIndex = Array.from(rows).indexOf(current);
        const next = rows[currentIndex + 1];
        if (next) {
            next.focus();
            next.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    },

    navigateToPrevTrade() {
        const rows = document.querySelectorAll('.trade-row');
        const current = document.querySelector('.trade-row:focus') || rows[0];
        const currentIndex = Array.from(rows).indexOf(current);
        const prev = rows[currentIndex - 1];
        if (prev) {
            prev.focus();
            prev.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    },

    toggleCurrentTradeDetails() {
        const focusedRow = document.querySelector('.trade-row:focus');
        if (focusedRow) {
            const tradeId = focusedRow.getAttribute('data-trade-id');
            if (tradeId) {
                this.toggleTradeDetails(tradeId);
            }
        }
    },

    openFilterModal() {
        const filterModal = document.getElementById('filterModal');
        if (filterModal && typeof bootstrap !== 'undefined') {
            const modal = new bootstrap.Modal(filterModal);
            modal.show();
        }
    },

    // Enhanced trade details toggle with improved animations
    toggleTradeDetails(tradeId) {
        const detailsRow = document.getElementById(`details-${tradeId}`);
        const chevron = document.getElementById(`chevron-${tradeId}`);
        const tradeRow = document.querySelector(`[data-trade-id="${tradeId}"]`);

        if (!detailsRow || !chevron) {
            console.error(`Missing elements for trade ${tradeId}`);
            return;
        }

        const isCurrentlyVisible = detailsRow.style.display === 'table-row';

        if (isCurrentlyVisible) {
            // Hide details with animation
            detailsRow.style.display = 'none';
            chevron.classList.remove('fa-chevron-down');
            chevron.classList.add('fa-chevron-right');
            tradeRow?.classList.remove('expanded');
            this.visibleCharts.delete(tradeId);
        } else {
            // Show details with animation
            detailsRow.style.display = 'table-row';
            chevron.classList.remove('fa-chevron-right');
            chevron.classList.add('fa-chevron-down');
            tradeRow?.classList.add('expanded');
            // Initialize radar chart with improved timing
            setTimeout(() => {
                this.initializeRadarChart(tradeId);
            }, 50);
        }
    },

    // Enhanced radar chart with better error handling
    initializeRadarChart(tradeId) {
        try {
            const canvas = document.getElementById(`radarChart-${tradeId}`);
            if (!canvas) {
                console.warn(`Radar chart canvas not found for trade ${tradeId}`);
                return;
            }
            const ratings = this.extractTradeRatings(tradeId);
            this.renderRadarChart(canvas, ratings);
            this.visibleCharts.add(tradeId);
        } catch (error) {
            console.error(`❌ Radar chart error for trade ${tradeId}:`, error);
        }
    },

    // Enhanced rating extraction with multiple fallback methods
    extractTradeRatings(tradeId) {
        const detailsRow = document.getElementById(`details-${tradeId}`);
        if (!detailsRow) {
            console.warn(`Details row not found for trade ${tradeId}`);
            return [0, 0, 0, 0, 0];
        }

        const ratings = [0, 0, 0, 0, 0];
        const ratingCategories = ['preparation', 'rules_adherence', 'risk_management', 'target_achievement', 'entry_execution'];

        ratingCategories.forEach((category, index) => {
            // Method 1: Data attributes
            const ratingElement = detailsRow.querySelector(`[data-rating-category="${category}"]`);
            if (ratingElement?.dataset.ratingValue) {
                const rating = parseInt(ratingElement.dataset.ratingValue);
                if (this.isValidRating(rating)) {
                    ratings[index] = rating;
                    return;
                }
            }

            // Method 2: Rating dots
            const ratingRow = detailsRow.querySelector(`.operation-item:nth-child(${index + 1})`);
            if (ratingRow) {
                const filledDots = ratingRow.querySelectorAll('.rating-dot[class*="filled-"]');
                if (filledDots.length > 0) {
                    const lastDot = filledDots[filledDots.length - 1];
                    const filledClass = Array.from(lastDot.classList)
                        .find(cls => cls.startsWith('filled-'));
                    if (filledClass) {
                        const rating = parseInt(filledClass.split('-')[1]);
                        if (this.isValidRating(rating)) {
                            ratings[index] = rating;
                        }
                    }
                }
            }
        });

        return ratings;
    },

    initializeVisibleCharts() {
        document.querySelectorAll('[id^="radarChart-"]').forEach(canvas => {
            const tradeId = canvas.id.split('-')[1];
            const detailsRow = document.getElementById(`details-${tradeId}`);
            if (detailsRow && detailsRow.style.display !== 'none') {
                this.initializeRadarChart(tradeId);
            }
        });
    },

    refreshVisibleCharts() {
        this.visibleCharts.forEach(tradeId => {
            this.initializeRadarChart(tradeId);
        });
    },

    // Enhanced radar chart rendering with better performance
    renderRadarChart(canvas, ratings) {
        const ctx = canvas.getContext('2d');
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = 85;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
        const colors = {
            grid: isDark ? '#6b7280' : '#e5e7eb',
            text: isDark ? '#d1d5db' : '#374151',
            data: '#3b82f6',
            fill: 'rgba(59, 130, 246, 0.15)'
        };

        this.drawRadarGrid(ctx, centerX, centerY, radius, colors.grid);
        this.drawRadarLabels(ctx, centerX, centerY, radius, colors.text);

        if (ratings.some(r => r > 0)) {
            this.drawRadarData(ctx, centerX, centerY, radius, ratings, colors);
        } else {
            this.drawNoDataMessage(ctx, centerX, centerY, colors.text);
        }
    },

    // Helper methods for radar chart
    drawRadarGrid(ctx, centerX, centerY, radius, color) {
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;

        // Concentric circles
        for (let i = 1; i <= 5; i++) {
            ctx.beginPath();
            ctx.arc(centerX, centerY, (radius * i) / 5, 0, 2 * Math.PI);
            ctx.stroke();
        }

        // Spokes
        const angleStep = (2 * Math.PI) / 5;
        for (let i = 0; i < 5; i++) {
            const angle = i * angleStep - Math.PI / 2;
            const x = centerX + Math.cos(angle) * radius;
            const y = centerY + Math.sin(angle) * radius;
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(x, y);
            ctx.stroke();
        }
    },

    drawRadarLabels(ctx, centerX, centerY, radius, color) {
        const labels = ['Prep', 'Rules', 'Risk', 'Target', 'Entry'];
        const angleStep = (2 * Math.PI) / 5;

        ctx.fillStyle = color;
        ctx.font = '12px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        labels.forEach((label, i) => {
            const angle = i * angleStep - Math.PI / 2;
            const labelDistance = radius + 25;
            const labelX = centerX + Math.cos(angle) * labelDistance;
            const labelY = centerY + Math.sin(angle) * labelDistance;
            ctx.fillText(label, labelX, labelY);
        });
    },

    drawRadarData(ctx, centerX, centerY, radius, ratings, colors) {
        const angleStep = (2 * Math.PI) / 5;
        const points = [];

        // Calculate points
        ratings.forEach((rating, i) => {
            const angle = i * angleStep - Math.PI / 2;
            const distance = (Math.max(0, rating) / 5) * radius;
            points.push({
                x: centerX + Math.cos(angle) * distance,
                y: centerY + Math.sin(angle) * distance
            });
        });

        // Fill area
        ctx.fillStyle = colors.fill;
        ctx.beginPath();
        points.forEach((point, i) => {
            if (i === 0) ctx.moveTo(point.x, point.y);
            else ctx.lineTo(point.x, point.y);
        });
        ctx.closePath();
        ctx.fill();

        // Draw outline
        ctx.strokeStyle = colors.data;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw points
        ctx.fillStyle = colors.data;
        points.forEach(point => {
            ctx.beginPath();
            ctx.arc(point.x, point.y, 4, 0, 2 * Math.PI);
            ctx.fill();
        });
    },

    drawNoDataMessage(ctx, centerX, centerY, color) {
        ctx.fillStyle = color;
        ctx.font = '12px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('No Ratings', centerX, centerY);
    },

    // Enhanced delete confirmation with proper CSRF token handling
    confirmSingleDelete(tradeId, date, instrument, direction) {
        console.log('🔍 Starting delete confirmation for trade:', tradeId);

        const csrfToken = window.getCsrfToken();
        if (!csrfToken) {
            console.error('❌ No CSRF token available');
            if (typeof showError === 'function') {
                showError('Security token not found. Please refresh the page and try again.', 'Security Error');
            } else {
                alert('Security token not found. Please refresh the page and try again.');
            }
            return;
        }

        console.log('✅ CSRF token found:', csrfToken.substring(0, 20) + '...');

        if (typeof showCustomConfirmation === 'function') {
            console.log('📋 Using custom confirmation modal');
            showCustomConfirmation({
                title: 'Confirm Configuration Removal',
                message: `
                    <div class="alert alert-warning d-flex align-items-center" role="alert">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <div>
                            Are you sure you want to permanently remove this trade configuration?
                        </div>
                    </div>
                    <div class="enterprise-module">
                        <div class="module-header">
                            <span class="module-title">Trade Configuration Details</span>
                        </div>
                        <div class="module-content">
                            <div class="operation-list">
                                <div class="operation-item">
                                    <span class="operation-name">Date:</span>
                                    <span class="operation-status">${date}</span>
                                </div>
                                <div class="operation-item">
                                    <span class="operation-name">Instrument:</span>
                                    <span class="operation-status">${instrument}</span>
                                </div>
                                <div class="operation-item">
                                    <span class="operation-name">Direction:</span>
                                    <span class="operation-status">${direction}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="mt-3">
                        <small class="text-muted">
                            <i class="fas fa-info-circle me-1"></i>
                            This operational change cannot be undone and will permanently remove all trade data including entries, exits, and analysis notes.
                        </small>
                    </div>
                `,
                confirmText: 'Remove Configuration',
                cancelText: 'Cancel Operation',
                confirmClass: 'btn-danger',
                icon: 'exclamation-triangle',
                onConfirm: () => {
                    console.log('🗑️ User confirmed deletion, executing...');
                    this.executeTradeDelete(tradeId, csrfToken);
                }
            });
        } else {
            console.log('⚠️ Custom modal not available, using browser confirm');
            const confirmMessage = `Remove Trade Configuration: ${date} - ${instrument} (${direction})\n\nThis operational change cannot be undone. Continue?`;
            if (confirm(confirmMessage)) {
                console.log('✅ User confirmed deletion via browser dialog');
                this.executeTradeDelete(tradeId, csrfToken);
            } else {
                console.log('❌ User cancelled deletion');
            }
        }
    },

    // Separate method to execute the actual deletion
    executeTradeDelete(tradeId, csrfToken) {
        console.log('🚀 Executing trade deletion:', tradeId);
        try {
            this.showLoading();
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/trades/${tradeId}/delete`;
            form.style.display = 'none';

            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrf_token';
            csrfInput.value = csrfToken;
            form.appendChild(csrfInput);

            document.body.appendChild(form);
            console.log('📤 Submitting delete form with token:', csrfToken.substring(0, 10) + '...');
            form.submit();
        } catch (error) {
            console.error('❌ Error executing deletion:', error);
            this.hideLoading();
            this.showError('Failed to remove trade configuration. Please try again.');
        }
    },

    // Utility methods
    isValidRating(rating) {
        return !isNaN(rating) && rating >= 0 && rating <= 5;
    },

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    showLoading() {
        this.isLoading = true;
        let overlay = document.querySelector('.loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.innerHTML = '<div class="loading-spinner"></div>';
            document.body.appendChild(overlay);
        }
        overlay.classList.add('show');
    },

    hideLoading() {
        this.isLoading = false;
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            overlay.classList.remove('show');
        }
    },

    showError(message) {
        console.error('Error:', message);
        if (typeof showError === 'function') {
            showError(message, 'Configuration Error');
        } else if (typeof window.showNotification === 'function') {
            window.showNotification(message, 'danger', 'Error');
        } else {
            alert('Error: ' + message);
        }
    }
};

// Global functions for backward compatibility
function updateUrlAndRedirect(params) {
    TradeListApp.updateUrlAndRedirect(params);
}

function changePageSize(newSize) {
    TradeListApp.changePageSize(newSize);
}

function sortTable(field) {
    TradeListApp.sortTable(field);
}

function toggleTradeDetails(tradeId) {
    TradeListApp.toggleTradeDetails(tradeId);
}

function confirmSingleDelete(tradeId, date, instrument, direction) {
    TradeListApp.confirmSingleDelete(tradeId, date, instrument, direction);
}

function extractTradeRatings(tradeId) {
    return TradeListApp.extractTradeRatings(tradeId);
}

function initializeRadarChart(tradeId, ratings = null) {
    if (ratings) {
        const canvas = document.getElementById(`radarChart-${tradeId}`);
        if (canvas) {
            TradeListApp.renderRadarChart(canvas, ratings);
        }
    } else {
        TradeListApp.initializeRadarChart(tradeId);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    TradeListApp.init();
});

console.log('✅ Enterprise trade list template loaded with accessibility and performance improvements');