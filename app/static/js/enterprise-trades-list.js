/**
 * Enterprise Trading Operations JavaScript
 * Handles trade list functionality, dropdowns, charts, and delete operations
 */

console.log('🚀 Loading enterprise trades script...');

// ============================================================================
// MAIN TOGGLE FUNCTIONALITY
// ============================================================================

function toggleTradeDetails(tradeId) {
    console.log('🔧 Toggling trade details for ID:', tradeId);

    const detailsRow = document.getElementById(`details-${tradeId}`);
    const chevron = document.getElementById(`chevron-${tradeId}`);

    if (!detailsRow) {
        console.error('❌ Details row not found for trade ID:', tradeId);
        return;
    }

    const isVisible = detailsRow.style.display !== 'none';
    console.log('Currently visible:', isVisible);

    if (isVisible) {
        // Hide details
        detailsRow.style.display = 'none';
        if (chevron) {
            chevron.classList.remove('fa-chevron-down');
            chevron.classList.add('fa-chevron-right');
        }
        console.log('✅ Collapsed trade details');
    } else {
        // Show details
        detailsRow.style.display = '';
        if (chevron) {
            chevron.classList.remove('fa-chevron-right');
            chevron.classList.add('fa-chevron-down');
        }
        console.log('✅ Expanded trade details');

        // Initialize radar chart when details are shown
        setTimeout(() => {
            initializeRadarChart(tradeId);
        }, 100);
    }
}

// ============================================================================
// DELETE FUNCTIONALITY WITH CUSTOM MODALS
// ============================================================================

function confirmSingleDelete(tradeId, date, instrument, direction) {
    if (typeof showCustomConfirmation === 'function') {
        showCustomConfirmation({
            title: 'Confirm Trade Removal',
            message: `Remove trade configuration: ${date} - ${instrument} (${direction})?<br><br>This operational data will be permanently removed from the system.`,
            confirmText: 'Remove Configuration',
            cancelText: 'Cancel',
            confirmClass: 'btn-danger',
            icon: 'exclamation-triangle',
            onConfirm: function() {
                executeTradeDelete(tradeId);
            }
        });
    } else {
        // Fallback to browser confirm
        const message = `Remove trade: ${date} - ${instrument} (${direction})?\n\nThis action cannot be undone.`;
        if (confirm(message)) {
            executeTradeDelete(tradeId);
        }
    }
}

