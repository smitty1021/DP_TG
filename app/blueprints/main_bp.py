from flask import Blueprint, render_template, request, jsonify, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, desc, extract, and_, or_
from datetime import datetime, timedelta, date as py_date
from collections import defaultdict
import calendar
import statistics
import math
from ..models import Trade, DailyJournal, TradingModel
from sqlalchemy import asc, desc, text

from flask import jsonify
from sqlalchemy import func
from collections import defaultdict
import statistics
import math
from datetime import datetime, date as py_date
from functools import lru_cache
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload
from app.utils.discord_decorators import require_discord_permission, sync_discord_roles_if_needed
from app.utils import record_activity


# Define the blueprint
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@main_bp.route('/index')
@login_required
def index():
    """
    Renders the comprehensive Trading Analytics Center with enhanced Fortune 500 styling.
    Provides macro and micro level trading analytics for professional traders.
    """
    try:
        # Get all trades for the current user
        trades = Trade.query.filter_by(user_id=current_user.id).order_by(Trade.trade_date.asc()).all()

        # Calculate comprehensive trading statistics
        stats = calculate_comprehensive_trading_stats(trades)

        # Prepare calendar data with daily P&L and trade counts
        calendar_data = prepare_enhanced_calendar_data(trades)

        # Get paginated trades for the main table (default to first 100)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)

        trades_query = Trade.query.filter_by(user_id=current_user.id).order_by(
            desc(Trade.trade_date), desc(Trade.id)
        )

        # Get all trades for the frontend (we'll handle pagination there)
        all_trades = trades_query.all()

        # Convert trades to serializable format
        trades_data = []
        for trade in all_trades:
            trades_data.append({
                'id': trade.id,
                'trade_date': trade.trade_date.strftime('%Y-%m-%d') if trade.trade_date else None,
                'instrument': trade.instrument,  # Uses the property
                'trading_model': trade.trading_model.name if trade.trading_model else None,
                'direction': trade.direction,
                'total_contracts_entered': trade.total_contracts_entered or 0,
                'entry_price': float(trade.average_entry_price) if trade.average_entry_price else 0,
                'exit_price': float(trade.average_exit_price) if trade.average_exit_price else 0,
                'pnl': float(trade.pnl) if trade.pnl else 0,
                'time_in_trade': self.get_time_in_trade_minutes(trade),
                'entry_time': self.get_first_entry_time(trade),
                'exit_time': self.get_last_exit_time(trade),
                'how_closed': trade.how_closed
            })

        # Prepare enhanced chart data
        chart_data = prepare_comprehensive_chart_data(trades)

        # Calculate model performance analytics
        model_analytics = calculate_model_performance(trades)

        # Current date info for calendar
        today = py_date.today()
        current_month = today.strftime('%B %Y')
        current_month_num = today.month
        current_year = today.year
        today_str = today.strftime('%Y-%m-%d')

        return render_template('main/dashboard.html',
                               title="Trading Analytics Center",
                               stats=stats,
                               calendar_data=calendar_data,
                               recent_trades=trades_data,
                               chart_data=chart_data,
                               model_analytics=model_analytics,
                               current_month=current_month,
                               current_month_num=current_month_num,
                               current_year=current_year,
                               today_str=today_str)

    except Exception as e:
        # Fallback for any errors - show basic dashboard
        print(f"Dashboard error: {e}")
        return render_template('main/dashboard.html',
                               title="Trading Analytics Center",
                               stats=get_default_comprehensive_stats(),
                               calendar_data={},
                               recent_trades=[],
                               chart_data=get_default_chart_data(),
                               model_analytics={},
                               current_month=py_date.today().strftime('%B %Y'),
                               current_month_num=py_date.today().month,
                               current_year=py_date.today().year,
                               today_str=py_date.today().strftime('%Y-%m-%d'))




def get_time_in_trade_minutes(trade):
    """Helper function to get time in trade in minutes."""
    try:
        if not trade.entries.first() or not trade.exits.first():
            return None

        first_entry = trade.entries.order_by(text('entry_time ASC')).first()
        last_exit = trade.exits.order_by(text('exit_time DESC')).first()

        if not first_entry or not last_exit or not first_entry.entry_time or not last_exit.exit_time:
            return None

        entry_datetime = datetime.combine(trade.trade_date, first_entry.entry_time)
        exit_datetime = datetime.combine(trade.trade_date, last_exit.exit_time)
        duration = exit_datetime - entry_datetime
        return int(duration.total_seconds() / 60)

    except Exception as e:
        print(f"Error calculating time in trade: {e}")
        return None


