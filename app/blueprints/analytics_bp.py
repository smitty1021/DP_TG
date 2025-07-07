# Replace app/blueprints/analytics_bp.py with this simplified version

from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import TagUsageStats, Tag, Trade

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


@analytics_bp.route('/tag-usage')
@login_required
def tag_usage_analytics():
    """Display tag usage analytics with corrected counts"""

    # Get most used tags (simpler approach)
    most_used_stats = TagUsageStats.get_user_most_used_tags(current_user.id, limit=20)

    # For each tag stat, get the actual trade count
    most_used_with_counts = []
    for stat in most_used_stats:
        trade_count = (Trade.query
                       .filter(Trade.user_id == current_user.id)
                       .filter(Trade.tags.contains(stat.tag))
                       .count())
        most_used_with_counts.append((stat, trade_count))

    # Get recently used tags (simpler approach)
    recently_used_stats = TagUsageStats.get_recently_used_tags(current_user.id, days=30, limit=15)

    # For each tag stat, get the actual trade count
    recently_used_with_counts = []
    for stat in recently_used_stats:
        trade_count = (Trade.query
                       .filter(Trade.user_id == current_user.id)
                       .filter(Trade.tags.contains(stat.tag))
                       .count())
        recently_used_with_counts.append((stat, trade_count))

    # Get tag distribution by category (usage count, not trade count)
    category_stats = (db.session.query(
        Tag.category,
        db.func.sum(TagUsageStats.usage_count).label('total_usage')
    ).join(TagUsageStats)
                      .filter(TagUsageStats.user_id == current_user.id)
                      .group_by(Tag.category)
                      .all())

    return render_template('analytics/tag_usage.html',
                           title='Tag Usage Analytics',
                           most_used=most_used_with_counts,
                           recently_used=recently_used_with_counts,
                           category_stats=category_stats)


@analytics_bp.route('/api/tag-usage-data')
@login_required
def tag_usage_data():
    """API endpoint for tag usage charts"""
    most_used = TagUsageStats.get_user_most_used_tags(current_user.id, limit=10)

    data = {
        'labels': [stat.tag.name for stat in most_used],
        'usage_counts': [stat.usage_count for stat in most_used],
        'last_used': [stat.last_used.isoformat() if stat.last_used else None for stat in most_used]
    }

    return jsonify(data)


@analytics_bp.route('/api/tag-trades')
@login_required
def tag_trades_data():
    """API endpoint to get trades associated with a specific tag"""
    tag_id = request.args.get('tag_id', type=int)

    if not tag_id:
        return jsonify({'error': 'Tag ID is required'}), 400

    try:
        # Get the tag and verify it belongs to the user or is a default tag
        tag = Tag.query.filter(
            Tag.id == tag_id,
            db.or_(
                Tag.user_id == current_user.id,
                Tag.is_default == True
            )
        ).first()

        if not tag:
            return jsonify({'error': 'Tag not found'}), 404

        # Get all trades that have this tag and belong to the current user
        trades = (Trade.query
                  .filter(Trade.user_id == current_user.id)
                  .filter(Trade.tags.contains(tag))
                  .order_by(Trade.trade_date.desc())
                  .limit(50)  # Limit to most recent 50 trades
                  .all())

        # Format trades data for JSON response
        trades_data = []
        for trade in trades:
            trades_data.append({
                'id': trade.id,
                'trade_date': trade.trade_date.strftime('%Y-%m-%d'),
                'instrument': trade.instrument,
                'direction': trade.direction,
                'gross_pnl': float(trade.gross_pnl) if trade.gross_pnl is not None else None,
                'total_contracts': trade.total_contracts_entered,
                'avg_entry_price': float(trade.average_entry_price) if trade.average_entry_price else None,
                'avg_exit_price': float(trade.average_exit_price) if trade.average_exit_price else None,
                'how_closed': trade.how_closed,
                'trading_model': trade.trading_model.name if trade.trading_model else None
            })

        return jsonify({
            'tag_name': tag.name,
            'tag_category': tag.category.value,
            'trades_count': len(trades_data),
            'trades': trades_data
        })

    except Exception as e:
        current_app.logger.error(f"Error fetching trades for tag {tag_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500