from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func, desc, extract
from datetime import datetime, timedelta, date as py_date
from collections import defaultdict
import calendar
from ..models import Trade, DailyJournal

# Defines the blueprint. The first argument, 'main', is the internal name.
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@main_bp.route('/index')
@login_required
def index():
    """
    Renders the main dashboard page with comprehensive trading statistics,
    charts data, and calendar integration.
    """
    try:
        # Get all trades for the current user
        trades = Trade.query.filter_by(user_id=current_user.id).order_by(Trade.trade_date.asc()).all()

        # Calculate basic statistics
        stats = calculate_trading_stats(trades)

        # Prepare calendar data - group trades by date
        calendar_data = prepare_calendar_data(trades)

        # Get recent trades (last 10)
        recent_trades = Trade.query.filter_by(user_id=current_user.id) \
            .order_by(desc(Trade.trade_date), desc(Trade.id)) \
            .limit(10).all()

        # Prepare chart data
        chart_data = prepare_chart_data(trades)

        # Current date info for calendar
        today = py_date.today()
        current_month = today.strftime('%B %Y')
        current_month_num = today.month
        current_year = today.year
        today_str = today.strftime('%Y-%m-%d')

        return render_template('main/dashboard.html',
                               title="Trading Dashboard",
                               stats=stats,
                               calendar_data=calendar_data,
                               recent_trades=recent_trades,
                               chart_data=chart_data,
                               current_month=current_month,
                               current_month_num=current_month_num,
                               current_year=current_year,
                               today_str=today_str)

    except Exception as e:
        # Fallback for any errors - show basic dashboard
        print(f"Dashboard error: {e}")
        return render_template('main/dashboard.html',
                               title="Trading Dashboard",
                               stats=get_default_stats(),
                               calendar_data={},
                               recent_trades=[],
                               chart_data=get_default_chart_data(),
                               current_month=py_date.today().strftime('%B %Y'),
                               current_month_num=py_date.today().month,
                               current_year=py_date.today().year,
                               today_str=py_date.today().strftime('%Y-%m-%d'))


def calculate_trading_stats(trades):
    """Calculate comprehensive trading statistics"""
    total_trades = len(trades)

    if total_trades == 0:
        return get_default_stats()

    # Filter trades with PnL data
    trades_with_pnl = [t for t in trades if t.pnl is not None]

    # Win/Loss calculations
    winning_trades = [t for t in trades_with_pnl if t.pnl > 0]
    losing_trades = [t for t in trades_with_pnl if t.pnl < 0]

    winning_count = len(winning_trades)
    losing_count = len(losing_trades)

    # Win rate
    win_rate = (winning_count / total_trades * 100) if total_trades > 0 else 0

    # PnL calculations
    total_pnl = sum(t.pnl for t in trades_with_pnl)
    gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
    gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0

    # Average winners and losers
    avg_winner = gross_profit / winning_count if winning_count > 0 else 0
    avg_loser = gross_loss / losing_count if losing_count > 0 else 0

    # Profit factor
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    return {
        'total_trades': total_trades,
        'win_rate': round(win_rate, 2),
        'winning_trades': winning_count,
        'losing_trades': losing_count,
        'total_pnl': round(total_pnl, 2),
        'avg_winner': round(avg_winner, 2),
        'avg_loser': round(avg_loser, 2),
        'profit_factor': round(profit_factor, 3),
        'gross_profit': round(gross_profit, 2),
        'gross_loss': round(gross_loss, 2)
    }


def prepare_calendar_data(trades):
    """Prepare calendar data with daily PnL and trade counts"""
    calendar_data = {}

    for trade in trades:
        date_str = trade.trade_date.strftime('%Y-%m-%d')

        if date_str not in calendar_data:
            calendar_data[date_str] = {'pnl': 0, 'trades': 0}

        calendar_data[date_str]['pnl'] += trade.pnl or 0
        calendar_data[date_str]['trades'] += 1

    # Round PnL values for display
    for date_str in calendar_data:
        calendar_data[date_str]['pnl'] = round(calendar_data[date_str]['pnl'], 2)

    return calendar_data


def prepare_chart_data(trades):
    """Prepare data for all dashboard charts"""
    if not trades:
        return get_default_chart_data()

    # Sort trades by date
    trades_sorted = sorted(trades, key=lambda t: t.trade_date)

    # Daily PnL data (last 30 days with trades)
    daily_data = defaultdict(float)
    for trade in trades_sorted:
        date_str = trade.trade_date.strftime('%m/%d')
        daily_data[date_str] += trade.pnl or 0

    # Get last 15 trading days for daily chart
    daily_items = list(daily_data.items())[-15:] if len(daily_data) > 15 else list(daily_data.items())
    daily_labels = [item[0] for item in daily_items]
    daily_pnl = [round(item[1], 2) for item in daily_items]

    # Equity curve calculation
    running_total = 0
    equity_curve = []
    equity_labels = []

    for trade in trades_sorted[-30:]:  # Last 30 trades for equity curve
        running_total += trade.pnl or 0
        equity_curve.append(round(running_total, 2))
        equity_labels.append(trade.trade_date.strftime('%m/%d'))

    # Monthly PnL data
    monthly_data = defaultdict(float)
    for trade in trades_sorted:
        month_key = trade.trade_date.strftime('%Y-%m')
        monthly_data[month_key] += trade.pnl or 0

    # Get last 6 months
    monthly_items = list(monthly_data.items())[-6:] if len(monthly_data) > 6 else list(monthly_data.items())
    monthly_labels = [datetime.strptime(item[0], '%Y-%m').strftime('%b %Y') for item in monthly_items]
    monthly_pnl = [round(item[1], 2) for item in monthly_items]

    return {
        'daily_labels': daily_labels,
        'daily_pnl': daily_pnl,
        'equity_labels': equity_labels,
        'equity_curve': equity_curve,
        'monthly_labels': monthly_labels,
        'monthly_pnl': monthly_pnl
    }


def get_default_stats():
    """Return default stats for users with no trades"""
    return {
        'total_trades': 0,
        'win_rate': 0.0,
        'winning_trades': 0,
        'losing_trades': 0,
        'total_pnl': 0.0,
        'avg_winner': 0.0,
        'avg_loser': 0.0,
        'profit_factor': 0.0,
        'gross_profit': 0.0,
        'gross_loss': 0.0
    }


def get_default_chart_data():
    """Return default chart data for users with no trades"""
    return {
        'daily_labels': [],
        'daily_pnl': [],
        'equity_labels': [],
        'equity_curve': [],
        'monthly_labels': [],
        'monthly_pnl': []
    }