def get_first_entry_time(trade):
    """Helper function to get first entry time as string."""
    try:
        if not trade.entries.first():
            return None

        first_entry = trade.entries.order_by(text('entry_time ASC')).first()
        if first_entry and first_entry.entry_time:
            return first_entry.entry_time.strftime('%H:%M')
        return None
    except Exception as e:
        print(f"Error getting first entry time: {e}")
        return None


def get_last_exit_time(trade):
    """Helper function to get last exit time as string."""
    try:
        if not trade.exits.first():
            return None

        last_exit = trade.exits.order_by(text('exit_time DESC')).first()
        if last_exit and last_exit.exit_time:
            return last_exit.exit_time.strftime('%H:%M')
        return None
    except Exception as e:
        print(f"Error getting last exit time: {e}")
        return None

    # Daily Analytics
    daily_data = calculate_daily_analytics(trades)

    # Model Analytics
    model_stats = calculate_model_expectancy(trades)

    result = {
        # Core Metrics
        'total_pnl': round(total_pnl, 2),
        'total_trades': total_trades,
        'winning_trades': win_count,
        'losing_trades': loss_count,
        'breakeven_trades': breakeven_count,

        # Performance Ratios
        'win_rate': round(win_rate, 1),
        'profit_factor': round(profit_factor, 2),
        'expectancy': round(expectancy, 2),
        'average_trade': round(average_trade, 2),
        'sqn': round(sqn, 1),

        # Win/Loss Analysis
        'gross_profit': round(gross_profit, 2),
        'gross_loss': round(gross_loss, 2),  # Already positive
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),  # Already positive

        # Daily Analytics
        'win_days': daily_data['win_days'],
        'loss_days': daily_data['loss_days'],
        'daily_win_rate': round(daily_data['daily_win_rate'], 1),
        'avg_wins_per_day': round(daily_data['avg_wins_per_day'], 1),
        'daily_expectancy': round(daily_data['daily_expectancy'], 2),

        # Model Performance
        'model_expectancies': model_stats['expectancies'],
        'best_model': model_stats['best_model'],
        'worst_model': model_stats['worst_model'],
    }

    print(f"DEBUG: Calculated stats: {result}")
    return result


def calculate_comprehensive_trading_stats(trades):
    """
    Calculate comprehensive trading statistics for the dashboard.
    Includes all metrics a professional trader would want to see.
    """
    if not trades:
        return get_default_comprehensive_stats()

    # Basic trade metrics
    total_trades = len(trades)
    trade_pnls = [float(trade.pnl) for trade in trades if trade.pnl is not None]

    print(f"DEBUG: Processing {total_trades} trades, {len(trade_pnls)} with P&L data")

    if not trade_pnls:
        return get_default_comprehensive_stats()

    # P&L Calculations
    total_pnl = sum(trade_pnls)
    winning_trades = [pnl for pnl in trade_pnls if pnl > 0]
    losing_trades = [pnl for pnl in trade_pnls if pnl < 0]
    breakeven_trades = [pnl for pnl in trade_pnls if pnl == 0]

    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    breakeven_count = len(breakeven_trades)

    # Core Statistics
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

    gross_profit = sum(winning_trades) if winning_trades else 0
    gross_loss = abs(sum(losing_trades)) if losing_trades else 0  # Make positive

    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (float('inf') if gross_profit > 0 else 0)

    average_trade = total_pnl / total_trades if total_trades > 0 else 0

    # Win/Loss Averages
    avg_win = statistics.mean(winning_trades) if winning_trades else 0
    avg_loss = abs(statistics.mean(losing_trades)) if losing_trades else 0  # Make positive

    # Expectancy Calculation
    expectancy = (win_rate / 100 * avg_win) - ((100 - win_rate) / 100 * avg_loss)

    # System Quality Number (SQN)
    if len(trade_pnls) > 1:
        std_dev = statistics.stdev(trade_pnls)
        sqn = (average_trade / std_dev) * math.sqrt(total_trades) if std_dev > 0 else 0
    else:
        sqn = 0

    # Daily Analytics
    daily_data = calculate_daily_analytics(trades)

    # Model Analytics
    model_stats = calculate_model_expectancy(trades)

    result = {
        # Core Metrics
        'total_pnl': round(total_pnl, 2),
        'total_trades': total_trades,
        'winning_trades': win_count,
        'losing_trades': loss_count,
        'breakeven_trades': breakeven_count,

        # Performance Ratios
        'win_rate': round(win_rate, 1),
        'profit_factor': round(profit_factor, 2),
        'expectancy': round(expectancy, 2),
        'average_trade': round(average_trade, 2),
        'sqn': round(sqn, 1),

        # Win/Loss Analysis
        'gross_profit': round(gross_profit, 2),
        'gross_loss': round(gross_loss, 2),  # Already positive
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),  # Already positive

        # Daily Analytics
        'win_days': daily_data['win_days'],
        'loss_days': daily_data['loss_days'],
        'daily_win_rate': round(daily_data['daily_win_rate'], 1),
        'avg_wins_per_day': round(daily_data['avg_wins_per_day'], 1),
        'daily_expectancy': round(daily_data['daily_expectancy'], 2),

        # Model Performance
        'model_expectancies': model_stats['expectancies'],
        'best_model': model_stats['best_model'],
        'worst_model': model_stats['worst_model'],
    }

    print(f"DEBUG: Calculated stats: {result}")
    return result


