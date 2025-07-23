# app/blueprints/portfolio_bp.py
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta, date
from decimal import Decimal
import json

from app.models import (
    Trade, TradingModel, Instrument, EntryPoint, ExitPoint,
    DailyJournal, P12Scenario, db
)


# Define helper functions for calculations since the utils functions expect different parameters
def calculate_trade_pnl_from_trade(trade):
    """Calculate P&L from a Trade object using the Trade model's built-in method."""
    try:
        # Use the Trade model's built-in P&L calculation
        if hasattr(trade, 'gross_pnl'):
            return float(trade.gross_pnl or 0)
        elif hasattr(trade, 'pnl'):
            return float(trade.pnl or 0)
        elif trade.entry_price and trade.exit_price and trade.quantity:
            # Fallback calculation
            entry = float(trade.entry_price)
            exit_price = float(trade.exit_price)
            quantity = float(trade.quantity)
            direction = trade.direction.lower()

            if direction == 'long':
                pnl = (exit_price - entry) * quantity
            elif direction == 'short':
                pnl = (entry - exit_price) * quantity
            else:
                pnl = 0.0
            return round(pnl, 2)
        else:
            return 0.0
    except Exception as e:
        current_app.logger.error(f"Error calculating P&L for trade {trade.id}: {e}")
        return 0.0


def calculate_risk_reward_from_trade(trade):
    """Calculate risk/reward ratio from a Trade object."""
    try:
        # Use the Trade model's built-in risk/reward calculation
        if hasattr(trade, 'risk_reward_ratio'):
            return trade.risk_reward_ratio or 0
        elif trade.entry_price and trade.initial_stop_loss and trade.terminus_target:
            entry = float(trade.entry_price)
            stop = float(trade.initial_stop_loss)
            target = float(trade.terminus_target)

            risk = abs(entry - stop)
            reward = abs(target - entry)

            if risk > 0:
                return round(reward / risk, 2)
        return 0.0
    except Exception as e:
        current_app.logger.error(f"Error calculating risk/reward for trade {trade.id}: {e}")
        return 0.0


# Try to import Discord decorators, but make them optional for now
try:
    from app.utils.discord_decorators import require_discord_permission, require_discord_access_level

    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False


    # Create dummy decorators if Discord isn't available
    def require_discord_permission(permission):
        def decorator(f):
            return f

        return decorator


    def require_discord_access_level(level):
        def decorator(f):
            return f

        return decorator

# Create blueprint for portfolio analytics
portfolio_bp = Blueprint('portfolio', __name__, url_prefix='/portfolio')


@portfolio_bp.route('/analytics')
@login_required
def portfolio_analytics():
    """Main portfolio analytics dashboard page."""
    return render_template('portfolio/analytics.html',
                           title='Portfolio Analytics - Random\'s Trading Journal')


