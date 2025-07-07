from flask import render_template, request, flash, redirect, url_for, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import func, desc, asc, and_, or_
from datetime import datetime, timedelta
import json
from decimal import Decimal
import statistics
import math
from collections import defaultdict
from . import bp
from app.models import TradingModel, Trade, EntryPoint, ExitPoint, db
from app.utils.calculations import calculate_trade_pnl, calculate_risk_reward_ratio

# Configuration for analytics calculations
ANALYTICS_CONFIG = {
    'default_risk_per_trade': 100,  # Default risk amount per trade in dollars
    'default_account_size': 10000,  # Default account size for percentage calculations
}


def get_risk_parameters(user_id=None):
    """Get user-specific risk parameters or defaults."""
    return {
        'risk_per_trade': ANALYTICS_CONFIG['default_risk_per_trade'],
        'account_size': ANALYTICS_CONFIG['default_account_size']
    }


@bp.route('/view/<int:model_id>')
@login_required
def view_model_detail(model_id):
    """
    Detailed analytics page for a specific trading model.
    Shows comprehensive performance metrics based on Random's methodology.
    """
    # Get the trading model - allow access to both user's models and default models
    model = TradingModel.query.filter(
        db.or_(
            db.and_(TradingModel.id == model_id, TradingModel.user_id == current_user.id),
            db.and_(TradingModel.id == model_id, TradingModel.is_default == True)
        )
    ).first_or_404()

    # Get all trades for this model (only user's trades)
    trades_query = Trade.query.filter_by(
        trading_model_id=model_id,
        user_id=current_user.id
    ).order_by(Trade.trade_date.desc(), Trade.id.desc())

    trades = trades_query.all()
    # If no trades, show empty state
    if not trades:
        return render_template('model_detail.html',
                               model=model,
                               trades=[],
                               analytics={},
                               has_trades=False,
                               equity_data_json='{"labels": [], "data": []}')  # ← FIXED: Always provide JSON

    # Calculate comprehensive analytics
    risk_params = get_risk_parameters(current_user.id)
    analytics = calculate_model_analytics(trades, risk_params)

    # Prepare equity curve data
    equity_data = prepare_equity_curve_data(trades)

    # ← FIXED: Ensure proper JSON serialization with error handling
    try:
        equity_data_json = json.dumps(equity_data, default=str)

    except Exception as e:

        equity_data_json = '{"labels": [], "data": []}'

    # Get model-specific insights based on Random's methodology
    model_insights = generate_model_insights(model, analytics)

    return render_template('model_detail.html',
                           model=model,
                           trades=[],
                           total_trades=len(trades),
                           analytics=analytics,
                           equity_data=equity_data,  # ← Keep for template access
                           equity_data_json=equity_data_json,  # ← FIXED: Proper JSON string
                           model_insights=model_insights,
                           has_trades=True)