def calculate_daily_analytics(trades):
    """Calculate daily-level analytics for trading performance."""
    daily_data = defaultdict(lambda: {'pnl': 0, 'trades': 0, 'wins': 0, 'losses': 0})

    for trade in trades:
        if trade.trade_date and trade.pnl is not None:
            date_key = trade.trade_date.strftime('%Y-%m-%d')
            daily_data[date_key]['pnl'] += float(trade.pnl)
            daily_data[date_key]['trades'] += 1

            if float(trade.pnl) > 0:
                daily_data[date_key]['wins'] += 1
            elif float(trade.pnl) < 0:
                daily_data[date_key]['losses'] += 1

    # Calculate daily metrics
    win_days = sum(1 for day in daily_data.values() if day['pnl'] > 0)
    loss_days = sum(1 for day in daily_data.values() if day['pnl'] < 0)
    total_days = len(daily_data)

    daily_win_rate = (win_days / total_days * 100) if total_days > 0 else 0

    # Average wins per day
    total_wins = sum(day['wins'] for day in daily_data.values())
    avg_wins_per_day = total_wins / total_days if total_days > 0 else 0

    # Daily expectancy
    total_daily_pnl = sum(day['pnl'] for day in daily_data.values())
    daily_expectancy = total_daily_pnl / total_days if total_days > 0 else 0

    return {
        'win_days': win_days,
        'loss_days': loss_days,
        'total_days': total_days,
        'daily_win_rate': daily_win_rate,
        'avg_wins_per_day': avg_wins_per_day,
        'daily_expectancy': daily_expectancy
    }


def calculate_model_expectancy(trades):
    """Calculate expectancy and performance metrics per trading model."""
    model_data = defaultdict(lambda: {'trades': [], 'total_pnl': 0, 'count': 0})

    for trade in trades:
        # Get model name properly
        model_name = None
        if trade.trading_model:
            model_name = trade.trading_model.name
        else:
            model_name = 'Unknown'

        if trade.pnl is not None:
            pnl = float(trade.pnl)

            model_data[model_name]['trades'].append(pnl)
            model_data[model_name]['total_pnl'] += pnl
            model_data[model_name]['count'] += 1

    # Calculate expectancy per model
    expectancies = {}
    avg_pnls = {}

    for model, data in model_data.items():
        if data['count'] > 0:
            expectancies[model] = data['total_pnl'] / data['count']
            avg_pnls[model] = data['total_pnl'] / data['count']

    # Find best and worst performing models
    best_model = max(expectancies.items(), key=lambda x: x[1]) if expectancies else ('N/A', 0)
    worst_model = min(expectancies.items(), key=lambda x: x[1]) if expectancies else ('N/A', 0)

    return {
        'expectancies': expectancies,
        'avg_pnls': avg_pnls,
        'best_model': {'name': best_model[0], 'expectancy': best_model[1]},
        'worst_model': {'name': worst_model[0], 'expectancy': worst_model[1]}
    }


def prepare_enhanced_calendar_data(trades):
    """Prepare enhanced calendar data with daily PnL and trade counts for calendar display."""
    calendar_data = {}

    for trade in trades:
        if trade.trade_date and trade.pnl is not None:
            date_str = trade.trade_date.strftime('%Y-%m-%d')

            if date_str not in calendar_data:
                calendar_data[date_str] = {'pnl': 0, 'trades': 0}

            calendar_data[date_str]['pnl'] += float(trade.pnl)
            calendar_data[date_str]['trades'] += 1

    # Round PnL values for display
    for date_str in calendar_data:
        calendar_data[date_str]['pnl'] = round(calendar_data[date_str]['pnl'], 2)

    return calendar_data


