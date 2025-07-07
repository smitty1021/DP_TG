from flask import render_template, request, flash, redirect, url_for, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import func, desc, asc, and_, or_
from datetime import datetime, timedelta
import json
from decimal import Decimal
import statistics
import math
from collections import defaultdict

from flask import Blueprint
bp = Blueprint('trading_models', __name__, url_prefix='/trading-models')
app.register_blueprint(trading_models_bp, url_prefix='/trading-models')
from app.models import TradingModel, Trade, EntryPoint, ExitPoint, db
from app.utils.calculations import calculate_trade_pnl, calculate_risk_reward_ratio


# Configuration for analytics calculations
ANALYTICS_CONFIG = {
    'default_risk_per_trade': 100,  # Default risk amount per trade in dollars
    'default_account_size': 10000,  # Default account size for percentage calculations
}


def get_risk_parameters(user_id=None):
    """
    Get user-specific risk parameters or defaults.
    You can enhance this to pull from user settings in the future.
    """
    # For now, return defaults. Later you can pull from user settings
    return {
        'risk_per_trade': ANALYTICS_CONFIG['default_risk_per_trade'],
        'account_size': ANALYTICS_CONFIG['default_account_size']
    }


@bp.route('/view/<int:model_id>')
@login_required
def view_model_detail(model_id):
    """
    Detailed analytics page for a specific trading model.
    Shows comprehensive performance metrics, risk analysis, and trading statistics
    based on Random's (Matt Mickey) methodology.
    """
    # Get the trading model
    model = TradingModel.query.filter_by(
        id=model_id,
        user_id=current_user.id if not current_user.has_role('admin') else None
    ).first_or_404()

    # Get all trades for this model
    trades_query = Trade.query.filter_by(
        trading_model_id=model_id,
        user_id=current_user.id
    ).order_by(Trade.entry_timestamp.desc())

    trades = trades_query.all()

    # If no trades, show empty state
    if not trades:
        return render_template('trading_models/model_detail.html',
                               model=model,
                               trades=[],
                               analytics={},
                               has_trades=False)

    # Calculate comprehensive analytics
    risk_params = get_risk_parameters(current_user.id)
    analytics = calculate_model_analytics(trades, risk_params)

    # Prepare equity curve data
    equity_data = prepare_equity_curve_data(trades)

    # Get model-specific insights based on Random's methodology
    model_insights = generate_model_insights(model, analytics)

    return render_template('trading_models/model_detail.html',
                           model=model,
                           trades=[],  # Remove recent trades as requested
                           total_trades=len(trades),
                           analytics=analytics,
                           equity_data=json.dumps(equity_data),
                           model_insights=model_insights,
                           has_trades=True)