def calculate_model_analytics(trades, risk_params=None):
    """
    Calculate comprehensive trading model analytics based on Random's methodology.
    Includes all requested metrics for complete performance analysis.

    Args:
        trades: List of trade objects
        risk_params: Dictionary with 'risk_per_trade' and 'account_size'

    Returns:
        Dictionary with all performance, risk, and consistency metrics.
    """
    if not trades:
        return {}

    if risk_params is None:
        risk_params = get_risk_parameters()

    # Extract trade data
    pnl_values = []
    r_multiples = []
    win_amounts = []
    loss_amounts = []
    trade_dates = []
    daily_pnls = defaultdict(float)  # For daily analysis

    for trade in trades:
        pnl = float(trade.pnl or 0)
        pnl_values.append(pnl)

        # Track daily P&L
        if trade.trade_date:
            daily_pnls[trade.trade_date] += pnl

        # Calculate R-multiple (assuming risk_per_trade as 1R)
        risk_amount = risk_params['risk_per_trade']
        r_multiple = pnl / risk_amount if risk_amount > 0 else 0
        r_multiples.append(r_multiple)

        if pnl > 0:
            win_amounts.append(pnl)
        elif pnl < 0:
            loss_amounts.append(abs(pnl))

        if trade.entry_timestamp:
            trade_dates.append(trade.entry_timestamp)
        elif trade.trade_date:
            trade_dates.append(datetime.combine(trade.trade_date, datetime.min.time()))

    # Basic Performance Metrics
    total_trades = len(trades)
    winning_trades = len([p for p in pnl_values if p > 0])
    losing_trades = len([p for p in pnl_values if p < 0])
    breakeven_trades = len([p for p in pnl_values if p == 0])

    net_pnl = sum(pnl_values)
    gross_profit = sum(win_amounts)
    gross_loss = sum(loss_amounts)

    # Win/Loss Rates
    win_rate = (winning_trades / total_trades) if total_trades > 0 else 0
    loss_rate = (losing_trades / total_trades) if total_trades > 0 else 0
    strike_rate = win_rate * 100

    # Profit Factor
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0

    # Expected Value and Averages
    expected_value = statistics.mean(pnl_values) if pnl_values else 0
    median_profit = statistics.median(pnl_values) if pnl_values else 0
    average_profit = expected_value

    # Win/Loss Analysis
    avg_win = statistics.mean(win_amounts) if win_amounts else 0
    avg_loss = statistics.mean(loss_amounts) if loss_amounts else 0
    largest_win = max(win_amounts) if win_amounts else 0
    largest_loss = max(loss_amounts) if loss_amounts else 0

    # R-Multiple Analysis
    total_r = sum(r_multiples)
    avg_r = statistics.mean(r_multiples) if r_multiples else 0
    avg_win_r = statistics.mean([r for r in r_multiples if r > 0]) if any(r > 0 for r in r_multiples) else 0
    avg_loss_r = statistics.mean([r for r in r_multiples if r < 0]) if any(r < 0 for r in r_multiples) else 0
    largest_win_r = max(r_multiples) if r_multiples else 0
    largest_loss_r = min(r_multiples) if r_multiples else 0

    # Standard Deviation
    standard_deviation = statistics.stdev(r_multiples) if len(r_multiples) > 1 else 0

    # Kelly Fraction Calculation
    if gross_loss > 0 and win_rate > 0:
        if avg_loss > 0:
            kelly_fraction = (win_rate * avg_win - loss_rate * avg_loss) / avg_win * 100
        else:
            kelly_fraction = 0
    else:
        kelly_fraction = 0

    # SQN (System Quality Number)
    if len(r_multiples) > 1:
        r_mean = statistics.mean(r_multiples)
        r_stdev = statistics.stdev(r_multiples)
        sqn = (r_mean / r_stdev * math.sqrt(len(r_multiples))) if r_stdev > 0 else 0
        sqn_100 = sqn * math.sqrt(100 / len(r_multiples)) if len(r_multiples) > 0 else 0
    else:
        sqn = 0
        sqn_100 = 0

    # Drawdown Analysis
    running_total = 0
    peak = 0
    drawdowns = []
    equity_curve = []
    drawdown_durations = []
    current_drawdown_duration = 0
    in_drawdown = False

    for pnl in pnl_values:
        running_total += pnl
        equity_curve.append(running_total)

        if running_total > peak:
            peak = running_total
            if in_drawdown:
                drawdown_durations.append(current_drawdown_duration)
                current_drawdown_duration = 0
                in_drawdown = False

        drawdown = peak - running_total
        drawdowns.append(drawdown)

        if drawdown > 0:
            if not in_drawdown:
                in_drawdown = True
                current_drawdown_duration = 1
            else:
                current_drawdown_duration += 1

    # Add final drawdown duration if still in drawdown
    if in_drawdown:
        drawdown_durations.append(current_drawdown_duration)

    max_drawdown = max(drawdowns) if drawdowns else 0
    median_drawdown = statistics.median([d for d in drawdowns if d > 0]) if any(d > 0 for d in drawdowns) else 0
    avg_drawdown = statistics.mean([d for d in drawdowns if d > 0]) if any(d > 0 for d in drawdowns) else 0
    longest_drawdown_duration = max(drawdown_durations) if drawdown_durations else 0
    median_drawdown_duration = statistics.median(drawdown_durations) if drawdown_durations else 0

    # Streak Analysis
    current_streak = 0
    max_win_streak = 0
    max_loss_streak = 0
    current_win_streak = 0
    current_loss_streak = 0

    profit_streaks = []
    loss_streaks = []
    current_profit_streak = 0
    current_loss_streak_count = 0

    for pnl in pnl_values:
        if pnl > 0:
            current_win_streak += 1
            current_loss_streak = 0
            current_profit_streak += 1
            if current_loss_streak_count > 0:
                loss_streaks.append(current_loss_streak_count)
                current_loss_streak_count = 0
        elif pnl < 0:
            current_loss_streak += 1
            current_win_streak = 0
            current_loss_streak_count += 1
            if current_profit_streak > 0:
                profit_streaks.append(current_profit_streak)
                current_profit_streak = 0
        else:  # breakeven
            if current_profit_streak > 0:
                profit_streaks.append(current_profit_streak)
                current_profit_streak = 0
            if current_loss_streak_count > 0:
                loss_streaks.append(current_loss_streak_count)
                current_loss_streak_count = 0

        max_win_streak = max(max_win_streak, current_win_streak)
        max_loss_streak = max(max_loss_streak, current_loss_streak)

    # Add final streaks
    if current_profit_streak > 0:
        profit_streaks.append(current_profit_streak)
    if current_loss_streak_count > 0:
        loss_streaks.append(current_loss_streak_count)

    median_profit_streak = statistics.median(profit_streaks) if profit_streaks else 0
    median_expense_streak = statistics.median(loss_streaks) if loss_streaks else 0

    # Time-based metrics
    trading_period_days = 0
    daily_ev = 0
    trades_per_day = 0
    avg_r_per_day = 0
    avg_r_per_week = 0
    avg_r_per_month = 0
    avg_annual_r = 0
    percent_days_positive = 0

    if trade_dates and len(trade_dates) > 1:
        first_trade = min(trade_dates)
        last_trade = max(trade_dates)
        trading_period_days = (last_trade - first_trade).days + 1

        if trading_period_days > 0:
            daily_ev = net_pnl / trading_period_days
            trades_per_day = total_trades / trading_period_days
            avg_r_per_day = total_r / trading_period_days
            avg_r_per_week = avg_r_per_day * 7
            avg_r_per_month = avg_r_per_day * 30
            avg_annual_r = avg_r_per_day * 252

        # Calculate % days positive
        positive_days = len([pnl for pnl in daily_pnls.values() if pnl > 0])
        total_trading_days = len(daily_pnls)
        percent_days_positive = (positive_days / total_trading_days * 100) if total_trading_days > 0 else 0

    # Median EV (Expected Value)
    median_ev = median_profit

    # Skewness and Kurtosis
    if len(pnl_values) > 2:
        skewness = calculate_skewness(pnl_values)
        kurtosis = calculate_kurtosis(pnl_values)
        skewness_returns = calculate_skewness(r_multiples) if len(r_multiples) > 2 else 0
    else:
        skewness = 0
        kurtosis = 0
        skewness_returns = 0

    # Expectancy (alternative calculation)
    expectancy = (avg_win_r * win_rate) - (abs(avg_loss_r) * loss_rate)

    # Return on Investment (ROI)
    account_size = risk_params.get('account_size', 10000)
    roi = (net_pnl / account_size * 100) if account_size > 0 else 0

    # Risk-Reward Ratio
    defined_risk_reward = abs(avg_win_r / avg_loss_r) if avg_loss_r != 0 else 0

    # MFE (Maximum Favorable Excursion) - simplified calculation
    mfe_equity = max(equity_curve) if equity_curve else 0

    # Calculate weekly MFE (approximation)
    avg_weekly_mfe = mfe_equity / (trading_period_days / 7) if trading_period_days > 7 else mfe_equity

    # Quarterly RR (approximation)
    quarterly_rr = avg_annual_r / 4 if avg_annual_r else 0

    # Max losing trades in sequence
    max_losing_trades = max_loss_streak

    # Average Loss with Constant Risk
    avg_loss_constant_risk = avg_loss_r * risk_params.get('risk_per_trade', 100)

    return {
        # Basic Performance
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'breakevens': breakeven_trades,
        'net_pnl': net_pnl,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'strike_rate': round(strike_rate, 1),
        'win_rate': round(win_rate * 100, 1),
        'loss_rate': round(loss_rate * 100, 1),
        'profit_factor': round(profit_factor, 2),
        'expected_value': round(expected_value, 2),
        'median_profit': round(median_profit, 2),
        'average_profit': round(average_profit, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'largest_win': round(largest_win, 2),
        'largest_loss': round(largest_loss, 2),

        # R-Multiple Analysis
        'total_r': round(total_r, 2),
        'avg_r': round(avg_r, 2),
        'avg_win_r': round(avg_win_r, 2),
        'avg_loss_r': round(avg_loss_r, 2),
        'largest_win_r': round(largest_win_r, 2),
        'largest_loss_r': round(largest_loss_r, 2),
        'standard_deviation': round(standard_deviation, 2),

        # Advanced Analytics
        'sqn': round(sqn, 2),
        'sqn_100': round(sqn_100, 2),
        'kelly_fraction': round(kelly_fraction, 1),
        'expectancy': round(expectancy, 2),
        'skewness': round(skewness, 2),
        'kurtosis': round(kurtosis, 2),
        'skewness_returns': round(skewness_returns, 2),
        'roi': round(roi, 2),
        'defined_risk_reward': round(defined_risk_reward, 2),

        # Risk & Drawdown
        'max_drawdown': round(max_drawdown, 2),
        'median_drawdown': round(median_drawdown, 2),
        'avg_drawdown': round(avg_drawdown, 2),
        'longest_drawdown_duration': longest_drawdown_duration,
        'median_drawdown_duration': median_drawdown_duration,
        'max_consecutive_wins': max_win_streak,
        'max_consecutive_losses': max_loss_streak,
        'max_losing_trades': max_losing_trades,
        'median_profit_streak': median_profit_streak,
        'median_expense_streak': median_expense_streak,

        # Time-based
        'trading_period_days': trading_period_days,
        'daily_ev': round(daily_ev, 2),
        'median_ev': round(median_ev, 2),
        'trades_per_day': round(trades_per_day, 2),
        'avg_r_per_day': round(avg_r_per_day, 2),
        'avg_r_per_week': round(avg_r_per_week, 2),
        'avg_r_per_month': round(avg_r_per_month, 2),
        'avg_annual_r': round(avg_annual_r, 2),
        'percent_days_positive': round(percent_days_positive, 1),
        'mfe_equity': round(mfe_equity, 2),
        'avg_weekly_mfe': round(avg_weekly_mfe, 2),
        'quarterly_rr': round(quarterly_rr, 2),

        # Additional metrics for template compatibility
        'total_profit_moves': winning_trades,
        'total_expense_moves': losing_trades,
        'total_moves': total_trades,
        'account_size': account_size,
        'avg_loss_constant_risk': round(avg_loss_constant_risk, 2),
    }


def calculate_skewness(data):
    """Calculate skewness of a dataset."""
    if len(data) < 3:
        return 0

    mean = statistics.mean(data)
    std = statistics.stdev(data)

    if std == 0:
        return 0

    n = len(data)
    skew = sum(((x - mean) / std) ** 3 for x in data) / n
    return skew


def calculate_kurtosis(data):
    """Calculate kurtosis of a dataset."""
    if len(data) < 4:
        return 0

    mean = statistics.mean(data)
    std = statistics.stdev(data)

    if std == 0:
        return 0

    n = len(data)
    kurt = sum(((x - mean) / std) ** 4 for x in data) / n - 3
    return kurt


def prepare_equity_curve_data(trades):
    """Prepare equity curve data for Chart.js visualization with enhanced debugging."""


    if not trades:

        return {'labels': [], 'data': []}

    # Sort trades by entry_timestamp (handling the property correctly)
    sorted_trades = []
    for i, trade in enumerate(trades):
        # Get the entry_timestamp property value and add it as a sort key
        entry_ts = trade.entry_timestamp
        if not entry_ts and trade.trade_date:
            # Fallback to trade_date if entry_timestamp is None
            entry_ts = datetime.combine(trade.trade_date, datetime.min.time())

        # Get P&L value - FIXED: Better P&L handling
        pnl = 0.0
        if hasattr(trade, 'pnl') and trade.pnl is not None:
            pnl = float(trade.pnl)
        elif hasattr(trade, 'realized_pnl') and trade.realized_pnl is not None:
            pnl = float(trade.realized_pnl)


        sorted_trades.append((trade, entry_ts or datetime.min, pnl))

    # Sort by the timestamp
    sorted_trades.sort(key=lambda x: x[1])


    labels = []
    equity_data = []
    running_total = 0.0

    for i, (trade, timestamp, pnl) in enumerate(sorted_trades):
        running_total += pnl

        # Format date for chart - FIXED: More robust date formatting
        if timestamp and timestamp != datetime.min:
            date_str = timestamp.strftime('%m/%d/%Y')
        elif trade.trade_date:
            date_str = trade.trade_date.strftime('%m/%d/%Y')
        else:
            date_str = f'Trade {i + 1}'

        labels.append(date_str)
        equity_data.append(round(running_total, 2))


    result = {
        'labels': labels,
        'data': equity_data
    }
    return result


def generate_model_insights(model, analytics):
    """Generate insights based on Random's trading methodology."""
    insights = []

    if analytics.get('sqn', 0) > 2.5:
        insights.append("Excellent system quality (SQN > 2.5)")
    elif analytics.get('sqn', 0) > 1.6:
        insights.append("Good system quality (SQN > 1.6)")
    elif analytics.get('sqn', 0) < 1.0:
        insights.append("System needs improvement (SQN < 1.0)")

    if analytics.get('profit_factor', 0) > 2.0:
        insights.append("Strong profit factor (> 2.0)")
    elif analytics.get('profit_factor', 0) < 1.2:
        insights.append("Profit factor needs improvement (< 1.2)")

    if analytics.get('kelly_fraction', 0) < 0:
        insights.append("Negative Kelly suggests system is not profitable")
    elif analytics.get('kelly_fraction', 0) > 25:
        insights.append("High Kelly suggests aggressive position sizing")

    return insights


@bp.route('/')
@login_required
def models_list():
    """List all trading models for the current user."""
    # Get user's personal models
    user_models = TradingModel.query.filter_by(
        user_id=current_user.id,
        is_default=False
    ).order_by(TradingModel.name).all()

    # Get default models (Random's models)
    default_models = TradingModel.query.filter_by(
        is_default=True
    ).order_by(TradingModel.name).all()

    # Get trade counts for each model
    models_with_counts = []
    all_models = user_models + default_models

    for model in all_models:
        trade_count = Trade.query.filter_by(
            trading_model_id=model.id,
            user_id=current_user.id
        ).count()

        models_with_counts.append({
            'model': model,
            'trade_count': trade_count
        })

    return render_template('view_trading_models_list.html',
                           title='Trading Models',
                           user_models=user_models,
                           default_models=default_models,
                           models_with_counts=models_with_counts)


# DEBUG: Add debugging function to check which file is loaded
def debug_blueprint_loading():
    """Debug function to verify correct file loading."""
    import os
    import inspect

    current_file = inspect.getfile(inspect.currentframe())


    return {
        'file_path': current_file,
        'blueprint_name': bp.name,
        'url_prefix': bp.url_prefix
    }


def safe_get_analytics_value(analytics_dict, key, default_value=0):
    """
    Helper function to safely get analytics values with proper defaults.
    Use this in your template or routes for extra safety.
    """
    if not analytics_dict:
        return default_value

    value = analytics_dict.get(key, default_value)

    # Handle None, empty string, or NaN values
    if value is None or value == '' or (isinstance(value, float) and math.isnan(value)):
        return default_value

    return value


def format_currency_safe(value, default=0):
    """Safe currency formatting that handles None/empty values."""
    if value is None or value == '':
        value = default
    try:
        return f"${value:,.0f}"
    except (ValueError, TypeError):
        return f"${default:,.0f}"


def format_percentage_safe(value, decimals=1, default=0):
    """Safe percentage formatting that handles None/empty values."""
    if value is None or value == '':
        value = default
    try:
        return f"{value:.{decimals}f}%"
    except (ValueError, TypeError):
        return f"{default:.{decimals}f}%"


def format_number_safe(value, decimals=2, default=0):
    """Safe number formatting that handles None/empty values."""
    if value is None or value == '':
        value = default
    try:
        return f"{value:.{decimals}f}"
    except (ValueError, TypeError):
        return f"{default:.{decimals}f}"


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_trading_model():
    """Add a new trading model."""
    from app.forms import TradingModelForm

    form = TradingModelForm()

    if form.validate_on_submit():
        model = TradingModel()
        form.populate_obj(model)
        model.user_id = current_user.id
        model.is_default = False

        try:
            db.session.add(model)
            db.session.commit()
            flash(f'Trading model "{model.name}" created successfully!', 'success')
            return redirect(url_for('trading_models.models_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating model: {str(e)}', 'danger')

    return render_template('add_trading_model.html',
                           title='Add Trading Model', form=form)


@bp.route('/edit/<int:model_id>', methods=['GET', 'POST'])
@login_required
def edit_trading_model(model_id):
    """Edit an existing trading model."""
    from app.forms import TradingModelForm

    model = TradingModel.query.filter_by(
        id=model_id,
        user_id=current_user.id
    ).first_or_404()

    form = TradingModelForm(obj=model)

    if form.validate_on_submit():
        form.populate_obj(model)

        try:
            db.session.commit()
            flash(f'Trading model "{model.name}" updated successfully!', 'success')
            return redirect(url_for('trading_models.view_model_detail', model_id=model.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating model: {str(e)}', 'danger')

    return render_template('edit_trading_model.html',
                           title=f'Edit {model.name}', form=form, model=model)


@bp.route('/delete/<int:model_id>', methods=['POST'])
@login_required
def delete_trading_model(model_id):
    """Delete a trading model."""
    model = TradingModel.query.filter_by(
        id=model_id,
        user_id=current_user.id
    ).first_or_404()

    try:
        db.session.delete(model)
        db.session.commit()
        flash(f'Trading model "{model.name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting model: {str(e)}', 'danger')

    return redirect(url_for('trading_models.models_list'))