def prepare_comprehensive_chart_data(trades):
    """Prepare comprehensive chart data for all dashboard visualizations."""
    if not trades:
        return get_default_chart_data()

    # Sort trades by date
    trades_sorted = sorted([t for t in trades if t.trade_date], key=lambda t: t.trade_date)

    # Equity curve calculation
    running_total = 0
    equity_curve = []
    equity_labels = []

    for trade in trades_sorted:
        if trade.pnl is not None:
            running_total += float(trade.pnl)
            equity_curve.append(round(running_total, 2))
            equity_labels.append(trade.trade_date.strftime('%m/%d'))

    # Daily PnL data (last 30 trading days)
    daily_data = defaultdict(float)
    for trade in trades_sorted:
        if trade.trade_date and trade.pnl is not None:
            date_str = trade.trade_date.strftime('%m/%d')
            daily_data[date_str] += float(trade.pnl)

    # Get last 20 days for daily chart
    daily_items = list(daily_data.items())[-20:] if len(daily_data) > 20 else list(daily_data.items())
    daily_labels = [item[0] for item in daily_items]
    daily_pnl = [round(item[1], 2) for item in daily_items]

    # Monthly PnL data
    monthly_data = defaultdict(float)
    for trade in trades_sorted:
        if trade.trade_date and trade.pnl is not None:
            month_key = trade.trade_date.strftime('%Y-%m')
            monthly_data[month_key] += float(trade.pnl)

    # Get last 12 months
    monthly_items = list(monthly_data.items())[-12:] if len(monthly_data) > 12 else list(monthly_data.items())
    monthly_labels = [datetime.strptime(item[0], '%Y-%m').strftime('%b %Y') for item in monthly_items]
    monthly_pnl = [round(item[1], 2) for item in monthly_items]

    return {
        # Equity curve
        'equity_labels': equity_labels,
        'equity_data': equity_curve,

        # Daily P&L
        'daily_labels': daily_labels,
        'daily_pnl': daily_pnl,

        # Monthly P&L
        'monthly_labels': monthly_labels,
        'monthly_pnl': monthly_pnl,

        # Additional metrics for charts
        'max_equity': max(equity_curve) if equity_curve else 0,
        'min_equity': min(equity_curve) if equity_curve else 0,
        'total_return': equity_curve[-1] if equity_curve else 0
    }


def calculate_model_performance(trades):
    """Calculate detailed performance analytics per trading model."""
    model_stats = defaultdict(lambda: {
        'trades': 0,
        'total_pnl': 0,
        'wins': 0,
        'losses': 0,
        'win_rate': 0,
        'avg_trade': 0,
        'expectancy': 0
    })

    for trade in trades:
        # Get model name properly
        model_name = None
        if trade.trading_model:
            model_name = trade.trading_model.name
        else:
            model_name = 'Unknown'

        if trade.pnl is not None:
            pnl = float(trade.pnl)

            model_stats[model_name]['trades'] += 1
            model_stats[model_name]['total_pnl'] += pnl

            if pnl > 0:
                model_stats[model_name]['wins'] += 1
            elif pnl < 0:
                model_stats[model_name]['losses'] += 1

    # Calculate derived metrics
    for model, stats in model_stats.items():
        if stats['trades'] > 0:
            stats['win_rate'] = (stats['wins'] / stats['trades']) * 100
            stats['avg_trade'] = stats['total_pnl'] / stats['trades']
            stats['expectancy'] = stats['avg_trade']  # Simplified expectancy

    return dict(model_stats)


def get_default_comprehensive_stats():
    """Return default statistics structure when no trades exist."""
    return {
        'total_pnl': 0,
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'breakeven_trades': 0,
        'win_rate': 0,
        'profit_factor': 0,
        'expectancy': 0,
        'average_trade': 0,
        'sqn': 0,
        'gross_profit': 0,
        'gross_loss': 0,
        'avg_win': 0,
        'avg_loss': 0,
        'win_days': 0,
        'loss_days': 0,
        'daily_win_rate': 0,
        'avg_wins_per_day': 0,
        'daily_expectancy': 0,
        'model_expectancies': {},
        'best_model': {'name': 'N/A', 'expectancy': 0},
        'worst_model': {'name': 'N/A', 'expectancy': 0}
    }


def get_default_chart_data():
    """Return default chart data structure when no trades exist."""
    return {
        'equity_labels': [],
        'equity_data': [],
        'daily_labels': [],
        'daily_pnl': [],
        'monthly_labels': [],
        'monthly_pnl': [],
        'max_equity': 0,
        'min_equity': 0,
        'total_return': 0
    }