def calculate_model_analytics(trades, risk_params=None):
    """
    Calculate comprehensive trading model analytics based on Random's methodology.

    Args:
        trades: List of trade objects
        risk_params: Dictionary with 'risk_per_trade' and 'account_size'

    Returns:
        Dictionary with all performance, risk, and consistency metrics.
    """
    if not trades:
        return {}

    # Get risk parameters or use defaults
    if risk_params is None:
        risk_params = get_risk_parameters()

    risk_per_trade = risk_params.get('risk_per_trade', 100)
    account_size = risk_params.get('account_size', 10000)

    # Initialize data collection lists
    trade_pnls = []
    trade_returns = []  # For R-multiple calculations
    winning_trades = []
    losing_trades = []
    breakeven_trades = []
    daily_pnls = defaultdict(float)
    weekly_pnls = defaultdict(float)
    monthly_pnls = defaultdict(float)

    # Process each trade
    for trade in trades:
        pnl = float(calculate_trade_pnl(trade))
        trade_pnls.append(pnl)

        # Calculate R-multiple (assuming risk_per_trade is the initial risk)
        r_multiple = pnl / risk_per_trade if risk_per_trade > 0 else 0
        trade_returns.append(r_multiple)

        # Categorize trades
        if pnl > 0:
            winning_trades.append(pnl)
        elif pnl < 0:
            losing_trades.append(pnl)
        else:
            breakeven_trades.append(pnl)

        # Time-based aggregations
        if trade.trade_date:
            trade_date = trade.trade_date
            daily_pnls[trade_date] += pnl

            # Weekly aggregation (Monday start)
            week_start = trade_date - timedelta(days=trade_date.weekday())
            weekly_pnls[week_start] += pnl

            # Monthly aggregation
            month_key = trade_date.replace(day=1)
            monthly_pnls[month_key] += pnl

    # Basic counts
    total_trades = len(trades)
    total_wins = len(winning_trades)
    total_losses = len(losing_trades)
    total_breakevens = len(breakeven_trades)

    # Calculate basic metrics
    total_pnl = sum(trade_pnls)
    avg_win = statistics.mean(winning_trades) if winning_trades else 0
    avg_loss = statistics.mean(losing_trades) if losing_trades else 0
    avg_trade = statistics.mean(trade_pnls) if trade_pnls else 0

    # Win/Loss rates
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    loss_rate = (total_losses / total_trades * 100) if total_trades > 0 else 0

    # Profit Factor
    total_winning_amount = sum(winning_trades) if winning_trades else 0
    total_losing_amount = abs(sum(losing_trades)) if losing_trades else 1  # Avoid division by zero
    profit_factor = total_winning_amount / total_losing_amount if total_losing_amount > 0 else 0

    # Expected Value
    expected_value = avg_trade

    # R-multiple calculations
    avg_win_r = statistics.mean([r for r in trade_returns if r > 0]) if any(r > 0 for r in trade_returns) else 0
    avg_loss_r = statistics.mean([r for r in trade_returns if r < 0]) if any(r < 0 for r in trade_returns) else 0
    total_r = sum(trade_returns)

    # Standard deviation and variance
    std_dev = statistics.stdev(trade_returns) if len(trade_returns) > 1 else 0

    # Expectancy (R-expectancy)
    expectancy = statistics.mean(trade_returns) if trade_returns else 0

    # System Quality Number (SQN)
    sqn = (expectancy * math.sqrt(total_trades)) / std_dev if std_dev > 0 and total_trades > 0 else 0

    # SQN(100) - Van Tharp's adjustment for large sample sizes
    if total_trades > 100:
        sqn_100 = (expectancy / std_dev) * 10 if std_dev > 0 else 0
    else:
        sqn_100 = sqn

    # Drawdown calculations
    running_pnl = 0
    peak = 0
    drawdowns = []
    max_drawdown = 0
    current_drawdown = 0
    drawdown_durations = []
    current_dd_duration = 0

    for pnl in trade_pnls:
        running_pnl += pnl
        if running_pnl > peak:
            peak = running_pnl
            if current_dd_duration > 0:
                drawdown_durations.append(current_dd_duration)
                current_dd_duration = 0
        else:
            current_dd_duration += 1

        current_drawdown = peak - running_pnl
        if current_drawdown > max_drawdown:
            max_drawdown = current_drawdown

        if current_drawdown > 0:
            drawdowns.append(current_drawdown)

    # Add final drawdown duration if still in drawdown
    if current_dd_duration > 0:
        drawdown_durations.append(current_dd_duration)

    # Median calculations
    median_profit = statistics.median(winning_trades) if winning_trades else 0
    median_drawdown = statistics.median(drawdowns) if drawdowns else 0
    median_drawdown_duration = statistics.median(drawdown_durations) if drawdown_durations else 0
    longest_drawdown_duration = max(drawdown_durations) if drawdown_durations else 0

    # Consecutive loss tracking
    consecutive_losses = 0
    max_consecutive_losses = 0

    for pnl in trade_pnls:
        if pnl < 0:
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        else:
            consecutive_losses = 0

    # Largest win/loss
    largest_win_r = max(trade_returns) if trade_returns else 0
    largest_loss_r = min(trade_returns) if trade_returns else 0

    # Time-based calculations
    if daily_pnls:
        total_trading_days = len(daily_pnls)
        positive_days = len([pnl for pnl in daily_pnls.values() if pnl > 0])
        pct_days_positive = (positive_days / total_trading_days * 100) if total_trading_days > 0 else 0

        avg_r_per_day = total_r / total_trading_days if total_trading_days > 0 else 0

        # Weekly and monthly calculations
        avg_r_per_week = total_r / len(weekly_pnls) if weekly_pnls else 0
        avg_r_per_month = total_r / len(monthly_pnls) if monthly_pnls else 0

        # Annualized calculations (assuming 252 trading days per year)
        avg_annual_r = avg_r_per_day * 252 if avg_r_per_day else 0
    else:
        total_trading_days = 0
        pct_days_positive = 0
        avg_r_per_day = 0
        avg_r_per_week = 0
        avg_r_per_month = 0
        avg_annual_r = 0

    # Kelly Fraction calculation
    # Kelly % = (Win Rate * Avg Win - Loss Rate * Avg Loss) / Avg Win
    if avg_win > 0:
        kelly_fraction = ((win_rate / 100) * avg_win - (loss_rate / 100) * abs(avg_loss)) / avg_win * 100
    else:
        kelly_fraction = 0

    # Return on Investment
    roi = (total_pnl / account_size * 100) if account_size > 0 else 0

    # Rate of Return (custom calculation)
    ror = roi  # Simple version, you may want to annualize this

    # Maximum relative drawdown (percentage)
    max_rel_drawdown = (max_drawdown / account_size * 100) if account_size > 0 and max_drawdown > 0 else 0

    # Skewness calculation
    if len(trade_returns) > 2:
        mean_return = statistics.mean(trade_returns)
        variance = statistics.variance(trade_returns)
        if variance > 0:
            skewness = sum([(x - mean_return) ** 3 for x in trade_returns]) / (len(trade_returns) * (variance ** 1.5))
        else:
            skewness = 0
    else:
        skewness = 0

    # MFE of Equity (Maximum Favorable Excursion)
    mfe_equity = max(trade_pnls) if trade_pnls else 0

    # Streak calculations
    win_streaks = []
    loss_streaks = []
    current_win_streak = 0
    current_loss_streak = 0

    for pnl in trade_pnls:
        if pnl > 0:
            current_win_streak += 1
            if current_loss_streak > 0:
                loss_streaks.append(current_loss_streak)
                current_loss_streak = 0
        elif pnl < 0:
            current_loss_streak += 1
            if current_win_streak > 0:
                win_streaks.append(current_win_streak)
                current_win_streak = 0
        # Breakeven trades don't affect streaks

    # Add final streaks
    if current_win_streak > 0:
        win_streaks.append(current_win_streak)
    if current_loss_streak > 0:
        loss_streaks.append(current_loss_streak)

    median_profit_streak = statistics.median(win_streaks) if win_streaks else 0
    median_expense_streak = statistics.median(loss_streaks) if loss_streaks else 0

    # Risk:Reward ratio
    defined_risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    # Daily and median EV calculations
    daily_ev = expected_value  # Simplified - adjust based on trading frequency
    median_ev = statistics.median(trade_pnls) if trade_pnls else 0

    # Average loss with constant risk
    average_loss_constant_risk = avg_loss if avg_loss else 0

    # R in dollars (risk amount in dollars)
    r_in_dollars = risk_per_trade

    # Max losing trades (longest losing streak)
    max_losing_trades = max(loss_streaks) if loss_streaks else 0

    # Max losing + margin of error (add 20% buffer)
    max_losing_margin = max_losing_trades * 1.2 if max_losing_trades else 0

    # Weekly MFE (simplified)
    avg_weekly_mfe = mfe_equity / len(weekly_pnls) if weekly_pnls else 0

    # Quarterly Risk:Reward (simplified)
    quarterly_rr = defined_risk_reward

    return {
        # Basic Performance
        'total_moves': total_trades,
        'total_profitable_moves': total_wins,
        'total_expense_moves': total_losses,
        'breakevens': total_breakevens,
        'wins': total_wins,
        'losers': total_losses,
        'net_pnl': round(total_pnl, 2),
        'strike_rate': round(win_rate, 2),
        'loss_rate': round(loss_rate, 2),
        'profit_factor': round(profit_factor, 2),
        'expected_value': round(expected_value, 2),
        'median_profit': round(median_profit, 2),
        'average_profit': round(avg_win, 2),

        # R-Multiple Metrics
        'avg_win_r': round(avg_win_r, 2),
        'avg_loss_r': round(avg_loss_r, 2),
        'total_r': round(total_r, 2),
        'expectancy': round(expectancy, 4),

        # Risk Metrics
        'standard_deviation': round(std_dev, 4),
        'sqn': round(sqn, 2),
        'sqn_100': round(sqn_100, 2),
        'kelly_fraction': round(kelly_fraction, 2),
        'max_drawdown': round(max_drawdown, 2),
        'median_drawdown': round(median_drawdown, 2),
        'max_rel_drawdown': round(max_rel_drawdown, 2),
        'longest_drawdown_duration': longest_drawdown_duration,
        'median_drawdown_duration': round(median_drawdown_duration, 1),
        'mfe_equity': round(mfe_equity, 2),

        # Advanced Analytics
        'skewness_of_returns': round(skewness, 4),
        'return_on_investment': round(roi, 2),
        'ror': round(ror, 2),

        # Consecutive & Streaks
        'max_consecutive_losses': max_consecutive_losses,
        'largest_win_r': round(largest_win_r, 2),
        'largest_loss_r': round(largest_loss_r, 2),
        'median_profit_streak': round(median_profit_streak, 1),
        'median_expense_streak': round(median_expense_streak, 1),

        # Time-based Analytics
        'total_trading_days': total_trading_days,
        'pct_days_positive': round(pct_days_positive, 2),
        'avg_r_per_day': round(avg_r_per_day, 4),
        'avg_r_per_week': round(avg_r_per_week, 2),
        'avg_r_per_month': round(avg_r_per_month, 2),
        'avg_annual_r': round(avg_annual_r, 2),
        'daily_ev': round(daily_ev, 2),
        'median_ev': round(median_ev, 2),

        # Additional Metrics
        'defined_risk_reward': round(defined_risk_reward, 2),
        'average_loss_constant_risk': round(average_loss_constant_risk, 2),
        'account_size': account_size,
        'r_in_dollars': r_in_dollars,
        'max_losing_trades': max_losing_trades,
        'max_losing_margin': round(max_losing_margin, 1),
        'avg_weekly_mfe': round(avg_weekly_mfe, 2),
        'quarterly_rr': round(quarterly_rr, 2),

        # Trading frequency
        'trade_frequency': round(total_trades / total_trading_days, 2) if total_trading_days > 0 else 0,
        'weekly_consistency': round(pct_days_positive, 2),  # Simplified metric
    }


