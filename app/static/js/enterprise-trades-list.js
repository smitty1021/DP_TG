/**
 * Clean Enterprise Trading Operations JavaScript
 * Simple, working implementation focused on dropdown functionality
 */

console.log('🚀 Loading clean enterprise trades script...');

// Simple dropdown toggle function
function toggleTradeDetails(tradeId) {
    console.log('🔧 Attempting to toggle trade details for ID:', tradeId);

    const detailsRow = document.getElementById(`details-${tradeId}`);
    const chevron = document.getElementById(`chevron-${tradeId}`);

    console.log('Details row found:', detailsRow);
    console.log('Chevron found:', chevron);

    if (detailsRow) {
        const isHidden = detailsRow.classList.contains('d-none');
        console.log('Currently hidden:', isHidden);

        if (isHidden) {
            detailsRow.classList.remove('d-none');
            if (chevron) {
                chevron.classList.remove('fa-chevron-right');
                chevron.classList.add('fa-chevron-down');
            }
            console.log('✅ Expanded trade details');
        } else {
            detailsRow.classList.add('d-none');
            if (chevron) {
                chevron.classList.remove('fa-chevron-down');
                chevron.classList.add('fa-chevron-right');
            }
            console.log('✅ Collapsed trade details');
        }
    } else {
        console.error('❌ Details row not found for trade ID:', tradeId);
    }
}

// Simple delete confirmation
function confirmSingleDelete(tradeId, date, instrument, direction) {
    const message = `Remove trade: ${date} - ${instrument} (${direction})?\n\nThis action cannot be undone.`;
    if (confirm(message)) {
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

        document.body.appendChild(form);
        form.submit();
    }
}

// Simple sorting function
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

// Setup event listeners when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Setting up enterprise trades event listeners...');

    // Setup trade row click handlers
    document.addEventListener('click', function(e) {
        console.log('👆 Click detected on:', e.target);

        // Handle chevron clicks directly
        if (e.target.classList.contains('chevron-icon')) {
            console.log('🎯 Chevron clicked directly');
            e.preventDefault();
            e.stopPropagation();

            const tradeId = e.target.id.replace('chevron-', '');
            console.log('📊 Trade ID from chevron:', tradeId);

            if (tradeId) {
                toggleTradeDetails(tradeId);
            }
            return;
        }

        // Handle trade row clicks (but not buttons)
        const tradeRow = e.target.closest('.trade-row');
        if (tradeRow && !e.target.closest('.btn-group') && !e.target.closest('.btn')) {
            console.log('📋 Trade row clicked');
            e.preventDefault();
            e.stopPropagation();

            const tradeId = tradeRow.getAttribute('data-trade-id');
            console.log('📊 Trade ID from row:', tradeId);

            if (tradeId) {
                toggleTradeDetails(tradeId);
            }
        }

        // Handle sortable header clicks
        const sortable = e.target.closest('.sortable');
        if (sortable) {
            console.log('📊 Sortable header clicked');
            const field = sortable.getAttribute('data-sort');
            if (field) {
                sortTable(field);
            }
        }
    });

    console.log('✅ Event listeners setup complete');
});

// Placeholder functions to prevent errors
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

function extractTradeRatings(tradeId) {
    return null; // Placeholder
}

function initializeRadarChart(tradeId, ratings = null) {
    console.log('📊 Radar chart initialization skipped for trade:', tradeId);
}

console.log('✅ Clean enterprise trades script loaded successfully');