@main_bp.route('/api/trades')
@login_required
def api_trades():
    """
    API endpoint for paginated trades data with sorting and filtering.
    Supports the enterprise-level table functionality.
    """
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 25, type=int), 100)  # Max 100 per page
        sort_field = request.args.get('sort', 'trade_date')
        sort_order = request.args.get('order', 'desc')

        # Filter parameters
        search = request.args.get('search', '').strip()
        symbol_filter = request.args.get('symbol', '').strip()
        model_filter = request.args.get('model', '').strip()
        direction_filter = request.args.get('direction', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()

        # Start building the query
        query = Trade.query.filter_by(user_id=current_user.id)

        # Apply filters
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                or_(
                    Trade.instrument.ilike(search_term),
                    Trade.trading_model.ilike(search_term),
                    Trade.direction.ilike(search_term)
                )
            )

        if symbol_filter:
            query = query.filter(Trade.instrument == symbol_filter)

        if model_filter:
            query = query.filter(Trade.trading_model == model_filter)

        if direction_filter:
            query = query.filter(Trade.direction.ilike(f'%{direction_filter}%'))

        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                query = query.filter(Trade.trade_date >= from_date)
            except ValueError:
                pass

        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                query = query.filter(Trade.trade_date <= to_date)
            except ValueError:
                pass

        # Apply sorting
        if sort_field and hasattr(Trade, sort_field):
            sort_column = getattr(Trade, sort_field)
            if sort_order.lower() == 'desc':
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            # Default sorting
            query = query.order_by(Trade.trade_date.desc(), Trade.id.desc())

        # Execute paginated query
        trades_pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        # Format trades data for JSON response
        trades_data = []
        for trade in trades_pagination.items:
            trades_data.append({
                'id': trade.id,
                'trade_date': trade.trade_date.strftime('%Y-%m-%d') if trade.trade_date else None,
                'instrument': trade.instrument,  # Uses the property
                'trading_model': trade.trading_model.name if trade.trading_model else None,
                'direction': trade.direction,
                'total_contracts_entered': trade.total_contracts_entered or 0,
                'entry_price': float(trade.average_entry_price) if trade.average_entry_price else 0,
                'exit_price': float(trade.average_exit_price) if trade.average_exit_price else 0,
                'pnl': float(trade.pnl) if trade.pnl else 0,
                'time_in_trade': get_time_in_trade_minutes(trade),
                'entry_time': get_first_entry_time(trade),
                'exit_time': get_last_exit_time(trade),
                'how_closed': trade.how_closed
            })

        return jsonify({
            'trades': trades_data,
            'pagination': {
                'page': trades_pagination.page,
                'pages': trades_pagination.pages,
                'per_page': trades_pagination.per_page,
                'total': trades_pagination.total,
                'has_next': trades_pagination.has_next,
                'has_prev': trades_pagination.has_prev
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Debug route to check data
@main_bp.route('/debug/data')
@login_required
def debug_data():
    """Debug route to check what data exists for the user."""
    try:
        trades = Trade.query.filter_by(user_id=current_user.id).all()

        debug_info = {
            'user_id': current_user.id,
            'username': current_user.username,
            'total_trades': len(trades),
            'trades_with_pnl': len([t for t in trades if t.pnl is not None]),
            'trades_sample': []
        }

        # Get sample of first 5 trades
        for trade in trades[:5]:
            trade_info = {
                'id': trade.id,
                'date': trade.trade_date.strftime('%Y-%m-%d') if trade.trade_date else None,
                'instrument': trade.instrument,
                'pnl': float(trade.pnl) if trade.pnl else None,
                'has_entries': trade.entries.count(),
                'has_exits': trade.exits.count(),
                'trading_model': trade.trading_model.name if trade.trading_model else None
            }
            debug_info['trades_sample'].append(trade_info)

        return jsonify(debug_info)

    except Exception as e:
        return jsonify({'error': str(e), 'traceback': str(e.__traceback__)})





@main_bp.route('/api/dashboard-data')
@login_required
def dashboard_data():
    """Optimized API endpoint to serve dashboard data as JSON"""
    try:
        # OPTIMIZATION 1: Single optimized query with eager loading
        trades = Trade.query.filter_by(user_id=current_user.id) \
            .options(joinedload(Trade.trading_model)) \
            .order_by(Trade.trade_date.asc()) \
            .all()

        print(f"API DEBUG: Found {len(trades)} trades for user {current_user.id}")

        # OPTIMIZATION 2: Batch calculate all data at once
        stats, calendar_data, chart_data, model_analytics = calculate_all_dashboard_data(trades)

        # OPTIMIZATION 3: Simplified trades data (only what's needed for table)
        trades_data = prepare_simplified_trades_data(trades[-50:])  # Only last 50 trades

        # Current date info for calendar
        today = py_date.today()

        response_data = {
            'stats': stats,
            'calendar_data': calendar_data,
            'trades_data': trades_data,
            'chart_data': chart_data,
            'model_analytics': model_analytics,
            'current_month': today.strftime('%B %Y'),
            'current_month_num': today.month,
            'current_year': today.year,
            'today_str': today.strftime('%Y-%m-%d')
        }

        print(f"API DEBUG: Returning data with {len(trades_data)} trades, {len(calendar_data)} calendar days")
        return jsonify(response_data)

    except Exception as e:
        import traceback
        print(f"API Error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'stats': get_default_comprehensive_stats(),
            'calendar_data': {},
            'trades_data': [],
            'chart_data': get_default_chart_data(),
            'model_analytics': {},
            'current_month': py_date.today().strftime('%B %Y'),
            'current_month_num': py_date.today().month,
            'current_year': py_date.today().year,
            'today_str': py_date.today().strftime('%Y-%m-%d')
        })


def calculate_all_dashboard_data(trades):
    """
    OPTIMIZATION: Calculate all dashboard data in a single pass
    This reduces multiple iterations over the same data
    """
    if not trades:
        return (
            get_default_comprehensive_stats(),
            {},
            get_default_chart_data(),
            {}
        )

    # Initialize all data structures
    trade_pnls = []
    daily_data = defaultdict(lambda: {'pnl': 0, 'trades': 0, 'wins': 0, 'losses': 0})
    calendar_data = {}
    model_data = defaultdict(lambda: {'trades': 0, 'total_pnl': 0, 'wins': 0, 'losses': 0})
    equity_curve = []
    equity_labels = []
    monthly_data = defaultdict(float)

    # SINGLE PASS through all trades
    running_total = 0

    for trade in trades:
        if trade.pnl is None:
            continue

        pnl = float(trade.pnl)
        trade_pnls.append(pnl)

        # Update running equity
        running_total += pnl

        if trade.trade_date:
            date_str = trade.trade_date.strftime('%Y-%m-%d')

            # Calendar data
            if date_str not in calendar_data:
                calendar_data[date_str] = {'pnl': 0, 'trades': 0}
            calendar_data[date_str]['pnl'] += pnl
            calendar_data[date_str]['trades'] += 1

            # Daily analytics
            daily_data[date_str]['pnl'] += pnl
            daily_data[date_str]['trades'] += 1
            if pnl > 0:
                daily_data[date_str]['wins'] += 1
            elif pnl < 0:
                daily_data[date_str]['losses'] += 1

            # Equity curve (sample every 10th trade for performance)
            if len(equity_curve) == 0 or len(trade_pnls) % 5 == 0:
                equity_curve.append(round(running_total, 2))
                equity_labels.append(trade.trade_date.strftime('%m/%d'))

            # Monthly data
            month_key = trade.trade_date.strftime('%Y-%m')
            monthly_data[month_key] += pnl

        # Model data
        model_name = trade.trading_model.name if trade.trading_model else 'Unknown'
        model_data[model_name]['trades'] += 1
        model_data[model_name]['total_pnl'] += pnl
        if pnl > 0:
            model_data[model_name]['wins'] += 1
        elif pnl < 0:
            model_data[model_name]['losses'] += 1

    # Round calendar PnL values
    for date_str in calendar_data:
        calendar_data[date_str]['pnl'] = round(calendar_data[date_str]['pnl'], 2)

    # Calculate final statistics
    stats = calculate_stats_from_data(trade_pnls, daily_data, model_data)
    chart_data = prepare_chart_data_from_data(equity_curve, equity_labels, daily_data, monthly_data)
    model_analytics = prepare_model_analytics_from_data(model_data)

    return stats, calendar_data, chart_data, model_analytics


def calculate_stats_from_data(trade_pnls, daily_data, model_data):
    """Calculate stats from pre-processed data"""
    if not trade_pnls:
        return get_default_comprehensive_stats()

    total_trades = len(trade_pnls)
    total_pnl = sum(trade_pnls)
    winning_trades = [pnl for pnl in trade_pnls if pnl > 0]
    losing_trades = [pnl for pnl in trade_pnls if pnl < 0]

    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

    gross_profit = sum(winning_trades) if winning_trades else 0
    gross_loss = abs(sum(losing_trades)) if losing_trades else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

    average_trade = total_pnl / total_trades if total_trades > 0 else 0
    avg_win = statistics.mean(winning_trades) if winning_trades else 0
    avg_loss = abs(statistics.mean(losing_trades)) if losing_trades else 0

    expectancy = (win_rate / 100 * avg_win) - ((100 - win_rate) / 100 * avg_loss)

    # SQN calculation
    if len(trade_pnls) > 1:
        std_dev = statistics.stdev(trade_pnls)
        sqn = (average_trade / std_dev) * math.sqrt(total_trades) if std_dev > 0 else 0
    else:
        sqn = 0

    # Daily analytics from pre-calculated data
    win_days = sum(1 for day in daily_data.values() if day['pnl'] > 0)
    loss_days = sum(1 for day in daily_data.values() if day['pnl'] < 0)
    total_days = len(daily_data)
    daily_win_rate = (win_days / total_days * 100) if total_days > 0 else 0

    total_wins = sum(day['wins'] for day in daily_data.values())
    avg_wins_per_day = total_wins / total_days if total_days > 0 else 0
    daily_expectancy = total_pnl / total_days if total_days > 0 else 0

    # Model expectancies
    expectancies = {}
    for model, data in model_data.items():
        if data['trades'] > 0:
            expectancies[model] = data['total_pnl'] / data['trades']

    best_model = max(expectancies.items(), key=lambda x: x[1]) if expectancies else ('N/A', 0)
    worst_model = min(expectancies.items(), key=lambda x: x[1]) if expectancies else ('N/A', 0)

    return {
        'total_pnl': round(total_pnl, 2),
        'total_trades': total_trades,
        'winning_trades': win_count,
        'losing_trades': loss_count,
        'breakeven_trades': total_trades - win_count - loss_count,
        'win_rate': round(win_rate, 1),
        'profit_factor': round(profit_factor, 2),
        'expectancy': round(expectancy, 2),
        'average_trade': round(average_trade, 2),
        'sqn': round(sqn, 1),
        'gross_profit': round(gross_profit, 2),
        'gross_loss': round(gross_loss, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'win_days': win_days,
        'loss_days': loss_days,
        'daily_win_rate': round(daily_win_rate, 1),
        'avg_wins_per_day': round(avg_wins_per_day, 1),
        'daily_expectancy': round(daily_expectancy, 2),
        'model_expectancies': expectancies,
        'best_model': {'name': best_model[0], 'expectancy': best_model[1]},
        'worst_model': {'name': worst_model[0], 'expectancy': worst_model[1]}
    }


def prepare_chart_data_from_data(equity_curve, equity_labels, daily_data, monthly_data):
    """Prepare chart data from pre-processed data"""
    # Sample daily data for performance (last 20 days)
    daily_items = list(daily_data.items())[-20:] if len(daily_data) > 20 else list(daily_data.items())
    daily_labels = [datetime.strptime(item[0], '%Y-%m-%d').strftime('%m/%d') for item in daily_items]
    daily_pnl = [round(item[1]['pnl'], 2) for item in daily_items]

    # Sample monthly data (last 12 months)
    monthly_items = list(monthly_data.items())[-12:] if len(monthly_data) > 12 else list(monthly_data.items())
    monthly_labels = [datetime.strptime(item[0], '%Y-%m').strftime('%b %Y') for item in monthly_items]
    monthly_pnl = [round(item[1], 2) for item in monthly_items]

    return {
        'equity_labels': equity_labels,
        'equity_data': equity_curve,
        'daily_labels': daily_labels,
        'daily_pnl': daily_pnl,
        'monthly_labels': monthly_labels,
        'monthly_pnl': monthly_pnl,
        'max_equity': max(equity_curve) if equity_curve else 0,
        'min_equity': min(equity_curve) if equity_curve else 0,
        'total_return': equity_curve[-1] if equity_curve else 0
    }


def prepare_model_analytics_from_data(model_data):
    """Prepare model analytics from pre-processed data"""
    model_analytics = {}

    for model, data in model_data.items():
        if data['trades'] > 0:
            win_rate = (data['wins'] / data['trades']) * 100
            model_analytics[model] = {
                'trades': data['trades'],
                'total_pnl': data['total_pnl'],
                'wins': data['wins'],
                'losses': data['losses'],
                'win_rate': win_rate,
                'avg_trade': data['total_pnl'] / data['trades'],
                'expectancy': data['total_pnl'] / data['trades']
            }

    return model_analytics


def prepare_simplified_trades_data(trades):
    """Simplified trades data preparation - only essential fields"""
    trades_data = []

    for trade in trades:
        try:
            trades_data.append({
                'id': trade.id,
                'trade_date': trade.trade_date.strftime('%Y-%m-%d') if trade.trade_date else None,
                'instrument': trade.instrument or 'N/A',
                'trading_model': trade.trading_model.name if trade.trading_model else 'N/A',
                'direction': trade.direction or 'N/A',
                'total_contracts_entered': trade.total_contracts_entered or 0,
                'pnl': round(float(trade.pnl), 2) if trade.pnl else 0,
                # Skip time calculations for performance - they're expensive
                'time_in_trade': None,
                'entry_time': None,
                'exit_time': None,
                'how_closed': trade.how_closed
            })
        except Exception as e:
            print(f"Error processing trade {trade.id}: {e}")
            continue

    return trades_data


# Add these imports to the top of your app/blueprints/main_bp.py file
# (if they're not already there):



@main_bp.route('/portfolio-analytics')
@login_required
@sync_discord_roles_if_needed
@require_discord_permission('can_access_portfolio')
def portfolio_analytics():
    """Portfolio performance analysis dashboard - Premium feature."""
    try:
        # Log access for audit trail
        record_activity('portfolio_access', 'Accessed portfolio analytics dashboard')

        # Get user's permission level for template context
        permissions = current_user.get_discord_permissions()

        # You can add any portfolio-specific data here
        # For now, we'll just render the template

        return render_template('portfolio_analytics.html',
                               title='Portfolio Analytics - Trading Journal',
                               user=current_user,
                               permissions=permissions)

    except Exception as e:
        current_app.logger.error(f"Error loading portfolio analytics for {current_user.username}: {e}", exc_info=True)
        flash('Failed to load portfolio analytics. Please try again.', 'danger')
        return redirect(url_for('main.index'))


@main_bp.route('/backtesting')
@login_required
@sync_discord_roles_if_needed
@require_discord_permission('can_access_backtesting')
def backtesting():
    """Captain Backtest - Premium backtesting feature."""
    try:
        record_activity('backtesting_access', 'Accessed backtesting tools')
        permissions = current_user.get_discord_permissions()

        return render_template('backtesting.html',
                               title='Captain Backtest - Trading Journal',
                               user=current_user,
                               permissions=permissions)

    except Exception as e:
        current_app.logger.error(f"Error loading backtesting for {current_user.username}: {e}", exc_info=True)
        flash('Failed to load backtesting tools. Please try again.', 'danger')
        return redirect(url_for('main.index'))


@main_bp.route('/live-trading')
@login_required
@sync_discord_roles_if_needed
@require_discord_permission('can_access_live_trading')
def live_trading():
    """Live Trading Interface - VIP feature."""
    try:
        record_activity('live_trading_access', 'Accessed live trading interface')
        permissions = current_user.get_discord_permissions()

        return render_template('live_trading.html',
                               title='Live Trading - Trading Journal',
                               user=current_user,
                               permissions=permissions)

    except Exception as e:
        current_app.logger.error(f"Error loading live trading for {current_user.username}: {e}", exc_info=True)
        flash('Failed to load live trading interface. Please try again.', 'danger')
        return redirect(url_for('main.index'))


@main_bp.route('/advanced-analytics')
@login_required
@sync_discord_roles_if_needed
@require_discord_permission('can_access_analytics')
def advanced_analytics():
    """Advanced Analytics - Premium feature."""
    try:
        record_activity('analytics_access', 'Accessed advanced analytics')
        permissions = current_user.get_discord_permissions()

        return render_template('advanced_analytics.html',
                               title='Advanced Analytics - Trading Journal',
                               user=current_user,
                               permissions=permissions)

    except Exception as e:
        current_app.logger.error(f"Error loading advanced analytics for {current_user.username}: {e}", exc_info=True)
        flash('Failed to load advanced analytics. Please try again.', 'danger')
        return redirect(url_for('main.index'))


@main_bp.route('/preview1')
def TEST_PAGE1():
    """Route to preview the TEST-PAGE.html file"""
    return render_template('backtesting.html')


@main_bp.route('/preview2')
def TEST_PAGE2():
    """Route to preview the TEST-PAGE.html file"""
    return render_template('errors/404.html')


@main_bp.route('/preview3')
def TEST_PAGE3():
    """Route to preview the TEST-PAGE.html file"""
    return render_template('profile.html')