@portfolio_bp.route('/api/metrics')
@login_required
def get_portfolio_metrics():
    """API endpoint to get portfolio performance metrics."""
    try:
        # Get date range from query parameters
        days = request.args.get('days', 30, type=int)
        start_date = datetime.now() - timedelta(days=days)

        # Get trading model filter
        model_filter = request.args.get('model', 'all')
        instrument_filter = request.args.get('instrument', 'all')
        classification_filter = request.args.get('classification', 'all')

        # Base query for user's trades
        trades_query = Trade.query.filter(
            Trade.user_id == current_user.id,
            Trade.entry_time >= start_date
        )

        # Apply filters if joins are available
        try:
            if model_filter != 'all':
                trades_query = trades_query.join(TradingModel).filter(
                    TradingModel.name == model_filter
                )
        except Exception:
            # Skip filter if join fails
            pass

        try:
            if instrument_filter != 'all':
                trades_query = trades_query.join(Instrument).filter(
                    Instrument.symbol == instrument_filter
                )
        except Exception:
            # Skip filter if join fails
            pass

        if classification_filter != 'all':
            trades_query = trades_query.filter(Trade.classification == classification_filter)

        trades = trades_query.all()

        # Calculate metrics
        total_trades = len(trades)

        if total_trades == 0:
            return jsonify({
                'totalPnL': 0,
                'winRate': 0,
                'totalTrades': 0,
                'avgRiskReward': 0,
                'totalWins': 0,
                'totalLosses': 0,
                'avgWin': 0,
                'avgLoss': 0,
                'largestWin': 0,
                'largestLoss': 0,
                'profitFactor': 0
            })

        # Calculate P&L for each trade
        pnl_values = []
        risk_reward_ratios = []

        for trade in trades:
            pnl = calculate_trade_pnl_from_trade(trade)
            pnl_values.append(pnl)

            rr = calculate_risk_reward_from_trade(trade)
            if rr and rr > 0:
                risk_reward_ratios.append(rr)

        total_pnl = sum(pnl_values)
        winning_trades = [pnl for pnl in pnl_values if pnl > 0]
        losing_trades = [pnl for pnl in pnl_values if pnl < 0]

        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        avg_risk_reward = sum(risk_reward_ratios) / len(risk_reward_ratios) if risk_reward_ratios else 0

        # Additional metrics
        avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0
        largest_win = max(winning_trades) if winning_trades else 0
        largest_loss = min(losing_trades) if losing_trades else 0

        gross_profit = sum(winning_trades)
        gross_loss = abs(sum(losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        return jsonify({
            'totalPnL': round(total_pnl, 2),
            'winRate': round(win_rate, 1),
            'totalTrades': total_trades,
            'avgRiskReward': round(avg_risk_reward, 2),
            'totalWins': len(winning_trades),
            'totalLosses': len(losing_trades),
            'avgWin': round(avg_win, 2),
            'avgLoss': round(avg_loss, 2),
            'largestWin': round(largest_win, 2),
            'largestLoss': round(largest_loss, 2),
            'profitFactor': round(profit_factor, 2)
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching portfolio metrics: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch portfolio metrics'}), 500


@portfolio_bp.route('/api/trades')
@login_required
def get_portfolio_trades():
    """API endpoint to get trade data for the portfolio table."""
    try:
        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)

        # Date range
        days = request.args.get('days', 30, type=int)
        start_date = datetime.now() - timedelta(days=days)

        # Filters
        model_filter = request.args.get('model', 'all')
        instrument_filter = request.args.get('instrument', 'all')
        classification_filter = request.args.get('classification', 'all')

        # Base query
        trades_query = Trade.query.filter(
            Trade.user_id == current_user.id,
            Trade.entry_time >= start_date
        )

        # Apply filters with error handling
        try:
            if model_filter != 'all':
                trades_query = trades_query.join(TradingModel).filter(TradingModel.name == model_filter)
        except Exception:
            pass

        try:
            if instrument_filter != 'all':
                trades_query = trades_query.join(Instrument).filter(Instrument.symbol == instrument_filter)
        except Exception:
            pass

        if classification_filter != 'all':
            trades_query = trades_query.filter(Trade.classification == classification_filter)

        # Order by entry time (most recent first)
        trades_query = trades_query.order_by(desc(Trade.entry_time))

        # Paginate
        trades_paginated = trades_query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        # Format trade data
        trades_data = []
        for trade in trades_paginated.items:
            pnl = calculate_trade_pnl_from_trade(trade)
            rr = calculate_risk_reward_from_trade(trade)

            # Safe attribute access
            model_name = getattr(trade.trading_model, 'name', 'Unknown') if hasattr(trade,
                                                                                    'trading_model') and trade.trading_model else 'Unknown'
            instrument_symbol = getattr(trade.instrument, 'symbol', 'Unknown') if hasattr(trade,
                                                                                          'instrument') and trade.instrument else 'Unknown'

            trades_data.append({
                'id': trade.id,
                'date': trade.entry_time.strftime('%Y-%m-%d') if trade.entry_time else 'N/A',
                'time': trade.entry_time.strftime('%H:%M') if trade.entry_time else 'N/A',
                'model': model_name,
                'instrument': instrument_symbol,
                'classification': trade.classification or 'N/A',
                'direction': trade.direction or 'N/A',
                'quantity': float(trade.quantity) if trade.quantity else 0,
                'entry_price': float(trade.entry_price) if trade.entry_price else 0,
                'exit_price': float(trade.exit_price) if trade.exit_price else 0,
                'pnl': pnl,
                'risk_reward': f"1:{rr:.1f}" if rr else "N/A",
                'status': trade.status or 'Unknown',
                'notes': trade.notes[:50] + '...' if trade.notes and len(trade.notes) > 50 else (trade.notes or '')
            })

        return jsonify({
            'trades': trades_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': trades_paginated.total,
                'pages': trades_paginated.pages,
                'has_next': trades_paginated.has_next,
                'has_prev': trades_paginated.has_prev
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching portfolio trades: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch portfolio trades'}), 500


@portfolio_bp.route('/api/chart-data')
@login_required
def get_chart_data():
    """API endpoint to get chart data for portfolio visualization."""
    try:
        # Get date range
        days = request.args.get('days', 30, type=int)
        start_date = datetime.now() - timedelta(days=days)

        # Get trades for the period
        trades = Trade.query.filter(
            Trade.user_id == current_user.id,
            Trade.entry_time >= start_date
        ).order_by(Trade.entry_time).all()

        # Calculate cumulative P&L over time
        cumulative_pnl = 0
        pnl_data = []
        labels = []

        # Group trades by date
        daily_pnl = {}
        for trade in trades:
            if trade.entry_time:
                trade_date = trade.entry_time.date()
                pnl = calculate_trade_pnl_from_trade(trade)

                if trade_date not in daily_pnl:
                    daily_pnl[trade_date] = 0
                daily_pnl[trade_date] += pnl

        # Build cumulative data
        for trade_date in sorted(daily_pnl.keys()):
            cumulative_pnl += daily_pnl[trade_date]
            labels.append(trade_date.strftime('%b %d'))
            pnl_data.append(round(cumulative_pnl, 2))

        # Performance by trading model
        model_performance = {}
        for trade in trades:
            model_name = getattr(trade.trading_model, 'name', 'Unknown') if hasattr(trade,
                                                                                    'trading_model') and trade.trading_model else 'Unknown'
            pnl = calculate_trade_pnl_from_trade(trade)

            if model_name not in model_performance:
                model_performance[model_name] = 0
            model_performance[model_name] += pnl

        return jsonify({
            'cumulative_pnl': {
                'labels': labels,
                'data': pnl_data
            },
            'model_performance': {
                'labels': list(model_performance.keys()),
                'data': [round(pnl, 2) for pnl in model_performance.values()]
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching chart data: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch chart data'}), 500


@portfolio_bp.route('/api/instruments')
@login_required
def get_available_instruments():
    """API endpoint to get available instruments for filtering."""
    try:
        # Get instruments that have been traded by this user
        instruments_subquery = db.session.query(Trade.instrument_id).filter(
            Trade.user_id == current_user.id
        ).distinct().subquery()

        instruments = Instrument.query.filter(
            Instrument.id.in_(db.session.query(instruments_subquery.c.instrument_id))
        ).all()

        instruments_data = [
            {
                'symbol': inst.symbol,
                'name': getattr(inst, 'name', inst.symbol),
                'exchange': getattr(inst, 'exchange', 'Unknown'),
                'asset_class': getattr(inst, 'asset_class', 'Unknown')
            }
            for inst in instruments
        ]

        return jsonify(instruments_data)

    except Exception as e:
        current_app.logger.error(f"Error fetching instruments: {e}", exc_info=True)
        return jsonify([])  # Return empty array on error


@portfolio_bp.route('/api/trading-models')
@login_required
def get_available_trading_models():
    """API endpoint to get available trading models for filtering."""
    try:
        models = TradingModel.query.filter(
            TradingModel.user_id == current_user.id
        ).all()

        models_data = [
            {
                'id': model.id,
                'name': model.name,
                'description': getattr(model, 'description', ''),
                'is_active': getattr(model, 'is_active', True)
            }
            for model in models
        ]

        return jsonify(models_data)

    except Exception as e:
        current_app.logger.error(f"Error fetching trading models: {e}", exc_info=True)
        return jsonify([])  # Return empty array on error