def prepare_equity_curve_data(trades):
    """
    Prepare equity curve data for chart visualization.
    Based on Random's emphasis on equity curve analysis.
    """
    if not trades:
        return {'labels': [], 'values': []}

    # Sort trades by entry timestamp
    sorted_trades = sorted(trades, key=lambda t: t.entry_timestamp if t.entry_timestamp else datetime.min)

    labels = []
    values = []
    running_pnl = 0

    for i, trade in enumerate(sorted_trades):
        pnl = float(calculate_trade_pnl(trade))
        running_pnl += pnl

        # Create label from trade date
        if trade.entry_timestamp:
            label = trade.entry_timestamp.strftime('%m/%d')
        elif trade.trade_date:
            label = trade.trade_date.strftime('%m/%d')
        else:
            label = f"Trade {i+1}"

        labels.append(label)
        values.append(round(running_pnl, 2))

    return {
        'labels': labels,
        'values': values
    }


def generate_model_insights(model, analytics):
    """
    Generate model-specific insights based on Random's (Matt Mickey) methodology.
    Provides actionable feedback for improving the trading model.
    """
    insights = {
        'strengths': [],
        'areas_for_improvement': [],
        'random_methodology_notes': [],
        'recommended_actions': []
    }

    if not analytics:
        return insights

    # Strike Rate Analysis
    strike_rate = analytics.get('strike_rate', 0)
    if strike_rate >= 60:
        insights['strengths'].append(f"Excellent strike rate of {strike_rate}% - well above Random's typical targets")
    elif strike_rate >= 45:
        insights['strengths'].append(f"Solid strike rate of {strike_rate}% - within acceptable range for trending strategies")
    else:
        insights['areas_for_improvement'].append(f"Strike rate of {strike_rate}% needs improvement - review entry criteria")

    # Profit Factor Analysis
    profit_factor = analytics.get('profit_factor', 0)
    if profit_factor >= 2.0:
        insights['strengths'].append(f"Outstanding profit factor of {profit_factor:.2f} - excellent risk/reward management")
    elif profit_factor >= 1.5:
        insights['strengths'].append(f"Good profit factor of {profit_factor:.2f} - model is profitable")
    elif profit_factor >= 1.2:
        insights['areas_for_improvement'].append(f"Marginal profit factor of {profit_factor:.2f} - tighten stop losses or improve targets")
    else:
        insights['areas_for_improvement'].append(f"Poor profit factor of {profit_factor:.2f} - fundamental review needed")

    # Consistency Analysis
    weekly_consistency = analytics.get('weekly_consistency', 0)
    if weekly_consistency >= 70:
        insights['strengths'].append(f"Excellent weekly consistency at {weekly_consistency}%")
    elif weekly_consistency >= 50:
        insights['areas_for_improvement'].append(f"Weekly consistency of {weekly_consistency}% could be improved")
    else:
        insights['areas_for_improvement'].append(f"Poor weekly consistency at {weekly_consistency}% - review model activation criteria")

    # Kelly Fraction Analysis
    kelly_fraction = analytics.get('kelly_fraction', 0)
    if kelly_fraction >= 15:
        insights['strengths'].append(f"High optimal risk of {kelly_fraction}% suggests strong edge")
        insights['recommended_actions'].append("Consider increasing position size based on Kelly criterion")
    elif kelly_fraction >= 5:
        insights['random_methodology_notes'].append(f"Moderate optimal risk of {kelly_fraction}% - suitable for consistent allocation")
    else:
        insights['areas_for_improvement'].append(f"Low optimal risk of {kelly_fraction}% - model needs refinement before scaling")

    # Drawdown Analysis
    max_drawdown = analytics.get('max_drawdown', 0)
    if max_drawdown <= 200:
        insights['strengths'].append(f"Excellent drawdown control at ${max_drawdown:.0f}")
    elif max_drawdown <= 500:
        insights['random_methodology_notes'].append(f"Acceptable drawdown of ${max_drawdown:.0f} - monitor closely")
    else:
        insights['areas_for_improvement'].append(f"High drawdown of ${max_drawdown:.0f} - review risk management rules")

    # Model-Specific Insights (based on model name)
    model_name = model.name.lower()
    if '0930' in model_name or 'snap' in model_name:
        insights['random_methodology_notes'].append("9:30 models should focus on quick scalps with tight risk management")
        if analytics.get('trade_frequency', 0) > 5:
            insights['areas_for_improvement'].append("9:30 trades happening too frequently - be more selective")

    elif 'hod' in model_name or 'lod' in model_name:
        insights['random_methodology_notes'].append("HOD/LOD models require patience for proper structural setups")
        if analytics.get('trade_frequency', 0) > 2:
            insights['areas_for_improvement'].append("HOD/LOD taking too many trades - be more selective")

    elif 'p12' in model_name:
        insights['random_methodology_notes'].append("P12 models should align with daily bias and session behavior")
        insights['recommended_actions'].append("Review P12 scenario classification accuracy")

    # Overall Recommendations
    if analytics.get('total_moves', 0) < 30:
        insights['recommended_actions'].append("Gather more trade data for statistically significant analysis")

    total_pnl = analytics.get('net_pnl', 0)
    if total_pnl > 0:
        insights['recommended_actions'].append("Consider transitioning to live trading or increasing position size")
    else:
        insights['recommended_actions'].append("Focus on back-testing and paper trading until consistent profitability")

    return insights