function executeTradeDelete(tradeId) {
    console.log('🗑️ Executing delete for trade ID:', tradeId);

    // Show loading notification
    if (typeof showInfo === 'function') {
        showInfo('Removing trade configuration...', 'Processing');
    }

    // Create form and submit
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/trades/${tradeId}/delete`;
    form.style.display = 'none';

    // Add CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    if (csrfToken) {
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrf_token';
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);
    }

    // Add custom modal flag
    const customModalInput = document.createElement('input');
    customModalInput.type = 'hidden';
    customModalInput.name = 'custom_modal_delete';
    customModalInput.value = 'true';
    form.appendChild(customModalInput);

    document.body.appendChild(form);
    form.submit();
}

// ============================================================================
// SORTING FUNCTIONALITY
// ============================================================================

function sortTable(field) {
    console.log('🔄 Sorting by field:', field);
    const currentUrl = new URL(window.location);
    const currentSort = currentUrl.searchParams.get('sort');
    const currentOrder = currentUrl.searchParams.get('order') || 'asc';

    let newOrder = 'asc';
    if (currentSort === field && currentOrder === 'asc') {
        newOrder = 'desc';
    }

    currentUrl.searchParams.set('sort', field);
    currentUrl.searchParams.set('order', newOrder);
    currentUrl.searchParams.set('page', '1');

    window.location.href = currentUrl.toString();
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function updateUrlAndRedirect(params) {
    const url = new URL(window.location);
    Object.keys(params).forEach(key => {
        url.searchParams.set(key, params[key]);
    });
    window.location.href = url.toString();
}

function changePageSize(newSize) {
    updateUrlAndRedirect({
        per_page: newSize,
        page: 1
    });
}

// ============================================================================
// RADAR CHART FUNCTIONALITY
// ============================================================================

function initializeRadarChart(tradeId) {
    const canvas = document.getElementById(`radarChart-${tradeId}`);
    if (!canvas || canvas.hasAttribute('data-chart-initialized')) {
        return;
    }

    console.log('📊 Initializing radar chart for trade:', tradeId);

    try {
        const ratings = extractTradeRatings(tradeId);
        if (ratings && Object.keys(ratings).length > 0) {
            renderRadarChart(canvas, ratings);
            canvas.setAttribute('data-chart-initialized', 'true');
        } else {
            console.log('📊 No ratings found for trade:', tradeId);
            renderEmptyRadarChart(canvas);
        }
    } catch (error) {
        console.error('❌ Chart initialization error:', error);
        renderEmptyRadarChart(canvas);
    }
}

function extractTradeRatings(tradeId) {
    const detailsRow = document.getElementById(`details-${tradeId}`);
    if (!detailsRow) return null;

    const ratings = {};
    const ratingItems = detailsRow.querySelectorAll('[data-rating-category]');

    ratingItems.forEach(item => {
        const category = item.getAttribute('data-rating-category');
        const value = parseInt(item.getAttribute('data-rating-value')) || 0;
        if (category && value >= 0) {
            ratings[category] = value;
        }
    });

    return Object.keys(ratings).length > 0 ? ratings : null;
}

function renderRadarChart(canvas, ratings) {
    const ctx = canvas.getContext('2d');
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) - 25;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const categories = Object.keys(ratings);
    const values = Object.values(ratings);
    const maxValue = 5;

    if (categories.length === 0) {
        renderEmptyRadarChart(canvas);
        return;
    }

    // Chart colors - matching the dark theme
    const gridColor = '#444';
    const axisColor = '#666';
    const dataColor = '#0d6efd';
    const fillColor = 'rgba(13, 110, 253, 0.2)';

    // Draw grid circles
    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 1;

    for (let i = 1; i <= maxValue; i++) {
        const gridRadius = (radius * i) / maxValue;
        ctx.beginPath();
        ctx.arc(centerX, centerY, gridRadius, 0, 2 * Math.PI);
        ctx.stroke();
    }

    // Draw grid lines and labels
    const angleStep = (2 * Math.PI) / categories.length;
    const labels = {
        'preparation': 'Prep',
        'rules': 'Rules',
        'management': 'Mgmt',
        'target': 'Target',
        'entry': 'Entry'
    };

    categories.forEach((category, index) => {
        const angle = index * angleStep - Math.PI / 2;
        const x = centerX + Math.cos(angle) * radius;
        const y = centerY + Math.sin(angle) * radius;

        // Grid line
        ctx.strokeStyle = axisColor;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(x, y);
        ctx.stroke();

        // Label
        ctx.fillStyle = '#aaa';
        ctx.font = '10px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        const labelX = centerX + Math.cos(angle) * (radius + 15);
        const labelY = centerY + Math.sin(angle) * (radius + 15);
        const labelText = labels[category] || category.substring(0, 5);

        ctx.fillText(labelText, labelX, labelY);
    });

    // Draw data polygon
    if (values.length > 0) {
        const points = values.map((value, index) => {
            const angle = index * angleStep - Math.PI / 2;
            const distance = (radius * value) / maxValue;
            return {
                x: centerX + Math.cos(angle) * distance,
                y: centerY + Math.sin(angle) * distance
            };
        });

        // Fill area
        ctx.fillStyle = fillColor;
        ctx.beginPath();
        points.forEach((point, i) => {
            if (i === 0) ctx.moveTo(point.x, point.y);
            else ctx.lineTo(point.x, point.y);
        });
        ctx.closePath();
        ctx.fill();

        // Draw outline
        ctx.strokeStyle = dataColor;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw data points
        ctx.fillStyle = dataColor;
        points.forEach(point => {
            ctx.beginPath();
            ctx.arc(point.x, point.y, 3, 0, 2 * Math.PI);
            ctx.fill();
        });
    }

    // Add center point
    ctx.fillStyle = '#666';
    ctx.beginPath();
    ctx.arc(centerX, centerY, 2, 0, 2 * Math.PI);
    ctx.fill();
}

function renderEmptyRadarChart(canvas) {
    const ctx = canvas.getContext('2d');
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw "No Ratings" message
    ctx.fillStyle = '#666';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('No Ratings', centerX, centerY);
}

// ============================================================================
// WIN/LOSS CHART FOR KPI
// ============================================================================

function initializeWinLossChart() {
    const canvas = document.getElementById('winLossChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) - 2;

    // Get data from the template
    const kpiCard = canvas.closest('.kpi-card');
    const kpiText = kpiCard?.querySelector('.kpi-value small')?.textContent;

    if (!kpiText) return;

    const matches = kpiText.match(/W: (\d+) \| L: (\d+) \| BE: (\d+)/);

    if (matches) {
        const wins = parseInt(matches[1]);
        const losses = parseInt(matches[2]);
        const breakeven = parseInt(matches[3]);
        const total = wins + losses + breakeven;

        if (total > 0) {
            const colors = ['#28a745', '#dc3545', '#ffc107']; // Green, Red, Yellow
            const data = [wins, losses, breakeven];

            let currentAngle = -Math.PI / 2;

            data.forEach((value, index) => {
                if (value > 0) {
                    const sliceAngle = (value / total) * 2 * Math.PI;

                    ctx.beginPath();
                    ctx.moveTo(centerX, centerY);
                    ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
                    ctx.closePath();
                    ctx.fillStyle = colors[index];
                    ctx.fill();

                    currentAngle += sliceAngle;
                }
            });
        }
    }
}

// ============================================================================
// EVENT LISTENERS SETUP
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Setting up enterprise trades event listeners...');

    // Initialize win/loss chart
    initializeWinLossChart();

    // Setup page size dropdown
    const pageSizeDropdown = document.getElementById('pageSizeDropdown');
    if (pageSizeDropdown) {
        pageSizeDropdown.addEventListener('change', function() {
            changePageSize(this.value);
        });
    }

    // Setup delete button handlers
    document.addEventListener('click', function(e) {
        // Handle delete button clicks
        if (e.target.closest('[data-trade-id]') && e.target.closest('.fa-trash-alt')) {
            e.preventDefault();
            e.stopPropagation();

            const button = e.target.closest('[data-trade-id]');
            const tradeId = button.getAttribute('data-trade-id');
            const date = button.getAttribute('data-trade-date');
            const instrument = button.getAttribute('data-trade-instrument');
            const direction = button.getAttribute('data-trade-direction');

            confirmSingleDelete(tradeId, date, instrument, direction);
            return;
        }

        // Handle chevron clicks directly
        if (e.target.classList.contains('chevron-icon')) {
            e.preventDefault();
            e.stopPropagation();

            const tradeId = e.target.id.replace('chevron-', '');
            if (tradeId) {
                toggleTradeDetails(tradeId);
            }
            return;
        }

        // Handle trade row clicks (but not buttons)
        const tradeRow = e.target.closest('.trade-row');
        if (tradeRow && !e.target.closest('.btn-group') && !e.target.closest('.btn')) {
            e.preventDefault();
            e.stopPropagation();

            const tradeId = tradeRow.getAttribute('data-trade-id');
            if (tradeId) {
                toggleTradeDetails(tradeId);
            }
            return;
        }

        // Handle sortable header clicks
        const sortable = e.target.closest('.sortable');
        if (sortable) {
            const field = sortable.getAttribute('data-sort');
            if (field) {
                sortTable(field);
            }
            return;
        }
    });

    console.log('✅ Event listeners setup complete');
});

// ============================================================================
// BULK OPERATIONS (PLACEHOLDER)
// ============================================================================

function executeBulkDelete() {
    console.log('🔧 Bulk delete function called - placeholder');
    if (typeof showWarning === 'function') {
        showWarning('Bulk delete functionality not yet implemented', 'Feature Unavailable');
    }
}

// ============================================================================
// EXPORT FUNCTIONS FOR GLOBAL ACCESS
// ============================================================================

// Make functions globally available
window.toggleTradeDetails = toggleTradeDetails;
window.confirmSingleDelete = confirmSingleDelete;
window.sortTable = sortTable;
window.changePageSize = changePageSize;
window.executeBulkDelete = executeBulkDelete;

console.log('✅ Enterprise trades script loaded successfully');



// ============================================================================
// UPDATED EVENT LISTENERS
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 DOM Content Loaded - setting up charts...');
    initializeAllCharts();

    // Setup other event listeners
    setupEventListeners();
});

// If DOMContentLoaded already fired
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        console.log('🎯 DOM Content Loaded (late) - setting up charts...');
        initializeAllCharts();
    });
} else {
    console.log('🎯 DOM already loaded - setting up charts immediately...');
    initializeAllCharts();
}
