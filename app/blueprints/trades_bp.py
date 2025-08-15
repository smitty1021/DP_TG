
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app, Response, abort, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from flask_wtf.csrf import generate_csrf
import os

import statistics
import uuid
import csv
import io
import json
import numpy as np
import pandas as pd
import shutil
from datetime import datetime, time as py_time
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app, Response)
from flask_login import login_required, current_user
from datetime import date as py_date, timedelta
from datetime import date as py_date, datetime as py_datetime, time as py_time
from datetime import datetime
import matplotlib
matplotlib.use('Agg') # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
from matplotlib.patches import Rectangle
import tempfile
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, PageBreak, NextPageTemplate, Image)
    from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
    from reportlab.platypus.frames import Frame
    from reportlab.lib import colors
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF

    SVG_AVAILABLE = True
except ImportError:
    SVG_AVAILABLE = False

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, \
    NextPageTemplate
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.lib import colors

from app.extensions import db
from app.models import (Trade, EntryPoint, ExitPoint, TradingModel, NewsEventItem,
                       TradeImage, Instrument, Tag, TagCategory, TagUsageStats)
from app.forms import TradeForm, EntryPointForm, ExitPointForm, TradeFilterForm, ImportTradesForm
from app.utils import (_parse_form_float, _parse_form_int, _parse_form_time,
                       get_news_event_options, record_activity)
from datetime import datetime, time as py_time, date as py_date
from app.models import Trade, TradingModel, Tag, Instrument, EntryPoint, ExitPoint
from app.extensions import db

trades_bp = Blueprint('trades', __name__,
                      template_folder='../templates/trades',
                      url_prefix='/trades')

def get_instrument_point_values():

    try:
        return Instrument.get_instrument_point_values()
    except Exception as e:
        current_app.logger.warning(f"Failed to get instrument point values from database: {e}")

        return {
            'NQ': 20.0,
            'ES': 50.0,
            'YM': 5.0,
            'MNQ': 2.0,
            'MES': 5.0,
            'MYM': 0.5,
            'Other': 1.0
        }

def _is_allowed_image(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config.get('ALLOWED_IMAGE_EXTENSIONS',
                                                                     {'png', 'jpg', 'jpeg', 'gif'})

def _populate_tags_choices(form):
    from app.models import Tag, TagCategory
    from flask_login import current_user

    all_tags = Tag.query.filter(
        db.or_(
            Tag.is_default == True,
            Tag.user_id == current_user.id
        )
    ).filter(Tag.is_active == True).order_by(Tag.category, Tag.name).all()

    if not all_tags:
        form.tags.choices = []
        return form

    grouped_tags = {category: [] for category in TagCategory}

    for tag in all_tags:
        if tag.category in grouped_tags:
            # Convert tag.id to string and include color_category
            grouped_tags[tag.category].append((
                str(tag.id),
                tag.name,
                tag.color_category or 'neutral'
            ))

    choices = []
    for category_enum, tags_list in grouped_tags.items():
        if tags_list:
            choices.append((category_enum.value, tags_list))

    form.tags.choices = choices
    return form


def _get_tags_by_category():
    """Helper function to get tags organized by category for modals"""
    from app.models import Tag, TagCategory
    from flask_login import current_user
    
    all_tags = Tag.query.filter(
        db.or_(
            Tag.is_default == True,
            Tag.user_id == current_user.id
        )
    ).filter(Tag.is_active == True).order_by(Tag.category, Tag.color_category, Tag.name).all()
    
    tags_by_category = {}
    for category in TagCategory:
        category_tags = [tag for tag in all_tags if tag.category == category]
        if category_tags:  # Only include categories with tags
            # Group tags by impact type within each category for template compatibility
            impact_groups = {
                'neutral': [tag for tag in category_tags if tag.color_category == 'neutral'],
                'good': [tag for tag in category_tags if tag.color_category == 'good'],
                'bad': [tag for tag in category_tags if tag.color_category == 'bad']
            }
            
            # Create flat list with impact type organization (neutral, positive, negative)
            organized_tags = []
            if impact_groups['neutral']:
                organized_tags.extend(impact_groups['neutral'])
            if impact_groups['good']:
                organized_tags.extend(impact_groups['good'])
            if impact_groups['bad']:
                organized_tags.extend(impact_groups['bad'])
            
            tags_by_category[category.value] = {
                'tags': organized_tags,
                'impact_groups': impact_groups
            }
    
    return tags_by_category


def _populate_trade_form_choices(form):
    form.trading_model_id.choices = [(0, 'Select Model')] + \
                                    [(tm.id, tm.name) for tm in
                                     TradingModel.query.filter_by(user_id=current_user.id, is_active=True).order_by(
                                         TradingModel.name).all()]
    if hasattr(form, 'news_event_select'):
        form.news_event_select.choices = [('', '-- None --')] + [(event, event) for event in get_news_event_options() if
                                                                 event and event.lower() != 'none']
    return form


def _apply_trade_filters(query, filter_form=None, request_args=None):
    """Apply comprehensive trade filtering based on form data and request args.
    
    Args:
        query: Base SQLAlchemy query for trades
        filter_form: TradeFilterForm instance (optional)  
        request_args: Request arguments dict (optional)
    
    Returns:
        Filtered query and filter status dictionary
    """
    if request_args is None:
        request_args = request.args
    
    if filter_form is None:
        filter_form = TradeFilterForm(request_args)
        _populate_filter_form_choices(filter_form)
    
    # Track active filters for export labeling
    active_filters = {}
    
    # Date range filters
    if filter_form.start_date.data:
        query = query.filter(Trade.trade_date >= filter_form.start_date.data)
        active_filters['start_date'] = filter_form.start_date.data
    if filter_form.end_date.data:
        query = query.filter(Trade.trade_date <= filter_form.end_date.data)
        active_filters['end_date'] = filter_form.end_date.data

    # Instrument filtering - handle both legacy and new instrument system
    if filter_form.instrument.data:
        # Try to filter by instrument_id first (new system)
        if filter_form.instrument.data.isdigit():
            instrument_id = int(filter_form.instrument.data)
            query = query.filter(Trade.instrument_id == instrument_id)
        else:
            # Fallback to symbol matching (legacy system)
            query = query.filter(Trade.instrument_legacy == filter_form.instrument.data)
        active_filters['instrument'] = filter_form.instrument.data

    # Direction filter
    if filter_form.direction.data:
        query = query.filter(Trade.direction == filter_form.direction.data)
        active_filters['direction'] = filter_form.direction.data

    # Trading model filter
    if filter_form.trading_model_id.data and filter_form.trading_model_id.data != 0:
        query = query.filter(Trade.trading_model_id == filter_form.trading_model_id.data)
        active_filters['trading_model_id'] = filter_form.trading_model_id.data

    # How closed filter
    how_closed_filter = request_args.get('how_closed')
    if how_closed_filter:
        query = query.filter(Trade.how_closed == how_closed_filter)
        active_filters['how_closed'] = how_closed_filter

    # P&L filter
    pnl_filter = request_args.get('pnl_filter')
    if pnl_filter:
        if pnl_filter == 'winners':
            query = query.filter(Trade.pnl > 0)
        elif pnl_filter == 'losers':
            query = query.filter(Trade.pnl < 0)
        elif pnl_filter == 'breakeven':
            query = query.filter(Trade.pnl == 0)
        active_filters['pnl_filter'] = pnl_filter

    # Min/Max P&L filters
    min_pnl = request_args.get('min_pnl')
    max_pnl = request_args.get('max_pnl')
    if min_pnl:
        try:
            min_val = float(min_pnl)
            query = query.filter(Trade.pnl >= min_val)
            active_filters['min_pnl'] = min_val
        except ValueError:
            pass
    if max_pnl:
        try:
            max_val = float(max_pnl)
            query = query.filter(Trade.pnl <= max_val)
            active_filters['max_pnl'] = max_val
        except ValueError:
            pass

    # Min/Max contracts filters
    min_contracts = request_args.get('min_contracts')
    max_contracts = request_args.get('max_contracts')
    if min_contracts:
        try:
            min_val = int(min_contracts)
            # Using subquery for total_contracts_entered property
            subquery = db.session.query(
                EntryPoint.trade_id,
                db.func.sum(EntryPoint.contracts).label('total_contracts')
            ).group_by(EntryPoint.trade_id).subquery()
            
            query = query.join(subquery, Trade.id == subquery.c.trade_id)\
                        .filter(subquery.c.total_contracts >= min_val)
            active_filters['min_contracts'] = min_val
        except ValueError:
            pass
    if max_contracts:
        try:
            max_val = int(max_contracts)
            # Using subquery for total_contracts_entered property
            subquery = db.session.query(
                EntryPoint.trade_id,
                db.func.sum(EntryPoint.contracts).label('total_contracts')
            ).group_by(EntryPoint.trade_id).subquery()
            
            query = query.join(subquery, Trade.id == subquery.c.trade_id)\
                        .filter(subquery.c.total_contracts <= max_val)
            active_filters['max_contracts'] = max_val
        except ValueError:
            pass

    # DCA only filter
    dca_only = request_args.get('dca_only')
    if dca_only == 'true':
        # Filter trades with multiple entries (DCA)
        subquery = db.session.query(
            EntryPoint.trade_id,
            db.func.count(EntryPoint.id).label('entry_count')
        ).group_by(EntryPoint.trade_id).subquery()
        
        query = query.join(subquery, Trade.id == subquery.c.trade_id)\
                    .filter(subquery.c.entry_count > 1)
        active_filters['dca_only'] = True

    # Tags filter (handle multiple tag selection)
    selected_tags = request_args.get('selected_tags')
    if selected_tags:
        tag_ids = [int(tid) for tid in selected_tags.split(',') if tid.isdigit()]
        if tag_ids:
            # Filter for trades that have ALL selected tags (AND logic)
            for tag_id in tag_ids:
                query = query.filter(Trade.tags.any(Tag.id == tag_id))
            active_filters['selected_tags'] = tag_ids

    return query, active_filters


def _populate_filter_form_choices(filter_form):
    from app.models import Tag, TagCategory, Instrument

    # Populate trading models
    filter_form.trading_model_id.choices = [(0, 'All Models')] + \
                                           [(tm.id, tm.name) for tm in
                                            TradingModel.query.filter_by(user_id=current_user.id,
                                                                         is_active=True).order_by(
                                                TradingModel.name).all()]

    # FIXED: Populate instruments properly with IDs
    try:
        # Get instruments that are actually used in trades
        used_instruments = db.session.query(Trade.instrument_id, Trade.instrument_legacy).filter(
            Trade.user_id == current_user.id
        ).distinct().all()

        instrument_choices = [('', 'All Instruments')]

        # Add instruments from the new system (instrument_id)
        for trade_instrument_id, trade_legacy in used_instruments:
            if trade_instrument_id:
                instrument = Instrument.query.get(trade_instrument_id)
                if instrument:
                    instrument_choices.append((str(instrument.id), f"{instrument.symbol} ({instrument.name})"))
            elif trade_legacy:
                # Add legacy instruments
                instrument_choices.append((trade_legacy, trade_legacy))

        # Remove duplicates and sort
        seen = set()
        unique_choices = []
        for choice in instrument_choices:
            if choice[0] not in seen:
                seen.add(choice[0])
                unique_choices.append(choice)

        filter_form.instrument.choices = sorted(unique_choices, key=lambda x: x[1] if x[1] != 'All Instruments' else '')
    except Exception as e:
        print(f"Error populating instruments: {e}")
        # Fallback to basic choices
        filter_form.instrument.choices = [
            ('', 'All Instruments'),
            ('NQ', 'NQ'),
            ('ES', 'ES'),
            ('YM', 'YM')
        ]

    # Get all available tags (default + user's custom tags)
    all_tags = Tag.query.filter(
        db.or_(
            Tag.is_default == True,
            Tag.user_id == current_user.id
        )
    ).filter(Tag.is_active == True).order_by(Tag.category, Tag.name).all()

    # Group tags by category using the same logic as _populate_tags_choices
    grouped_tags = {category: [] for category in TagCategory}

    for tag in all_tags:
        if tag.category in grouped_tags:
            # Convert tag.id to string and include color_category
            grouped_tags[tag.category].append((
                str(tag.id),
                tag.name,
                tag.color_category or 'neutral'
            ))

    # Convert to the format expected by the template (same as add_trade.html)
    categorized_choices = []
    for category_enum, tags_list in grouped_tags.items():
        if tags_list:  # Only include categories that have tags
            categorized_choices.append((category_enum.value, tags_list))

    # For the simple choices (backward compatibility)
    filter_form.tags.choices = [('', 'All Tags')] + [(str(tag.id), tag.name) for tag in all_tags]

    return filter_form, categorized_choices


@trades_bp.route('/', methods=['GET'])
@login_required
def view_trades_list():
    from flask_wtf.csrf import generate_csrf

    filter_form = TradeFilterForm(request.args)
    filter_form, categorized_tags = _populate_filter_form_choices(filter_form)

    query = Trade.query.filter_by(user_id=current_user.id)

    # Get ALL user trades for KPI calculations (not just filtered ones)
    all_user_trades = Trade.query.filter_by(user_id=current_user.id).all()

    # Calculate KPI data
    kpi_data = {
        'total_trades': len(all_user_trades),
        'profitable_trades': len([t for t in all_user_trades if t.pnl and t.pnl > 0]),
        'losing_trades': len([t for t in all_user_trades if t.pnl and t.pnl < 0]),
        'breakeven_trades': len([t for t in all_user_trades if t.pnl and t.pnl == 0]),
        'cumulative_pnl': sum([t.pnl for t in all_user_trades if t.pnl is not None]),
        'strike_rate': 0
    }

    # Calculate strike rate
    trades_with_pnl = [t for t in all_user_trades if t.pnl is not None]
    if trades_with_pnl:
        kpi_data['strike_rate'] = (kpi_data['profitable_trades'] / len(trades_with_pnl)) * 100
    
    # Calculate best model by strike rate (using all trades, not just paginated)
    model_performance = {}
    for trade in all_user_trades:
        if trade.trading_model and trade.pnl is not None:
            model_name = trade.trading_model.name
            if model_name not in model_performance:
                model_performance[model_name] = {'total_trades': 0, 'winning_trades': 0}
            model_performance[model_name]['total_trades'] += 1
            if trade.pnl > 0:
                model_performance[model_name]['winning_trades'] += 1
    
    # Find best model by strike rate
    best_model = None
    if model_performance:
        best_strike_rate = -1
        for model_name, stats in model_performance.items():
            if stats['total_trades'] > 0:
                strike_rate = (stats['winning_trades'] / stats['total_trades']) * 100
                if strike_rate > best_strike_rate:
                    best_model = model_name
                    best_strike_rate = strike_rate
    
    kpi_data['best_model'] = best_model

    # Apply filters
    if filter_form.start_date.data:
        query = query.filter(Trade.trade_date >= filter_form.start_date.data)
    if filter_form.end_date.data:
        query = query.filter(Trade.trade_date <= filter_form.end_date.data)

    # FIXED: Instrument filtering - handle both legacy and new instrument system
    if filter_form.instrument.data:
        # Try to filter by instrument_id first (new system)
        if filter_form.instrument.data.isdigit():
            instrument_id = int(filter_form.instrument.data)
            query = query.filter(Trade.instrument_id == instrument_id)
        else:
            # Fallback to symbol matching (legacy system)
            query = query.filter(Trade.instrument_legacy == filter_form.instrument.data)

    if filter_form.direction.data:
        query = query.filter(Trade.direction == filter_form.direction.data)

    if filter_form.trading_model_id.data and filter_form.trading_model_id.data != 0:
        query = query.filter(Trade.trading_model_id == filter_form.trading_model_id.data)

    # Handle how_closed filter (from request.args since it's not in the form)

    how_closed_filter = request.args.get('how_closed')
    if how_closed_filter:
        print(f"DEBUG: Filtering by how_closed = '{how_closed_filter}'")

        # Let's see what values actually exist in the database
        existing_how_closed_values = db.session.query(Trade.how_closed).filter(
            Trade.user_id == current_user.id
        ).distinct().all()
        print(f"DEBUG: Existing how_closed values in database:")
        for value in existing_how_closed_values:
            print(f"  - '{value[0]}'")

        query = query.filter(Trade.how_closed == how_closed_filter)

        # Check how many trades match after this filter
        count_after_filter = query.count()
        print(f"DEBUG: Trades matching how_closed filter: {count_after_filter}")

    # Handle P&L filter - now using the stored pnl column
    pnl_filter = request.args.get('pnl_filter')
    if pnl_filter:
        if pnl_filter == 'winners':
            query = query.filter(Trade.pnl > 0)
        elif pnl_filter == 'losers':
            query = query.filter(Trade.pnl < 0)
        elif pnl_filter == 'breakeven':
            query = query.filter(Trade.pnl == 0)

    # Handle DCA filter
    is_dca_filter = request.args.get('is_dca')
    if is_dca_filter:
        if is_dca_filter == 'true':
            query = query.filter(Trade.is_dca == True)
        elif is_dca_filter == 'false':
            query = query.filter(Trade.is_dca == False)

    # Handle min/max P&L filters
    min_pnl = request.args.get('min_pnl')
    if min_pnl:
        try:
            min_pnl_value = float(min_pnl)
            query = query.filter(Trade.pnl >= min_pnl_value)
        except (ValueError, TypeError):
            pass  # Ignore invalid values
    
    max_pnl = request.args.get('max_pnl')
    if max_pnl:
        try:
            max_pnl_value = float(max_pnl)
            query = query.filter(Trade.pnl <= max_pnl_value)
        except (ValueError, TypeError):
            pass  # Ignore invalid values

    # Handle min/max contracts filters
    min_contracts = request.args.get('min_contracts')
    max_contracts = request.args.get('max_contracts')
    
    if min_contracts or max_contracts:
        try:
            from app.models import EntryPoint
            # Use subquery to sum contracts from entry points
            subquery = db.session.query(
                EntryPoint.trade_id,
                db.func.sum(EntryPoint.contracts).label('total_contracts')
            ).group_by(EntryPoint.trade_id).subquery()
            
            query = query.join(subquery, Trade.id == subquery.c.trade_id)
            
            if min_contracts:
                min_contracts_value = int(min_contracts)
                query = query.filter(subquery.c.total_contracts >= min_contracts_value)
            
            if max_contracts:
                max_contracts_value = int(max_contracts)
                query = query.filter(subquery.c.total_contracts <= max_contracts_value)
                
        except (ValueError, TypeError):
            pass

    # Handle min rating filter
    min_rating = request.args.get('min_rating')
    if min_rating:
        try:
            min_rating_value = int(min_rating)
            # Calculate average rating and filter
            query = query.filter(
                ((Trade.preparation_rating + Trade.rules_rating + Trade.management_rating + 
                  Trade.target_rating + Trade.entry_rating) / 5.0) >= min_rating_value
            )
        except (ValueError, TypeError):
            pass

    # Handle tags filter - support multiple tags with AND logic
    selected_tags = request.args.getlist('tags')  # Get list of selected tag IDs
    if selected_tags and any(tag.strip() for tag in selected_tags if tag):  # Check if any non-empty tags
        # Handle comma-separated values and individual tags
        all_tag_ids = []
        for tag_param in selected_tags:
            if tag_param and tag_param.strip():
                # Split comma-separated values and add to list
                tag_ids_in_param = [t.strip() for t in tag_param.split(',') if t.strip()]
                all_tag_ids.extend(tag_ids_in_param)
        
        # Filter to only valid integer IDs
        valid_tag_ids = []
        for tag_id in all_tag_ids:
            try:
                valid_tag_ids.append(int(tag_id))
            except (ValueError, TypeError):
                continue

        if valid_tag_ids:
            # Use AND logic - show trades that have ALL of the selected tags
            for tag_id in valid_tag_ids:
                query = query.filter(Trade.tags.any(Tag.id == tag_id))

    selected_tag_details = []
    if selected_tags:
        # Handle comma-separated values for display
        all_tag_ids = []
        for tag_param in selected_tags:
            if tag_param and tag_param.strip():
                tag_ids_in_param = [t.strip() for t in tag_param.split(',') if t.strip()]
                all_tag_ids.extend(tag_ids_in_param)
        
        valid_tag_ids = []
        for tag_id in all_tag_ids:
            try:
                valid_tag_ids.append(int(tag_id))
            except (ValueError, TypeError):
                continue
                
        if valid_tag_ids:
            tags_for_display = Tag.query.filter(Tag.id.in_(valid_tag_ids)).all()
            selected_tag_details = [(tag.id, tag.name, tag.color_category or 'neutral') for tag in tags_for_display]

    # Debug logging
    print(f"Filter form data: {filter_form.data}")
    print(f"Request args: {request.args}")

    # Continue with rest of the function (sorting, pagination, etc.)
    sort_field = request.args.get('sort', 'date')
    sort_order = request.args.get('order', 'desc')
    sort_reverse = sort_order == 'desc'

    query = query.join(TradingModel, Trade.trading_model_id == TradingModel.id, isouter=True)

    if sort_field == 'date':
        order_clauses = (Trade.trade_date.desc(), Trade.id.desc()) if sort_reverse else (Trade.trade_date.asc(),
                                                                                         Trade.id.asc())
        query = query.order_by(*order_clauses)
    elif sort_field == 'instrument':
        query = query.join(Instrument, Trade.instrument_id == Instrument.id, isouter=True)
        order_clauses = (Instrument.symbol.desc(), Trade.trade_date.desc()) if sort_reverse else (
            Instrument.symbol.asc(), Trade.trade_date.desc())
        query = query.order_by(*order_clauses)
    elif sort_field == 'model':
        order_clauses = (TradingModel.name.desc(), Trade.trade_date.desc()) if sort_reverse else (
            TradingModel.name.asc(), Trade.trade_date.desc())
        query = query.order_by(*order_clauses)
    elif sort_field == 'direction':
        order_clauses = (Trade.direction.desc(), Trade.trade_date.desc()) if sort_reverse else (Trade.direction.asc(),
                                                                                                Trade.trade_date.desc())
        query = query.order_by(*order_clauses)
    elif sort_field == 'how_closed':
        order_clauses = (Trade.how_closed.desc().nullslast(), Trade.trade_date.desc()) if sort_reverse else (
            Trade.how_closed.asc().nullsfirst(), Trade.trade_date.desc())
        query = query.order_by(*order_clauses)
    elif sort_field == 'pnl':
        order_clauses = (Trade.pnl.desc().nullslast(), Trade.trade_date.desc()) if sort_reverse else (
            Trade.pnl.asc().nullsfirst(), Trade.trade_date.desc())
        query = query.order_by(*order_clauses)
    else:
        query = query.order_by(Trade.trade_date.desc(), Trade.id.desc())

    # Pagination with dynamic page size
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    if per_page not in [25, 50, 100, 250]:
        per_page = 25
    trades_pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # In-memory sorting for calculated properties (P&L, Ratings, etc.)
    property_sort_fields = ['contracts', 'entry_time', 'entry', 'exit', 'avg_rating', 'time_in_trade']
    if sort_field in property_sort_fields:

        def _calculate_avg_rating(trade):
            ratings = [r for r in
                       [trade.preparation_rating, trade.rules_rating, trade.management_rating, trade.target_rating,
                        trade.entry_rating] if r is not None]
            return sum(ratings) / len(ratings) if ratings else None

        key_func = None
        if sort_field == 'pnl':
            key_func = lambda t: t.pnl if t.pnl is not None else -float('inf')
        elif sort_field == 'contracts':
            key_func = lambda t: t.total_contracts_entered if t.total_contracts_entered is not None else -1
        elif sort_field == 'entry_time':
            key_func = lambda \
                    t: t.entries.first().entry_time if t.entries.first() and t.entries.first().entry_time else py_time.min
        elif sort_field == 'entry':
            key_func = lambda t: t.average_entry_price if t.average_entry_price is not None else -float('inf')
        elif sort_field == 'exit':
            key_func = lambda t: t.average_exit_price if t.average_exit_price is not None else -float('inf')
        elif sort_field == 'avg_rating':
            key_func = lambda t: _calculate_avg_rating(t) if _calculate_avg_rating(t) is not None else -1
        elif sort_field == 'time_in_trade':
            def _calculate_time_in_trade(trade):
                if trade.exits.count() > 0 and trade.entries.count() > 0:
                    first_entry = trade.entries.order_by(EntryPoint.entry_time.asc()).first()
                    last_exit = trade.exits.order_by(ExitPoint.exit_time.desc()).first()

                    if first_entry and last_exit and first_entry.entry_time and last_exit.exit_time:
                        from datetime import datetime
                        entry_datetime = datetime.combine(trade.trade_date, first_entry.entry_time)
                        exit_datetime = datetime.combine(trade.trade_date, last_exit.exit_time)
                        return (exit_datetime - entry_datetime).total_seconds()
                return 0

            key_func = _calculate_time_in_trade
        if key_func:
            trades_pagination.items = sorted(trades_pagination.items, key=key_func, reverse=sort_reverse)



    # Set the title
    title = "Trades List"
    trades_on_page = trades_pagination.items

    return render_template("trades/view_trades_list.html",
                           title=title,
                           trades=trades_on_page,
                           pagination=trades_pagination,
                           filter_form=filter_form,
                           categorized_tags=categorized_tags,
                           selected_tag_details=selected_tag_details,
                           kpi_data=kpi_data,
                           csrf_token=generate_csrf())

# --- ADD TRADE ---
# Also fix the add_trade function in trades_bp.py
# Replace the relevant part of add_trade function:

@trades_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_trade():
    form = TradeForm()

    _populate_tags_choices(form)
    _populate_trade_form_choices(form)

    if request.method == 'GET':
        if not form.entries.entries:
            form.entries.append_entry(None)
        if not form.exits.entries:
            form.exits.append_entry(None)

    instrument_point_values = get_instrument_point_values()

    if form.validate_on_submit():
        try:
            # FIXED: Handle instrument properly
            instrument_id = form.instrument.data
            if not instrument_id:
                flash('Please select an instrument.', 'danger')
                return render_template('trades/add_trade.html',
                                       title='Log New Trade',
                                       form=form,
                                       instrument_point_values=instrument_point_values,
                                       default_trade_date=py_date.today().strftime('%Y-%m-%d'),
                                       tags_by_category=_get_tags_by_category())

            # Get the instrument object
            instrument_obj = Instrument.query.get(int(instrument_id))
            if not instrument_obj:
                flash('Invalid instrument selected.', 'danger')
                return render_template('trades/add_trade.html',
                                       title='Log New Trade',
                                       form=form,
                                       instrument_point_values=instrument_point_values,
                                       default_trade_date=py_date.today().strftime('%Y-%m-%d'),
                                       tags_by_category=_get_tags_by_category())

            # Create new trade
            new_trade = Trade(user_id=current_user.id)

            # FIXED: Set instrument fields properly
            new_trade.instrument_id = instrument_obj.id
            new_trade.instrument_legacy = instrument_obj.symbol
            new_trade.point_value = instrument_obj.point_value

            # Set other fields
            new_trade.trade_date = form.trade_date.data
            new_trade.direction = form.direction.data
            new_trade.initial_stop_loss = _parse_form_float(form.initial_stop_loss.data)
            new_trade.terminus_target = _parse_form_float(form.terminus_target.data)
            new_trade.is_dca = form.is_dca.data
            new_trade.mae_price = _parse_form_float(form.mae_price.data)
            new_trade.mfe_price = _parse_form_float(form.mfe_price.data)
            new_trade.how_closed = form.how_closed.data if form.how_closed.data else None
            new_trade.rules_rating = form.rules_rating.data
            new_trade.management_rating = form.management_rating.data
            new_trade.target_rating = form.target_rating.data
            new_trade.entry_rating = form.entry_rating.data
            new_trade.preparation_rating = form.preparation_rating.data
            new_trade.trade_notes = form.trade_notes.data
            new_trade.psych_scored_highest = form.psych_scored_highest.data
            new_trade.psych_scored_lowest = form.psych_scored_lowest.data
            new_trade.overall_analysis_notes = form.overall_analysis_notes.data
            new_trade.trade_management_notes = form.trade_management_notes.data
            new_trade.errors_notes = form.errors_notes.data
            new_trade.improvements_notes = form.improvements_notes.data
            new_trade.screenshot_link = form.screenshot_link.data
            new_trade.trading_model_id = form.trading_model_id.data if form.trading_model_id.data and form.trading_model_id.data != 0 else None
            new_trade.news_event = form.news_event_select.data if form.news_event_select.data else None

            db.session.add(new_trade)
            db.session.flush()  # Get the trade ID

            # Add entries
            for entry_form in form.entries:
                if (entry_form.entry_time.data and entry_form.contracts.data and entry_form.entry_price.data):
                    new_entry = EntryPoint(
                        trade_id=new_trade.id,
                        entry_time=entry_form.entry_time.data,
                        contracts=entry_form.contracts.data,
                        entry_price=entry_form.entry_price.data
                    )
                    db.session.add(new_entry)

            # Add exits
            for exit_form in form.exits:
                if (exit_form.exit_time.data and exit_form.contracts.data and exit_form.exit_price.data):
                    new_exit = ExitPoint(
                        trade_id=new_trade.id,
                        exit_time=exit_form.exit_time.data,
                        contracts=exit_form.contracts.data,
                        exit_price=exit_form.exit_price.data
                    )
                    db.session.add(new_exit)

            new_trade.calculate_and_store_pnl()

            # Add tags
            if form.tags.data:
                for tag_id in form.tags.data:
                    tag = Tag.query.get(int(tag_id))
                    if tag and (tag.user_id == current_user.id or tag.is_default):
                        new_trade.tags.append(tag)

            # Handle image uploads
            if form.trade_images.data:
                for file in form.trade_images.data:
                    if file and _is_allowed_image(file.filename):
                        filename = secure_filename(file.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        
                        # Get file stats before saving
                        file.seek(0, 2)  # Seek to end of file
                        filesize = file.tell()
                        file.seek(0)  # Reset to beginning
                        
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(file_path)
                        
                        new_image = TradeImage(
                            trade_id=new_trade.id,
                            user_id=current_user.id,
                            filename=filename,
                            filepath=unique_filename,
                            filesize=filesize,
                            mime_type=file.mimetype
                        )
                        db.session.add(new_image)

            db.session.commit()
            record_activity(current_user.id, 'trade_logged',
                            f'Trade logged for {instrument_obj.symbol} on {new_trade.trade_date}')
            flash(f'Trade for {instrument_obj.symbol} logged successfully!', 'success')
            return redirect(url_for('trades.view_trades_list'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error logging new trade for user {current_user.username}: {e}", exc_info=True)
            flash(f'An error occurred while logging the trade: {str(e)}', 'danger')

    elif request.method == 'POST':
        flash('Please correct the errors in the form and try again.', 'warning')
        if not form.entries.entries:
            form.entries.append_entry(None)
        if not form.exits.entries and len(form.exits.data) == 0:
            form.exits.append_entry(None)

    return render_template('trades/add_trade.html',
                           title='Log New Trade',
                           form=form,
                           instrument_point_values=instrument_point_values,
                           default_trade_date=py_date.today().strftime('%Y-%m-%d'),
                           tags_by_category=_get_tags_by_category())

# --- VIEW TRADE DETAIL ---
@trades_bp.route('/<int:trade_id>/view')
@login_required
def view_trade_detail(trade_id):
    trade = db.get_or_404(Trade, trade_id)
    if trade.user_id != current_user.id:
        abort(403)
    
    # Get trade images explicitly due to relationship issue
    trade_images = TradeImage.query.filter_by(trade_id=trade.id).all()
    
    return render_template('trades/view_trade_detail.html', title="Trade Details", trade=trade, trade_images=trade_images)


# --- EDIT TRADE ---
# Fixed edit_trade function with correct entry/exit handling
@trades_bp.route('/<int:trade_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_trade(trade_id):
    from app.models import Instrument

    trade_to_edit = db.get_or_404(Trade, trade_id)
    if trade_to_edit.user_id != current_user.id:
        abort(403)

    form = TradeForm(obj=trade_to_edit)
    _populate_trade_form_choices(form)
    _populate_tags_choices(form)

    if request.method == 'GET':
        # FIXED: Properly set instrument field to the ID, not the symbol
        if trade_to_edit.instrument_id:
            form.instrument.data = str(trade_to_edit.instrument_id)
        elif trade_to_edit.instrument_legacy:
            # Find instrument by symbol and set the ID
            instrument = Instrument.query.filter_by(
                symbol=trade_to_edit.instrument_legacy.upper(),
                is_active=True
            ).first()
            if instrument:
                form.instrument.data = str(instrument.id)

        # Populate entries
        while len(form.entries) > 0:
            form.entries.pop_entry()
        for entry in trade_to_edit.entries.all():
            entry_form_data = {
                'id': entry.id, 'entry_time': entry.entry_time,
                'contracts': entry.contracts, 'entry_price': entry.entry_price
            }
            form.entries.append_entry(data=entry_form_data)
        if not form.entries.entries:
            form.entries.append_entry(None)

        # Populate exits
        while len(form.exits) > 0:
            form.exits.pop_entry()
        for exit_item in trade_to_edit.exits.all():
            exit_form_data = {
                'id': exit_item.id, 'exit_time': exit_item.exit_time,
                'contracts': exit_item.contracts, 'exit_price': exit_item.exit_price
            }
            form.exits.append_entry(data=exit_form_data)
        if not form.exits.entries:
            form.exits.append_entry(None)

        # Populate tags
        if trade_to_edit.tags:
            form.tags.data = [str(tag.id) for tag in trade_to_edit.tags]

    if form.validate_on_submit():
        try:
            # FIXED: Handle instrument assignment properly
            instrument_id = form.instrument.data
            if instrument_id:
                # Set the instrument_id directly
                trade_to_edit.instrument_id = int(instrument_id)
                # Also update the legacy field with the symbol for consistency
                instrument = Instrument.query.get(int(instrument_id))
                if instrument:
                    trade_to_edit.instrument_legacy = instrument.symbol
                    trade_to_edit.point_value = instrument.point_value

            # Rest of the form processing
            trade_to_edit.trade_date = form.trade_date.data
            trade_to_edit.direction = form.direction.data
            trade_to_edit.initial_stop_loss = _parse_form_float(form.initial_stop_loss.data)
            trade_to_edit.terminus_target = _parse_form_float(form.terminus_target.data)
            trade_to_edit.is_dca = form.is_dca.data
            trade_to_edit.mae_price = _parse_form_float(form.mae_price.data)
            trade_to_edit.mfe_price = _parse_form_float(form.mfe_price.data)
            trade_to_edit.trading_model_id = form.trading_model_id.data if form.trading_model_id.data and form.trading_model_id.data != 0 else None
            trade_to_edit.news_event = form.news_event_select.data if form.news_event_select.data else None
            trade_to_edit.how_closed = form.how_closed.data if form.how_closed.data else None
            trade_to_edit.rules_rating = form.rules_rating.data
            trade_to_edit.management_rating = form.management_rating.data
            trade_to_edit.target_rating = form.target_rating.data
            trade_to_edit.entry_rating = form.entry_rating.data
            trade_to_edit.preparation_rating = form.preparation_rating.data
            trade_to_edit.trade_notes = form.trade_notes.data
            trade_to_edit.psych_scored_highest = form.psych_scored_highest.data
            trade_to_edit.psych_scored_lowest = form.psych_scored_lowest.data
            trade_to_edit.overall_analysis_notes = form.overall_analysis_notes.data
            trade_to_edit.trade_management_notes = form.trade_management_notes.data
            trade_to_edit.errors_notes = form.errors_notes.data
            trade_to_edit.improvements_notes = form.improvements_notes.data
            trade_to_edit.screenshot_link = form.screenshot_link.data

            # FIXED: Handle entries with proper data access
            existing_entry_ids = {entry.id for entry in trade_to_edit.entries.all()}
            form_entry_ids = set()

            for entry_form in form.entries:
                # Check if this entry has an ID (existing entry)
                entry_id = getattr(entry_form, 'id', None)
                if entry_id and hasattr(entry_id, 'data') and entry_id.data:
                    form_entry_ids.add(entry_id.data)
                    existing_entry = EntryPoint.query.get(entry_id.data)
                    if existing_entry and existing_entry.trade_id == trade_to_edit.id:
                        existing_entry.entry_time = entry_form.entry_time.data
                        existing_entry.contracts = entry_form.contracts.data
                        existing_entry.entry_price = entry_form.entry_price.data
                else:
                    # New entry
                    if (hasattr(entry_form, 'entry_time') and entry_form.entry_time.data and
                            hasattr(entry_form, 'contracts') and entry_form.contracts.data and
                            hasattr(entry_form, 'entry_price') and entry_form.entry_price.data):
                        new_entry = EntryPoint(
                            trade_id=trade_to_edit.id,
                            entry_time=entry_form.entry_time.data,
                            contracts=entry_form.contracts.data,
                            entry_price=entry_form.entry_price.data
                        )
                        db.session.add(new_entry)

            # Remove deleted entries
            for entry_id in existing_entry_ids - form_entry_ids:
                entry_to_delete = EntryPoint.query.get(entry_id)
                if entry_to_delete:
                    db.session.delete(entry_to_delete)

            # FIXED: Handle exits with proper data access
            existing_exit_ids = {exit.id for exit in trade_to_edit.exits.all()}
            form_exit_ids = set()

            for exit_form in form.exits:
                # Check if this exit has an ID (existing exit)
                exit_id = getattr(exit_form, 'id', None)
                if exit_id and hasattr(exit_id, 'data') and exit_id.data:
                    form_exit_ids.add(exit_id.data)
                    existing_exit = ExitPoint.query.get(exit_id.data)
                    if existing_exit and existing_exit.trade_id == trade_to_edit.id:
                        existing_exit.exit_time = exit_form.exit_time.data
                        existing_exit.contracts = exit_form.contracts.data
                        existing_exit.exit_price = exit_form.exit_price.data
                else:
                    # New exit
                    if (hasattr(exit_form, 'exit_time') and exit_form.exit_time.data and
                            hasattr(exit_form, 'contracts') and exit_form.contracts.data and
                            hasattr(exit_form, 'exit_price') and exit_form.exit_price.data):
                        new_exit = ExitPoint(
                            trade_id=trade_to_edit.id,
                            exit_time=exit_form.exit_time.data,
                            contracts=exit_form.contracts.data,
                            exit_price=exit_form.exit_price.data
                        )
                        db.session.add(new_exit)

            # Remove deleted exits
            for exit_id in existing_exit_ids - form_exit_ids:
                exit_to_delete = ExitPoint.query.get(exit_id)
                if exit_to_delete:
                    db.session.delete(exit_to_delete)

            trade_to_edit.calculate_and_store_pnl()

            # Handle tags
            trade_to_edit.tags.clear()
            if form.tags.data:
                for tag_id in form.tags.data:
                    tag = Tag.query.get(int(tag_id))
                    if tag and (tag.user_id == current_user.id or tag.is_default):
                        trade_to_edit.tags.append(tag)

            # Handle images (existing code for image deletion)
            for key in request.form.keys():
                if key.startswith('delete_image_'):
                    image_id = int(key.split('_')[-1])
                    image_to_delete = TradeImage.query.get(image_id)
                    if image_to_delete and image_to_delete.trade_id == trade_to_edit.id:
                        try:
                            os.remove(image_to_delete.full_disk_path)
                        except OSError:
                            pass
                        db.session.delete(image_to_delete)

            # Handle new images
            if form.trade_images.data:
                for file in form.trade_images.data:
                    if file and _is_allowed_image(file.filename):
                        filename = secure_filename(file.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        
                        # Get file stats before saving
                        file.seek(0, 2)  # Seek to end of file
                        filesize = file.tell()
                        file.seek(0)  # Reset to beginning
                        
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(file_path)
                        
                        new_image = TradeImage(
                            trade_id=trade_to_edit.id,
                            user_id=current_user.id,
                            filename=filename,
                            filepath=unique_filename,
                            filesize=filesize,
                            mime_type=file.mimetype
                        )
                        db.session.add(new_image)

            db.session.commit()
            flash('Trade updated successfully!', 'success')
            return redirect(url_for('trades.view_trade_detail', trade_id=trade_to_edit.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error editing trade {trade_id}: {e}", exc_info=True)
            flash(f'An error occurred while updating the trade: {str(e)}', 'danger')

    # Get instrument point values for JavaScript calculations
    instrument_point_values = Instrument.get_instrument_point_values()

    # Get tags by category for the modal (same as add_trade)
    tags_by_category = _get_tags_by_category()
    
    # Get trade images explicitly due to relationship issue
    trade_images = TradeImage.query.filter_by(trade_id=trade_to_edit.id).all()
    
    return render_template('trades/add_trade.html',
                           title="Edit Trade",
                           form=form,
                           trade=trade_to_edit,
                           trade_images=trade_images,
                           tags_by_category=tags_by_category,
                           instrument_point_values=instrument_point_values)


# --- DELETE TRADE (Single) ---
@trades_bp.route('/<int:trade_id>/delete', methods=['POST'])
@login_required
def delete_trade(trade_id):
    trade_to_delete = db.get_or_404(Trade, trade_id)
    if trade_to_delete.user_id != current_user.id:
        abort(403)
    try:
        for img in trade_to_delete.images:
            if img.filepath:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], img.filepath))
                except OSError:
                    current_app.logger.warning(f"Could not delete image file: {img.filepath}")
        db.session.delete(trade_to_delete)  # Cascades should handle entries, exits, images in DB
        db.session.commit()
        TagUsageStats.cleanup_unused_stats(current_user.id)
        # Check if this was a custom modal delete
        if request.form.get('custom_modal_delete') == 'true':
            flash('Trade deleted successfully using custom modal!', 'success')
        else:
            flash('Trade deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting trade {trade_id}: {e}", exc_info=True)
        flash('Error deleting trade. Please try again.', 'danger')
    return redirect(url_for('trades.view_trades_list'))


@trades_bp.route('/get_tags_modal_content', methods=['GET'])
@login_required
def get_tags_modal_content():
    """Return updated modal content for tag selection after tag creation"""
    try:
        tags_by_category = _get_tags_by_category()
        
        # Render just the modal body content
        modal_content = ""
        for category_name, category_data in tags_by_category.items():
            # Calculate total tags in category
            total_tags = len(category_data['tags'])
            
            modal_content += f'''
            <div class="tag-category-section">
                <div class="tag-category-header">
                    <span><i class="fas fa-folder me-2"></i>{category_name}</span>
                    <span class="badge bg-secondary">{total_tags} tags</span>
                </div>
                <div class="tag-category-body">'''
            
            impact_groups = category_data['impact_groups']
            
            # Render tags in single wrapped row format (neutral, then good, then bad)
            modal_content += '''
                    <div class="tag-impact-group">
                        <div class="tag-impact-body">'''
            
            # Add neutral tags
            for tag in impact_groups['neutral']:
                color_class = f"tag-{tag.color_category}" if tag.color_category else "tag-neutral"
                modal_content += f'''
                        <div class="tag-item {color_class} tag-selectable" data-tag-id="{tag.id}" data-tag-name="{tag.name}" data-tag-color="{tag.color_category or 'neutral'}" role="button" tabindex="0" style="cursor: pointer; user-select: none;">
                            <span class="tag-name">{tag.name}</span>
                        </div>'''
            
            # Add good tags
            for tag in impact_groups['good']:
                color_class = f"tag-{tag.color_category}" if tag.color_category else "tag-neutral"
                modal_content += f'''
                        <div class="tag-item {color_class} tag-selectable" data-tag-id="{tag.id}" data-tag-name="{tag.name}" data-tag-color="{tag.color_category or 'neutral'}" role="button" tabindex="0" style="cursor: pointer; user-select: none;">
                            <span class="tag-name">{tag.name}</span>
                        </div>'''
            
            # Add bad tags
            for tag in impact_groups['bad']:
                color_class = f"tag-{tag.color_category}" if tag.color_category else "tag-neutral"
                modal_content += f'''
                        <div class="tag-item {color_class} tag-selectable" data-tag-id="{tag.id}" data-tag-name="{tag.name}" data-tag-color="{tag.color_category or 'neutral'}" role="button" tabindex="0" style="cursor: pointer; user-select: none;">
                            <span class="tag-name">{tag.name}</span>
                        </div>'''
            
            modal_content += '''
                        </div>
                    </div>'''
            
            if total_tags == 0:
                modal_content += '<p class="text-muted fst-italic">No tags in this category yet.</p>'
            
            modal_content += '''
                </div>
            </div>'''
        
        # Add the create tag form at the bottom
        modal_content += '''
        <div class="enterprise-module mt-4" id="create-tag-form" style="display: none;">
            <div class="module-header">
                <div class="module-title">
                    <i class="fas fa-plus module-icon"></i>
                    Create Personal Tag
                </div>
                <div class="module-meta">
                    Add Custom Trade Classification
                </div>
            </div>
            <div class="module-content">
                <div class="d-flex gap-3 align-items-end">
                    <div style="min-width: 200px; max-width: 250px;">
                        <label class="form-label">Tag Name</label>
                        <input type="text" id="new-tag-name" class="form-control" placeholder="Enter tag name" maxlength="50">
                    </div>
                    <div style="min-width: 180px; max-width: 220px;">
                        <label class="form-label">Category</label>
                        <select id="new-tag-category" class="form-select">'''
        
        # Add category options
        from app.models import TagCategory
        for category in TagCategory:
            modal_content += f'<option value="{category.name}">{category.value}</option>'
        
        modal_content += '''
                        </select>
                    </div>
                    <div style="min-width: 150px; max-width: 180px;">
                        <label class="form-label">Performance Impact</label>
                        <select id="new-tag-color" class="form-select">
                            <option value="neutral">Neutral (Blue)</option>
                            <option value="good">Positive (Green)</option>
                            <option value="bad">Negative (Red)</option>
                        </select>
                    </div>
                    <div>
                        <button type="button" id="submit-new-tag" class="btn btn-success me-2">
                            <i class="fas fa-save"></i>
                        </button>
                        <button type="button" id="cancel-new-tag" class="btn btn-secondary">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>'''
        
        return modal_content
        
    except Exception as e:
        current_app.logger.error(f"Error getting tags modal content: {e}", exc_info=True)
        return '<div class="alert alert-danger">Error loading tags. Please refresh the page.</div>'


# --- BULK DELETE TRADES ---
@trades_bp.route('/bulk_delete', methods=['POST'])
@login_required
def bulk_delete_trades():
    trade_ids_to_delete = request.form.getlist('trade_ids')
    if not trade_ids_to_delete:
        flash('No trades selected for deletion.', 'warning')
        return redirect(url_for('trades.view_trades_list'))

    deleted_count = 0
    error_count = 0
    for trade_id_str in trade_ids_to_delete:
        try:
            trade_id = int(trade_id_str)
            trade = Trade.query.get(trade_id)
            if trade and trade.user_id == current_user.id:
                for img in trade.images:
                    if img.filepath:
                        try:
                            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], img.filepath))
                        except OSError:
                            pass
                db.session.delete(trade)
                deleted_count += 1
            else:
                error_count += 1
        except ValueError:
            error_count += 1
        except Exception as e:
            error_count += 1
            current_app.logger.error(f"Error during bulk delete of trade ID {trade_id_str}: {e}", exc_info=True)

    if deleted_count > 0:
        try:
            db.session.commit()
            TagUsageStats.cleanup_unused_stats(current_user.id)
            flash(f'Successfully deleted {deleted_count} trade(s).', 'success')
        except Exception as e_commit:
            db.session.rollback()
            flash('An error occurred during bulk deletion commit.', 'danger')
            current_app.logger.error(f"Error committing bulk delete: {e_commit}", exc_info=True)
    if error_count > 0:
        flash(f'Could not delete {error_count} selected item(s) due to errors or permissions.', 'warning')

    return redirect(url_for('trades.view_trades_list'))


# --- EXPORT TRADES ---
@trades_bp.route('/export_csv', methods=['GET'])
@login_required
def export_trades_csv():
    """Export trades to CSV format - filtered data if filters active, complete dataset if not."""
    try:
        # Create and populate filter form properly  
        filter_form = TradeFilterForm(request.args, meta={'csrf': False})
        filter_form, categorized_tags = _populate_filter_form_choices(filter_form)
        
        # Create base query for current user
        query = Trade.query.filter_by(user_id=current_user.id)
        
        # Apply filters directly (same logic as main view)
        active_filters = {}
        if filter_form.start_date.data:
            query = query.filter(Trade.trade_date >= filter_form.start_date.data)
            active_filters['start_date'] = filter_form.start_date.data
        if filter_form.end_date.data:
            query = query.filter(Trade.trade_date <= filter_form.end_date.data)
            active_filters['end_date'] = filter_form.end_date.data
        if filter_form.instrument.data:
            if filter_form.instrument.data.isdigit():
                instrument_id = int(filter_form.instrument.data)
                query = query.filter(Trade.instrument_id == instrument_id)
            else:
                query = query.filter(Trade.instrument_legacy == filter_form.instrument.data)
            active_filters['instrument'] = filter_form.instrument.data
        if filter_form.direction.data:
            query = query.filter(Trade.direction == filter_form.direction.data)
            active_filters['direction'] = filter_form.direction.data
        if filter_form.trading_model_id.data and filter_form.trading_model_id.data != 0:
            query = query.filter(Trade.trading_model_id == filter_form.trading_model_id.data)
            active_filters['trading_model_id'] = filter_form.trading_model_id.data
        
        # Handle additional filters from request.args
        how_closed_filter = request.args.get('how_closed')
        if how_closed_filter:
            query = query.filter(Trade.how_closed == how_closed_filter)
            active_filters['how_closed'] = how_closed_filter
        
        pnl_filter = request.args.get('pnl_filter')
        if pnl_filter:
            if pnl_filter == 'winners':
                query = query.filter(Trade.pnl > 0)
            elif pnl_filter == 'losers':
                query = query.filter(Trade.pnl < 0)
            elif pnl_filter == 'breakeven':
                query = query.filter(Trade.pnl == 0)
            active_filters['pnl_filter'] = pnl_filter
        
        # Debug: Log filter status
        current_app.logger.info(f"CSV Export - Active filters: {active_filters}")
        current_app.logger.info(f"CSV Export - Request args: {dict(request.args)}")
        
        trades_to_export = query.order_by(Trade.trade_date.asc()).all()
        current_app.logger.info(f"CSV Export - Total trades found: {len(trades_to_export)}")

        if not trades_to_export:
            flash('No trades found matching current filters to export.', 'warning')
            return redirect(url_for('trades.view_trades_list', **request.args))

        output = io.StringIO()
        writer = csv.writer(output)
        headers = [
            'ID', 'Date', 'Instrument', 'Direction', 'Point Value',
            'Total Entry Contracts', 'Avg Entry Price', 'Total Exit Contracts', 'Avg Exit Price',
            'Gross P&L', 'R-Value (Initial)', 'Dollar Risk (Initial)',
            'Initial SL', 'Terminus Target', 'MAE', 'MFE', 'How Closed',
            'Trading Model', 'Tags', 'Trade Notes', 'Overall Analysis', 'Management Notes',
            'Errors', 'Improvements', 'External Screenshot Link'
            # Detailed entries/exits would require a more complex CSV or separate export
        ]
        writer.writerow(headers)
        for trade in trades_to_export:
            writer.writerow([
                trade.id, trade.trade_date.strftime('%Y-%m-%d'), trade.instrument, trade.direction, trade.point_value,
                trade.total_contracts_entered, trade.average_entry_price,
                trade.total_contracts_exited, trade.average_exit_price,
                trade.pnl, trade.pnl_in_r, trade.dollar_risk,
                trade.initial_stop_loss, trade.terminus_target, trade.mae_price, trade.mfe_price,
                trade.how_closed, trade.trading_model.name if trade.trading_model else '',
                ', '.join([tag.name for tag in trade.tags]) if trade.tags else '', trade.trade_notes, trade.overall_analysis_notes, trade.trade_management_notes,
                trade.errors_notes, trade.improvements_notes, trade.screenshot_link
            ])
        output.seek(0)
        
        # Create filename based on filter status
        if active_filters:
            filename = "trades_export_filtered.csv"
        else:
            filename = "trades_export_complete.csv"
        
        return Response(output.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment;filename={filename}"})
    
    except Exception as e:
        current_app.logger.error(f"CSV Export failed: {e}")
        flash(f'Export failed: {str(e)}', 'danger')
        return redirect(url_for('trades.view_trades_list', **request.args))


@trades_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_trades():
    form = ImportTradesForm()
    if form.validate_on_submit():
        csv_file = form.csv_file.data
        try:
            stream = io.StringIO(csv_file.stream.read().decode("UTF-8"), newline=None)
            csv_reader = csv.DictReader(stream)

            imported_count = 0
            error_count = 0
            error_details = []

            # MODIFIED: Updated header names to match the new CSV template
            header_map = {
                'date': 'Date (Req: YYYY-MM-DD)', 'instrument': 'Instrument (Req)', 'direction': 'Direction (Req)',
                'entry_time': 'Entry Time {i} (Req: HH:MM)', 'entry_contracts': 'Entry Contracts {i} (Req)',
                'entry_price': 'Entry Price {i} (Req)',
                'exit_time': 'Exit Time {i} (Req: HH:MM)', 'exit_contracts': 'Exit Contracts {i} (Req)',
                'exit_price': 'Exit Price {i} (Req)',
                'model': 'Trading Model', 'tags': 'Tags', 'how_closed': 'How Closed', 'sl': 'Initial SL',
                'tp': 'Terminus Target', 'mae': 'MAE', 'mfe': 'MFE', 'notes': 'Trade Notes'
            }
            # For optional entries/exits, the header might not have "(Req)"
            header_map_optional = {
                'entry_time': 'Entry Time {i} (HH:MM)', 'entry_contracts': 'Entry Contracts {i}',
                'entry_price': 'Entry Price {i}',
                'exit_time': 'Exit Time {i} (HH:MM)', 'exit_contracts': 'Exit Contracts {i}',
                'exit_price': 'Exit Price {i}'
            }

            for row_num, row in enumerate(csv_reader, 1):
                try:
                    # --- 1. Validate required main trade data using new headers ---
                    trade_date_str = row.get(header_map['date'])
                    instrument = row.get(header_map['instrument'])
                    direction = row.get(header_map['direction'])

                    if not all([trade_date_str, instrument, direction]):
                        error_details.append(
                            f"Row {row_num + 1}: Missing required fields (Date, Instrument, or Direction).");
                        error_count += 1;
                        continue

                    trade_date = py_datetime.strptime(trade_date_str, '%Y-%m-%d').date()

                    # --- 2. Create the main Trade object ---
                    new_trade = Trade(user_id=current_user.id, trade_date=trade_date, instrument=instrument,
                                      direction=direction, point_value=Instrument.get_point_value(instrument))

                    # --- 3. Process Entries and Exits ---
                    entries_found = 0
                    # Look for up to 5 entries (you can increase this number)
                    for i in range(1, 6):
                        # Try both required and optional header formats
                        entry_time_hdr = header_map['entry_time'].format(i=i) if i == 1 else header_map_optional[
                            'entry_time'].format(i=i)
                        entry_contracts_hdr = header_map['entry_contracts'].format(i=i) if i == 1 else \
                        header_map_optional['entry_contracts'].format(i=i)
                        entry_price_hdr = header_map['entry_price'].format(i=i) if i == 1 else header_map_optional[
                            'entry_price'].format(i=i)

                        entry_time_str = row.get(entry_time_hdr) or row.get(
                            header_map_optional['entry_time'].format(i=i))
                        entry_contracts_str = row.get(entry_contracts_hdr) or row.get(
                            header_map_optional['entry_contracts'].format(i=i))
                        entry_price_str = row.get(entry_price_hdr) or row.get(
                            header_map_optional['entry_price'].format(i=i))

                        if entry_time_str and entry_contracts_str and entry_price_str:
                            new_trade.entries.append(EntryPoint(
                                entry_time=py_datetime.strptime(entry_time_str, '%H:%M').time(),
                                contracts=_parse_form_int(entry_contracts_str),
                                entry_price=_parse_form_float(entry_price_str)
                            ))
                            entries_found += 1

                    if entries_found == 0:
                        error_details.append(
                            f"Row {row_num + 1}: At least one full entry (Time, Contracts, Price) is required.");
                        error_count += 1;
                        continue

                    # Process Exit 1 (Required)
                    exit_time_1_str = row.get(header_map['exit_time'].format(i=1))
                    exit_contracts_1_str = row.get(header_map['exit_contracts'].format(i=1))
                    exit_price_1_str = row.get(header_map['exit_price'].format(i=1))

                    if not all([exit_time_1_str, exit_contracts_1_str, exit_price_1_str]):
                        error_details.append(f"Row {row_num + 1}: Missing required fields for first exit.");
                        error_count += 1;
                        continue

                    new_trade.exits.append(ExitPoint(
                        exit_time=py_datetime.strptime(exit_time_1_str, '%H:%M').time(),
                        contracts=_parse_form_int(exit_contracts_1_str),
                        exit_price=_parse_form_float(exit_price_1_str)
                    ))

                    # Look for optional additional exits
                    for i in range(2, 6):
                        exit_time_hdr = header_map_optional['exit_time'].format(i=i)
                        exit_contracts_hdr = header_map_optional['exit_contracts'].format(i=i)
                        exit_price_hdr = header_map_optional['exit_price'].format(i=i)

                        exit_time_str = row.get(exit_time_hdr)
                        exit_contracts_str = row.get(exit_contracts_hdr)
                        exit_price_str = row.get(exit_price_hdr)

                        if exit_time_str and exit_contracts_str and exit_price_str:
                            new_trade.exits.append(ExitPoint(
                                exit_time=py_datetime.strptime(exit_time_str, '%H:%M').time(),
                                contracts=_parse_form_int(exit_contracts_str),
                                exit_price=_parse_form_float(exit_price_str)
                            ))

                    # --- 4. Populate optional main trade fields ---
                    model_name = row.get(header_map['model'])
                    if model_name:
                        model = TradingModel.query.filter_by(user_id=current_user.id, name=model_name).first()
                        if model: new_trade.trading_model_id = model.id

                    new_trade.tags = row.get(header_map['tags'])
                    new_trade.how_closed = row.get(header_map['how_closed'])
                    new_trade.initial_stop_loss = _parse_form_float(row.get(header_map['sl']))
                    new_trade.terminus_target = _parse_form_float(row.get(header_map['tp']))
                    new_trade.mae_price = _parse_form_float(row.get(header_map['mae']))
                    new_trade.mfe_price = _parse_form_float(row.get(header_map['mfe']))
                    new_trade.trade_notes = row.get(header_map['notes'])

                    db.session.add(new_trade)
                    imported_count += 1
                except (ValueError, TypeError) as ve:
                    error_details.append(
                        f"Row {row_num + 1}: Data conversion error - {ve}. Check number/date/time formats.");
                    error_count += 1
                except Exception as e_row:
                    error_details.append(f"Row {row_num + 1}: Unexpected error - {e_row}.");
                    error_count += 1

            if imported_count > 0:
                db.session.commit()
                flash(f'Successfully imported {imported_count} trades.', 'success')
            else:
                db.session.rollback()

            if error_count > 0:
                flash(f'Skipped or had errors with {error_count} rows during import.', 'danger')
            if error_details:
                for err_detail in error_details[:5]:
                    flash(err_detail, 'warning')
                if len(error_details) > 5:
                    flash(f"...and {len(error_details) - 5} more errors.", 'warning')

            return redirect(url_for('trades.view_trades_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'A critical error occurred while processing the file: {str(e)}', 'danger')
            current_app.logger.error(f"Fatal error during trade import process: {e}", exc_info=True)

    return render_template('trades/import_trades.html', title="Import Trades", form=form)


# ============================================================================
# ENTERPRISE-LEVEL EXPORT FUNCTIONALITY
# ============================================================================

@trades_bp.route('/export_excel', methods=['GET'])
@login_required
def export_trades_excel():
    """Export trades to Excel format with enterprise-level formatting."""
    try:
        # For now, create a CSV that can be opened as Excel
        # In production, you'd use openpyxl for true Excel format
        filter_form = TradeFilterForm(request.args, meta={'csrf': False})
        _populate_filter_form_choices(filter_form)

        query = Trade.query.filter_by(user_id=current_user.id)
        if filter_form.start_date.data: query = query.filter(Trade.trade_date >= filter_form.start_date.data)
        if filter_form.end_date.data: query = query.filter(Trade.trade_date <= filter_form.end_date.data)
        if filter_form.instrument.data: query = query.filter(Trade.instrument == filter_form.instrument.data)
        if filter_form.direction.data: query = query.filter(Trade.direction == filter_form.direction.data)
        if filter_form.trading_model_id.data and filter_form.trading_model_id.data != 0:
            query = query.filter(Trade.trading_model_id == filter_form.trading_model_id.data)

        trades_to_export = query.order_by(Trade.trade_date.asc()).all()

        if not trades_to_export:
            flash('No trades found matching current filters to export.', 'warning')
            return redirect(url_for('trades.view_trades_list', **request.args))

        output = io.StringIO()
        writer = csv.writer(output)
        
        # Enhanced headers for Excel export
        headers = [
            'Trade ID', 'Date', 'Day of Week', 'Instrument', 'Direction', 'Point Value',
            'Total Entry Contracts', 'Avg Entry Price', 'Total Exit Contracts', 'Avg Exit Price',
            'Gross P&L', 'R-Value', 'Dollar Risk', 'Win/Loss', 'Strike Rate Contribution',
            'Initial SL', 'Terminus Target', 'MAE', 'MFE', 'How Closed',
            'Trading Model', 'Tags', 'Trade Notes', 'Analysis Notes', 'Management Notes',
            'Errors', 'Improvements', 'Screenshot Link'
        ]
        writer.writerow(headers)
        
        for trade in trades_to_export:
            writer.writerow([
                trade.id, 
                trade.trade_date.strftime('%Y-%m-%d'), 
                trade.trade_date.strftime('%A'),
                trade.instrument, 
                trade.direction, 
                trade.point_value,
                trade.total_contracts_entered, 
                trade.average_entry_price,
                trade.total_contracts_exited, 
                trade.average_exit_price,
                trade.pnl, 
                trade.pnl_in_r, 
                trade.dollar_risk,
                'Win' if trade.pnl and trade.pnl > 0 else 'Loss' if trade.pnl and trade.pnl < 0 else 'Breakeven',
                '1' if trade.pnl and trade.pnl > 0 else '0',
                trade.initial_stop_loss, 
                trade.terminus_target, 
                trade.mae_price, 
                trade.mfe_price,
                trade.how_closed, 
                trade.trading_model.name if trade.trading_model else '',
                ', '.join([tag.name for tag in trade.tags]) if trade.tags else '', 
                trade.trade_notes, 
                trade.overall_analysis_notes, 
                trade.trade_management_notes,
                trade.errors_notes, 
                trade.improvements_notes, 
                trade.screenshot_link
            ])
        
        output.seek(0)
        filename = f"trades_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(output, mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment;filename={filename}"})

    except Exception as e:
        flash(f'Error exporting to Excel: {str(e)}', 'danger')
        return redirect(url_for('trades.view_trades_list'))


@trades_bp.route('/export_json', methods=['GET'])
@login_required
def export_trades_json():
    """Export trades to JSON format for API integration."""
    try:
        filter_form = TradeFilterForm(request.args, meta={'csrf': False})
        _populate_filter_form_choices(filter_form)

        query = Trade.query.filter_by(user_id=current_user.id)
        if filter_form.start_date.data: query = query.filter(Trade.trade_date >= filter_form.start_date.data)
        if filter_form.end_date.data: query = query.filter(Trade.trade_date <= filter_form.end_date.data)
        if filter_form.instrument.data: query = query.filter(Trade.instrument == filter_form.instrument.data)
        if filter_form.direction.data: query = query.filter(Trade.direction == filter_form.direction.data)
        if filter_form.trading_model_id.data and filter_form.trading_model_id.data != 0:
            query = query.filter(Trade.trading_model_id == filter_form.trading_model_id.data)

        trades_to_export = query.order_by(Trade.trade_date.asc()).all()

        if not trades_to_export:
            flash('No trades found matching current filters to export.', 'warning')
            return redirect(url_for('trades.view_trades_list', **request.args))

        # Build comprehensive JSON structure
        export_data = {
            'export_metadata': {
                'exported_by': current_user.username,
                'export_date': datetime.now().isoformat(),
                'total_trades': len(trades_to_export),
                'filters_applied': {
                    'start_date': filter_form.start_date.data.isoformat() if filter_form.start_date.data else None,
                    'end_date': filter_form.end_date.data.isoformat() if filter_form.end_date.data else None,
                    'instrument': filter_form.instrument.data,
                    'direction': filter_form.direction.data
                }
            },
            'trades': []
        }

        for trade in trades_to_export:
            trade_data = {
                'id': trade.id,
                'trade_date': trade.trade_date.isoformat(),
                'instrument': trade.instrument,
                'direction': trade.direction,
                'point_value': float(trade.point_value) if trade.point_value else None,
                'contracts': {
                    'total_entered': trade.total_contracts_entered,
                    'total_exited': trade.total_contracts_exited
                },
                'prices': {
                    'average_entry': float(trade.average_entry_price) if trade.average_entry_price else None,
                    'average_exit': float(trade.average_exit_price) if trade.average_exit_price else None
                },
                'performance': {
                    'gross_pnl': float(trade.pnl) if trade.pnl else None,
                    'r_value': float(trade.pnl_in_r) if trade.pnl_in_r else None,
                    'dollar_risk': float(trade.dollar_risk) if trade.dollar_risk else None,
                    'mae_price': float(trade.mae_price) if trade.mae_price else None,
                    'mfe_price': float(trade.mfe_price) if trade.mfe_price else None
                },
                'levels': {
                    'initial_stop_loss': float(trade.initial_stop_loss) if trade.initial_stop_loss else None,
                    'terminus_target': float(trade.terminus_target) if trade.terminus_target else None
                },
                'metadata': {
                    'how_closed': trade.how_closed,
                    'trading_model': trade.trading_model.name if trade.trading_model else None,
                    'tags': [tag.name for tag in trade.tags] if trade.tags else [],
                    'notes': {
                        'trade_notes': trade.trade_notes,
                        'analysis_notes': trade.overall_analysis_notes,
                        'management_notes': trade.trade_management_notes,
                        'errors_notes': trade.errors_notes,
                        'improvements_notes': trade.improvements_notes
                    },
                    'screenshot_link': trade.screenshot_link
                },
                'entries': [
                    {
                        'entry_time': entry.entry_time.isoformat() if entry.entry_time else None,
                        'contracts': entry.contracts,
                        'entry_price': float(entry.entry_price) if entry.entry_price else None
                    } for entry in trade.entry_points
                ],
                'exits': [
                    {
                        'exit_time': exit.exit_time.isoformat() if exit.exit_time else None,
                        'contracts': exit.contracts,
                        'exit_price': float(exit.exit_price) if exit.exit_price else None
                    } for exit in trade.exit_points
                ]
            }
            export_data['trades'].append(trade_data)

        json_str = json.dumps(export_data, indent=2, default=str)
        filename = f"trades_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return Response(json_str, mimetype="application/json",
                        headers={"Content-Disposition": f"attachment;filename={filename}"})

    except Exception as e:
        flash(f'Error exporting to JSON: {str(e)}', 'danger')
        return redirect(url_for('trades.view_trades_list'))


@trades_bp.route('/export_tax_report', methods=['GET'])
@login_required
def export_tax_report():
    """Export tax-compliant trading report."""
    try:
        # Get all trades for current tax year (or allow date range)
        current_year = datetime.now().year
        start_date = py_date(current_year, 1, 1)
        end_date = py_date(current_year, 12, 31)
        
        trades = Trade.query.filter_by(user_id=current_user.id).filter(
            Trade.trade_date >= start_date,
            Trade.trade_date <= end_date
        ).order_by(Trade.trade_date.asc()).all()

        if not trades:
            flash(f'No trades found for tax year {current_year}.', 'warning')
            return redirect(url_for('trades.view_trades_list'))

        output = io.StringIO()
        writer = csv.writer(output)
        
        # Tax report headers
        headers = [
            'Trade Date', 'Security', 'Quantity', 'Price', 'Proceeds', 'Cost Basis', 
            'Gain/Loss', 'Short/Long Term', 'Days Held', 'Trade Type'
        ]
        writer.writerow(headers)
        
        for trade in trades:
            # All futures trades are typically Section 1256 contracts (60/40 rule)
            writer.writerow([
                trade.trade_date.strftime('%Y-%m-%d'),
                trade.instrument,
                trade.total_contracts_entered,
                trade.average_entry_price or 0,
                (trade.average_exit_price or 0) * (trade.total_contracts_exited or 0) * (trade.point_value or 1),
                (trade.average_entry_price or 0) * (trade.total_contracts_entered or 0) * (trade.point_value or 1),
                trade.pnl or 0,
                'Section 1256',  # Futures contracts
                '1',  # Futures are marked-to-market
                'Future'
            ])
        
        # Add summary row
        total_pnl = sum(trade.pnl for trade in trades if trade.pnl)
        writer.writerow([])
        writer.writerow(['TOTAL P&L', '', '', '', '', '', total_pnl, '', '', ''])
        
        output.seek(0)
        filename = f"tax_report_{current_year}_{datetime.now().strftime('%Y%m%d')}.csv"
        return Response(output, mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment;filename={filename}"})

    except Exception as e:
        flash(f'Error generating tax report: {str(e)}', 'danger')
        return redirect(url_for('trades.view_trades_list'))


@trades_bp.route('/export_performance_report', methods=['GET'])
@login_required
def export_performance_report():
    """Export the most comprehensive trading performance analysis report imaginable."""
    try:
        trades = Trade.query.filter_by(user_id=current_user.id).order_by(Trade.trade_date.desc()).all()

        if not trades:
            flash('No trades found for performance report.', 'warning')
            return redirect(url_for('trades.view_trades_list'))

        output = io.StringIO()
        writer = csv.writer(output)
        
        # REPORT HEADER & EXECUTIVE SUMMARY
        writer.writerow(['COMPREHENSIVE TRADING PERFORMANCE ANALYSIS REPORT'])
        writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([f'Account: {current_user.username}'])
        writer.writerow([f'Analysis Period: {trades[0].trade_date} to {trades[-1].trade_date}'])
        writer.writerow([])
        
        # Calculate all base statistics
        total_trades = len(trades)
        trades_with_pnl = [t for t in trades if t.pnl is not None]
        profitable_trades = len([t for t in trades if t.pnl and t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl and t.pnl < 0])
        breakeven_trades = len([t for t in trades if t.pnl and t.pnl == 0])
        strike_rate = (profitable_trades / len(trades_with_pnl) * 100) if trades_with_pnl else 0
        total_pnl = sum(trade.pnl for trade in trades if trade.pnl)
        avg_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0
        
        # Winner/Loser analysis
        winning_pnls = [t.pnl for t in trades if t.pnl and t.pnl > 0]
        losing_pnls = [t.pnl for t in trades if t.pnl and t.pnl < 0]
        avg_winner = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
        avg_loser = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0
        largest_winner = max(winning_pnls) if winning_pnls else 0
        largest_loser = min(losing_pnls) if losing_pnls else 0
        profit_factor = abs(sum(winning_pnls) / sum(losing_pnls)) if losing_pnls and sum(losing_pnls) != 0 else float('inf')
        
        # EXECUTIVE SUMMARY STATISTICS
        writer.writerow(['EXECUTIVE SUMMARY STATISTICS'])
        writer.writerow(['Metric', 'Value', 'Analysis'])
        writer.writerow(['Total Trades', total_trades, 'Sample Size'])
        writer.writerow(['Profitable Trades', profitable_trades, f'{profitable_trades/total_trades*100:.1f}% of all trades'])
        writer.writerow(['Losing Trades', losing_trades, f'{losing_trades/total_trades*100:.1f}% of all trades'])
        writer.writerow(['Breakeven Trades', breakeven_trades, f'{breakeven_trades/total_trades*100:.1f}% of all trades'])
        writer.writerow(['Strike Rate', f'{strike_rate:.2f}%', 'Win Percentage'])
        writer.writerow(['Total P&L', f'${total_pnl:,.2f}', 'Cumulative Performance'])
        writer.writerow(['Avg P&L per Trade', f'${avg_pnl_per_trade:,.2f}', 'Expected Value per Trade'])
        writer.writerow(['Average Winner', f'${avg_winner:,.2f}', 'Avg Profitable Trade'])
        writer.writerow(['Average Loser', f'${avg_loser:,.2f}', 'Avg Losing Trade'])
        writer.writerow(['Largest Winner', f'${largest_winner:,.2f}', 'Best Single Trade'])
        writer.writerow(['Largest Loser', f'${largest_loser:,.2f}', 'Worst Single Trade'])
        writer.writerow(['Profit Factor', f'{profit_factor:.2f}', 'Gross Profit / Gross Loss'])
        writer.writerow([])
        
        # COMPREHENSIVE MODEL PERFORMANCE ANALYSIS
        writer.writerow(['COMPREHENSIVE MODEL PERFORMANCE ANALYSIS'])
        model_stats = {}
        for trade in trades:
            model_name = trade.trading_model.name if trade.trading_model else 'No Model'
            if model_name not in model_stats:
                model_stats[model_name] = {
                    'trades': 0, 'pnl': 0, 'wins': 0, 'losses': 0, 'breakevens': 0,
                    'winning_pnls': [], 'losing_pnls': [], 'all_pnls': []
                }
            
            stats = model_stats[model_name]
            stats['trades'] += 1
            if trade.pnl is not None:
                stats['all_pnls'].append(trade.pnl)
                stats['pnl'] += trade.pnl
                if trade.pnl > 0:
                    stats['wins'] += 1
                    stats['winning_pnls'].append(trade.pnl)
                elif trade.pnl < 0:
                    stats['losses'] += 1
                    stats['losing_pnls'].append(trade.pnl)
                else:
                    stats['breakevens'] += 1
        
        writer.writerow(['Model', 'Trades', 'Total P&L', 'Win Rate', 'Avg P&L', 'Avg Winner', 'Avg Loser', 'Profit Factor', 'Best Trade', 'Worst Trade'])
        for model, stats in model_stats.items():
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            avg_pnl = stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
            avg_winner = sum(stats['winning_pnls']) / len(stats['winning_pnls']) if stats['winning_pnls'] else 0
            avg_loser = sum(stats['losing_pnls']) / len(stats['losing_pnls']) if stats['losing_pnls'] else 0
            profit_factor = abs(sum(stats['winning_pnls']) / sum(stats['losing_pnls'])) if stats['losing_pnls'] and sum(stats['losing_pnls']) != 0 else float('inf')
            best_trade = max(stats['all_pnls']) if stats['all_pnls'] else 0
            worst_trade = min(stats['all_pnls']) if stats['all_pnls'] else 0
            
            writer.writerow([
                model, stats['trades'], f"${stats['pnl']:,.2f}", f"{win_rate:.1f}%", f"${avg_pnl:,.2f}",
                f"${avg_winner:,.2f}", f"${avg_loser:,.2f}", f"{profit_factor:.2f}",
                f"${best_trade:,.2f}", f"${worst_trade:,.2f}"
            ])
        writer.writerow([])
        
        # DAY OF WEEK ANALYSIS
        writer.writerow(['DAY OF WEEK ANALYSIS'])
        dow_stats = {}
        dow_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for trade in trades:
            dow = trade.trade_date.strftime('%A')
            if dow not in dow_stats:
                dow_stats[dow] = {'trades': 0, 'pnl': 0, 'wins': 0, 'losses': 0}
            dow_stats[dow]['trades'] += 1
            if trade.pnl is not None:
                dow_stats[dow]['pnl'] += trade.pnl
                if trade.pnl > 0:
                    dow_stats[dow]['wins'] += 1
                elif trade.pnl < 0:
                    dow_stats[dow]['losses'] += 1
        
        writer.writerow(['Day', 'Trades', 'Total P&L', 'Avg P&L', 'Win Rate', 'Wins', 'Losses'])
        for dow_name in dow_names:
            if dow_name in dow_stats:
                stats = dow_stats[dow_name]
                win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
                avg_pnl = stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
                writer.writerow([
                    dow_name, stats['trades'], f"${stats['pnl']:,.2f}", f"${avg_pnl:,.2f}",
                    f"{win_rate:.1f}%", stats['wins'], stats['losses']
                ])
        writer.writerow([])
        
        # MODEL BREAKDOWN BY DAY OF WEEK
        writer.writerow(['MODEL PERFORMANCE BY DAY OF WEEK'])
        model_dow_stats = {}
        for trade in trades:
            model_name = trade.trading_model.name if trade.trading_model else 'No Model'
            dow = trade.trade_date.strftime('%A')
            key = f"{model_name}_{dow}"
            
            if key not in model_dow_stats:
                model_dow_stats[key] = {'model': model_name, 'dow': dow, 'trades': 0, 'pnl': 0, 'wins': 0}
            
            model_dow_stats[key]['trades'] += 1
            if trade.pnl is not None:
                model_dow_stats[key]['pnl'] += trade.pnl
                if trade.pnl > 0:
                    model_dow_stats[key]['wins'] += 1
        
        writer.writerow(['Model', 'Day', 'Trades', 'Total P&L', 'Avg P&L', 'Win Rate'])
        for key in sorted(model_dow_stats.keys()):
            stats = model_dow_stats[key]
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            avg_pnl = stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
            writer.writerow([
                stats['model'], stats['dow'], stats['trades'], f"${stats['pnl']:,.2f}",
                f"${avg_pnl:,.2f}", f"{win_rate:.1f}%"
            ])
        writer.writerow([])
        
        # TIME OF DAY ANALYSIS
        writer.writerow(['TIME OF DAY ANALYSIS'])
        time_stats = {}
        
        for trade in trades:
            if trade.entries.first() and trade.entries.first().entry_time:
                hour = trade.entries.first().entry_time.hour
                time_bucket = f"{hour:02d}:00-{hour:02d}:59"
                
                if time_bucket not in time_stats:
                    time_stats[time_bucket] = {'trades': 0, 'pnl': 0, 'wins': 0}
                
                time_stats[time_bucket]['trades'] += 1
                if trade.pnl is not None:
                    time_stats[time_bucket]['pnl'] += trade.pnl
                    if trade.pnl > 0:
                        time_stats[time_bucket]['wins'] += 1
        
        writer.writerow(['Time Bucket', 'Trades', 'Total P&L', 'Avg P&L', 'Win Rate'])
        for time_bucket in sorted(time_stats.keys()):
            stats = time_stats[time_bucket]
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            avg_pnl = stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
            writer.writerow([
                time_bucket, stats['trades'], f"${stats['pnl']:,.2f}",
                f"${avg_pnl:,.2f}", f"{win_rate:.1f}%"
            ])
        writer.writerow([])
        
        # MODEL PERFORMANCE BY TIME OF DAY
        writer.writerow(['MODEL PERFORMANCE BY TIME OF DAY'])
        model_time_stats = {}
        
        for trade in trades:
            if trade.entries.first() and trade.entries.first().entry_time and trade.trading_model:
                model_name = trade.trading_model.name
                hour = trade.entries.first().entry_time.hour
                time_bucket = f"{hour:02d}:00-{hour:02d}:59"
                key = f"{model_name}_{time_bucket}"
                
                if key not in model_time_stats:
                    model_time_stats[key] = {'model': model_name, 'time': time_bucket, 'trades': 0, 'pnl': 0, 'wins': 0}
                
                model_time_stats[key]['trades'] += 1
                if trade.pnl is not None:
                    model_time_stats[key]['pnl'] += trade.pnl
                    if trade.pnl > 0:
                        model_time_stats[key]['wins'] += 1
        
        writer.writerow(['Model', 'Time Bucket', 'Trades', 'Total P&L', 'Avg P&L', 'Win Rate'])
        for key in sorted(model_time_stats.keys()):
            stats = model_time_stats[key]
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            avg_pnl = stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
            writer.writerow([
                stats['model'], stats['time'], stats['trades'], f"${stats['pnl']:,.2f}",
                f"${avg_pnl:,.2f}", f"{win_rate:.1f}%"
            ])
        writer.writerow([])
        
        # INSTRUMENT BREAKDOWN
        writer.writerow(['INSTRUMENT PERFORMANCE BREAKDOWN'])
        instrument_stats = {}
        
        for trade in trades:
            instrument = trade.instrument or trade.instrument_legacy or 'Unknown'
            if instrument not in instrument_stats:
                instrument_stats[instrument] = {
                    'trades': 0, 'pnl': 0, 'wins': 0, 'losses': 0,
                    'total_contracts': 0, 'winning_pnls': [], 'losing_pnls': []
                }
            
            stats = instrument_stats[instrument]
            stats['trades'] += 1
            stats['total_contracts'] += trade.total_contracts_entered or 0
            
            if trade.pnl is not None:
                stats['pnl'] += trade.pnl
                if trade.pnl > 0:
                    stats['wins'] += 1
                    stats['winning_pnls'].append(trade.pnl)
                elif trade.pnl < 0:
                    stats['losses'] += 1
                    stats['losing_pnls'].append(trade.pnl)
        
        writer.writerow(['Instrument', 'Trades', 'Contracts', 'Total P&L', 'Avg P&L', 'Win Rate', 'Avg Winner', 'Avg Loser', 'Profit Factor'])
        for instrument, stats in instrument_stats.items():
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            avg_pnl = stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
            avg_winner = sum(stats['winning_pnls']) / len(stats['winning_pnls']) if stats['winning_pnls'] else 0
            avg_loser = sum(stats['losing_pnls']) / len(stats['losing_pnls']) if stats['losing_pnls'] else 0
            profit_factor = abs(sum(stats['winning_pnls']) / sum(stats['losing_pnls'])) if stats['losing_pnls'] and sum(stats['losing_pnls']) != 0 else float('inf')
            
            writer.writerow([
                instrument, stats['trades'], stats['total_contracts'], f"${stats['pnl']:,.2f}",
                f"${avg_pnl:,.2f}", f"{win_rate:.1f}%", f"${avg_winner:,.2f}",
                f"${avg_loser:,.2f}", f"{profit_factor:.2f}"
            ])
        writer.writerow([])
        
        # MODEL BY INSTRUMENT MATRIX
        writer.writerow(['MODEL BY INSTRUMENT PERFORMANCE MATRIX'])
        model_instrument_stats = {}
        
        for trade in trades:
            model_name = trade.trading_model.name if trade.trading_model else 'No Model'
            instrument = trade.instrument or trade.instrument_legacy or 'Unknown'
            key = f"{model_name}_{instrument}"
            
            if key not in model_instrument_stats:
                model_instrument_stats[key] = {'model': model_name, 'instrument': instrument, 'trades': 0, 'pnl': 0, 'wins': 0}
            
            model_instrument_stats[key]['trades'] += 1
            if trade.pnl is not None:
                model_instrument_stats[key]['pnl'] += trade.pnl
                if trade.pnl > 0:
                    model_instrument_stats[key]['wins'] += 1
        
        writer.writerow(['Model', 'Instrument', 'Trades', 'Total P&L', 'Avg P&L', 'Win Rate'])
        for key in sorted(model_instrument_stats.keys()):
            stats = model_instrument_stats[key]
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            avg_pnl = stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
            writer.writerow([
                stats['model'], stats['instrument'], stats['trades'], f"${stats['pnl']:,.2f}",
                f"${avg_pnl:,.2f}", f"{win_rate:.1f}%"
            ])
        writer.writerow([])
        
        # DIRECTION BY RESULT ANALYSIS
        writer.writerow(['DIRECTION BY RESULT ANALYSIS'])
        direction_stats = {}
        
        for trade in trades:
            direction = trade.direction or 'Unknown'
            if direction not in direction_stats:
                direction_stats[direction] = {'trades': 0, 'pnl': 0, 'wins': 0, 'losses': 0, 'breakevens': 0}
            
            direction_stats[direction]['trades'] += 1
            if trade.pnl is not None:
                direction_stats[direction]['pnl'] += trade.pnl
                if trade.pnl > 0:
                    direction_stats[direction]['wins'] += 1
                elif trade.pnl < 0:
                    direction_stats[direction]['losses'] += 1
                else:
                    direction_stats[direction]['breakevens'] += 1
        
        writer.writerow(['Direction', 'Trades', 'Total P&L', 'Avg P&L', 'Win Rate', 'Wins', 'Losses', 'Breakevens'])
        for direction, stats in direction_stats.items():
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            avg_pnl = stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
            writer.writerow([
                direction, stats['trades'], f"${stats['pnl']:,.2f}", f"${avg_pnl:,.2f}",
                f"{win_rate:.1f}%", stats['wins'], stats['losses'], stats['breakevens']
            ])
        writer.writerow([])
        
        # TAG UTILIZATION BREAKDOWN
        writer.writerow(['TAG UTILIZATION AND PERFORMANCE ANALYSIS'])
        tag_stats = {}
        
        for trade in trades:
            if trade.tags:
                for tag in trade.tags:
                    tag_name = tag.name
                    if tag_name not in tag_stats:
                        tag_stats[tag_name] = {'trades': 0, 'pnl': 0, 'wins': 0, 'losses': 0}
                    
                    tag_stats[tag_name]['trades'] += 1
                    if trade.pnl is not None:
                        tag_stats[tag_name]['pnl'] += trade.pnl
                        if trade.pnl > 0:
                            tag_stats[tag_name]['wins'] += 1
                        elif trade.pnl < 0:
                            tag_stats[tag_name]['losses'] += 1
            else:
                # Track trades with no tags
                if 'No Tags' not in tag_stats:
                    tag_stats['No Tags'] = {'trades': 0, 'pnl': 0, 'wins': 0, 'losses': 0}
                
                tag_stats['No Tags']['trades'] += 1
                if trade.pnl is not None:
                    tag_stats['No Tags']['pnl'] += trade.pnl
                    if trade.pnl > 0:
                        tag_stats['No Tags']['wins'] += 1
                    elif trade.pnl < 0:
                        tag_stats['No Tags']['losses'] += 1
        
        writer.writerow(['Tag', 'Usage Count', 'Total P&L', 'Avg P&L', 'Win Rate', 'Usage %'])
        for tag_name, stats in sorted(tag_stats.items(), key=lambda x: x[1]['trades'], reverse=True):
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            avg_pnl = stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
            usage_pct = (stats['trades'] / total_trades * 100) if total_trades > 0 else 0
            writer.writerow([
                tag_name, stats['trades'], f"${stats['pnl']:,.2f}", f"${avg_pnl:,.2f}",
                f"{win_rate:.1f}%", f"{usage_pct:.1f}%"
            ])
        writer.writerow([])
        
        # MONTHLY PERFORMANCE DETAILED
        writer.writerow(['DETAILED MONTHLY PERFORMANCE'])
        monthly_stats = {}
        for trade in trades:
            month_key = trade.trade_date.strftime('%Y-%m')
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {'trades': 0, 'pnl': 0, 'wins': 0, 'losses': 0, 'breakevens': 0, 'winning_pnls': [], 'losing_pnls': []}
            
            monthly_stats[month_key]['trades'] += 1
            if trade.pnl is not None:
                monthly_stats[month_key]['pnl'] += trade.pnl
                if trade.pnl > 0:
                    monthly_stats[month_key]['wins'] += 1
                    monthly_stats[month_key]['winning_pnls'].append(trade.pnl)
                elif trade.pnl < 0:
                    monthly_stats[month_key]['losses'] += 1
                    monthly_stats[month_key]['losing_pnls'].append(trade.pnl)
                else:
                    monthly_stats[month_key]['breakevens'] += 1
        
        writer.writerow(['Month', 'Trades', 'P&L', 'Avg P&L', 'Win Rate', 'Avg Winner', 'Avg Loser', 'Best Trade', 'Worst Trade'])
        for month, stats in sorted(monthly_stats.items()):
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            avg_pnl = stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
            avg_winner = sum(stats['winning_pnls']) / len(stats['winning_pnls']) if stats['winning_pnls'] else 0
            avg_loser = sum(stats['losing_pnls']) / len(stats['losing_pnls']) if stats['losing_pnls'] else 0
            best_trade = max(stats['winning_pnls'] + stats['losing_pnls']) if (stats['winning_pnls'] + stats['losing_pnls']) else 0
            worst_trade = min(stats['winning_pnls'] + stats['losing_pnls']) if (stats['winning_pnls'] + stats['losing_pnls']) else 0
            
            writer.writerow([
                month, stats['trades'], f"${stats['pnl']:,.2f}", f"${avg_pnl:,.2f}",
                f"{win_rate:.1f}%", f"${avg_winner:,.2f}", f"${avg_loser:,.2f}",
                f"${best_trade:,.2f}", f"${worst_trade:,.2f}"
            ])
        writer.writerow([])
        
        # RISK ANALYSIS
        writer.writerow(['COMPREHENSIVE RISK ANALYSIS'])
        
        # Calculate risk metrics
        all_pnls = [t.pnl for t in trades if t.pnl is not None]
        if all_pnls:
            import statistics
            
            # Standard deviation of returns
            std_dev = statistics.stdev(all_pnls) if len(all_pnls) > 1 else 0
            
            # Max drawdown calculation
            running_total = 0
            peak = 0
            max_drawdown = 0
            drawdown_periods = []
            current_drawdown = 0
            
            for trade in trades:
                if trade.pnl is not None:
                    running_total += trade.pnl
                    if running_total > peak:
                        peak = running_total
                        if current_drawdown != 0:
                            drawdown_periods.append(current_drawdown)
                            current_drawdown = 0
                    else:
                        current_drawdown = peak - running_total
                        if current_drawdown > max_drawdown:
                            max_drawdown = current_drawdown
            
            # Sharpe ratio (simplified - assuming risk-free rate of 0)
            sharpe_ratio = avg_pnl_per_trade / std_dev if std_dev > 0 else 0
            
            # Sortino ratio (downside deviation)
            negative_returns = [p for p in all_pnls if p < 0]
            downside_deviation = statistics.stdev(negative_returns) if len(negative_returns) > 1 else 0
            sortino_ratio = avg_pnl_per_trade / downside_deviation if downside_deviation > 0 else 0
            
            writer.writerow(['Risk Metric', 'Value', 'Interpretation'])
            writer.writerow(['Standard Deviation', f'${std_dev:,.2f}', 'Volatility of returns'])
            writer.writerow(['Maximum Drawdown', f'${max_drawdown:,.2f}', 'Largest peak-to-trough decline'])
            writer.writerow(['Sharpe Ratio', f'{sharpe_ratio:.3f}', 'Risk-adjusted return (>1.0 is good)'])
            writer.writerow(['Sortino Ratio', f'{sortino_ratio:.3f}', 'Downside risk-adjusted return'])
            writer.writerow(['Value at Risk (1%)', f'${min(all_pnls):,.2f}', 'Worst 1% outcome'])
            writer.writerow(['Average Drawdown Period', f'{len(drawdown_periods)} periods', 'Number of drawdown cycles'])
            
        writer.writerow([])
        
        # STREAK ANALYSIS
        writer.writerow(['WINNING & LOSING STREAK ANALYSIS'])
        
        current_win_streak = 0
        current_loss_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        win_streaks = []
        loss_streaks = []
        
        for trade in trades:
            if trade.pnl is not None:
                if trade.pnl > 0:
                    current_win_streak += 1
                    if current_loss_streak > 0:
                        loss_streaks.append(current_loss_streak)
                        current_loss_streak = 0
                elif trade.pnl < 0:
                    current_loss_streak += 1
                    if current_win_streak > 0:
                        win_streaks.append(current_win_streak)
                        current_win_streak = 0
                
                max_win_streak = max(max_win_streak, current_win_streak)
                max_loss_streak = max(max_loss_streak, current_loss_streak)
        
        # Add final streak
        if current_win_streak > 0:
            win_streaks.append(current_win_streak)
        if current_loss_streak > 0:
            loss_streaks.append(current_loss_streak)
        
        avg_win_streak = sum(win_streaks) / len(win_streaks) if win_streaks else 0
        avg_loss_streak = sum(loss_streaks) / len(loss_streaks) if loss_streaks else 0
        
        writer.writerow(['Streak Type', 'Maximum', 'Average', 'Total Streaks'])
        writer.writerow(['Winning Streaks', max_win_streak, f'{avg_win_streak:.1f}', len(win_streaks)])
        writer.writerow(['Losing Streaks', max_loss_streak, f'{avg_loss_streak:.1f}', len(loss_streaks)])
        writer.writerow([])
        
        # QUARTERLY ANALYSIS
        writer.writerow(['QUARTERLY PERFORMANCE ANALYSIS'])
        quarterly_stats = {}
        
        for trade in trades:
            quarter = f"{trade.trade_date.year}-Q{(trade.trade_date.month-1)//3 + 1}"
            if quarter not in quarterly_stats:
                quarterly_stats[quarter] = {'trades': 0, 'pnl': 0, 'wins': 0}
            
            quarterly_stats[quarter]['trades'] += 1
            if trade.pnl is not None:
                quarterly_stats[quarter]['pnl'] += trade.pnl
                if trade.pnl > 0:
                    quarterly_stats[quarter]['wins'] += 1
        
        writer.writerow(['Quarter', 'Trades', 'Total P&L', 'Avg P&L', 'Win Rate'])
        for quarter in sorted(quarterly_stats.keys()):
            stats = quarterly_stats[quarter]
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            avg_pnl = stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
            writer.writerow([
                quarter, stats['trades'], f"${stats['pnl']:,.2f}",
                f"${avg_pnl:,.2f}", f"{win_rate:.1f}%"
            ])
        writer.writerow([])
        
        # REPORT FOOTER
        writer.writerow(['END OF PERFORMANCE ANALYSIS REPORT'])
        writer.writerow([f'Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([f'Total analysis points: {total_trades} trades across {len(set(t.trade_date.strftime("%Y-%m") for t in trades))} months'])
        writer.writerow([])
        
        output.seek(0)
        filename = f"comprehensive_performance_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(output, mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment;filename={filename}"})

    except Exception as e:
        flash(f'Error generating comprehensive performance report: {str(e)}', 'danger')
        return redirect(url_for('trades.view_trades_list'))


class TradingChartsGenerator:
    """Generate comprehensive charts for trading performance analysis."""
    
    def __init__(self, trades, temp_dir=None):
        self.trades = trades
        self.temp_dir = temp_dir or tempfile.gettempdir()
        
        # Set global styling for professional appearance
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Corporate color scheme
        self.colors = {
            'primary': '#0066cc',
            'success': '#28a745',
            'danger': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8',
            'dark': '#343a40',
            'light': '#f8f9fa',
            'muted': '#6c757d'
        }
        
        # Chart styling
        self.chart_style = {
            'figure.figsize': (12, 8),
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10,
            'font.size': 10
        }
        plt.rcParams.update(self.chart_style)
    
    def create_equity_curve_chart(self):
        """Create cumulative P&L equity curve with drawdown."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[3, 1])
        
        # Sort trades chronologically for equity curve (oldest first)
        trades_chronological = sorted(self.trades, key=lambda t: t.trade_date)
        
        # Prepare data
        trades_data = []
        cumulative_pnl = 0
        peak_equity = 0
        
        for i, trade in enumerate(trades_chronological):
            if trade.pnl is not None:
                cumulative_pnl += trade.pnl
                if cumulative_pnl > peak_equity:
                    peak_equity = cumulative_pnl
                drawdown = peak_equity - cumulative_pnl
                
                trades_data.append({
                    'trade_num': i + 1,
                    'date': trade.trade_date,
                    'cumulative_pnl': cumulative_pnl,
                    'drawdown': -drawdown  # Negative for visualization
                })
        
        df = pd.DataFrame(trades_data)
        
        # Equity curve
        ax1.plot(df['trade_num'], df['cumulative_pnl'], 
                color=self.colors['primary'], linewidth=2.5, label='Cumulative P&L')
        ax1.fill_between(df['trade_num'], df['cumulative_pnl'], 0, 
                        alpha=0.3, color=self.colors['primary'])
        ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax1.set_title('Equity Curve - Cumulative P&L Over Time', fontweight='bold', pad=20)
        ax1.set_xlabel('Trade Number')
        ax1.set_ylabel('Cumulative P&L ($)')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Format y-axis as currency
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # Drawdown chart
        ax2.fill_between(df['trade_num'], df['drawdown'], 0, 
                        color=self.colors['danger'], alpha=0.7, label='Drawdown from Peak')
        ax2.set_title('Drawdown from Peak Equity', fontweight='bold')
        ax2.set_xlabel('Trade Number')
        ax2.set_ylabel('Drawdown ($)')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${abs(x):,.0f}'))
        
        plt.tight_layout()
        filename = os.path.join(self.temp_dir, 'equity_curve.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        return filename
    
    def create_monthly_pnl_chart(self):
        """Create monthly P&L bar chart."""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Group trades by month
        monthly_data = {}
        for trade in self.trades:
            if trade.pnl is not None:
                month_key = trade.trade_date.strftime('%Y-%m')
                month_name = trade.trade_date.strftime('%b %Y')
                if month_key not in monthly_data:
                    monthly_data[month_key] = {'name': month_name, 'pnl': 0, 'trades': 0}
                monthly_data[month_key]['pnl'] += trade.pnl
                monthly_data[month_key]['trades'] += 1
        
        months = list(monthly_data.keys())
        month_names = [monthly_data[m]['name'] for m in months]
        pnls = [monthly_data[m]['pnl'] for m in months]
        
        # Color bars based on positive/negative
        colors = [self.colors['success'] if pnl >= 0 else self.colors['danger'] for pnl in pnls]
        
        bars = ax.bar(month_names, pnls, color=colors, alpha=0.8)
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax.set_title('Monthly P&L Performance', fontweight='bold', pad=20)
        ax.set_xlabel('Month')
        ax.set_ylabel('Net P&L ($)')
        ax.grid(True, axis='y', alpha=0.3)
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        
        # Format y-axis as currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # Add value labels on bars
        for bar, pnl in zip(bars, pnls):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + (abs(height) * 0.01),
                   f'${pnl:,.0f}', ha='center', va='bottom' if height >= 0 else 'top',
                   fontweight='bold', fontsize=9)
        
        plt.tight_layout()
        filename = os.path.join(self.temp_dir, 'monthly_pnl.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        return filename
    
    def create_model_performance_chart(self):
        """Create trading model performance comparison."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # Calculate model statistics
        model_stats = {}
        for trade in self.trades:
            model_name = trade.trading_model.name if trade.trading_model else 'No Model'
            if model_name not in model_stats:
                model_stats[model_name] = {'pnl': 0, 'trades': 0, 'wins': 0}
            
            model_stats[model_name]['trades'] += 1
            if trade.pnl is not None:
                model_stats[model_name]['pnl'] += trade.pnl
                if trade.pnl > 0:
                    model_stats[model_name]['wins'] += 1
        
        models = list(model_stats.keys())
        pnls = [model_stats[m]['pnl'] for m in models]
        win_rates = [(model_stats[m]['wins'] / model_stats[m]['trades'] * 100) 
                    if model_stats[m]['trades'] > 0 else 0 for m in models]
        
        # P&L by model
        colors = [self.colors['success'] if pnl >= 0 else self.colors['danger'] for pnl in pnls]
        bars1 = ax1.bar(models, pnls, color=colors, alpha=0.8)
        ax1.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax1.set_title('Total P&L by Trading Model', fontweight='bold')
        ax1.set_xlabel('Trading Model')
        ax1.set_ylabel('Total P&L ($)')
        ax1.grid(True, axis='y', alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Win rate by model
        bars2 = ax2.bar(models, win_rates, color=self.colors['info'], alpha=0.8)
        ax2.set_title('Win Rate by Trading Model', fontweight='bold')
        ax2.set_xlabel('Trading Model')
        ax2.set_ylabel('Win Rate (%)')
        ax2.set_ylim(0, 100)
        ax2.grid(True, axis='y', alpha=0.3)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Add value labels
        for bar, pnl in zip(bars1, pnls):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + (abs(height) * 0.01),
                    f'${pnl:,.0f}', ha='center', va='bottom' if height >= 0 else 'top',
                    fontweight='bold', fontsize=9)
        
        for bar, wr in zip(bars2, win_rates):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{wr:.1f}%', ha='center', va='bottom',
                    fontweight='bold', fontsize=9)
        
        plt.tight_layout()
        filename = os.path.join(self.temp_dir, 'model_performance.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        return filename
    
    def create_pnl_distribution_chart(self):
        """Create P&L distribution histogram."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        pnls = [trade.pnl for trade in self.trades if trade.pnl is not None]
        
        # Create histogram
        n_bins = min(50, len(pnls) // 10) if pnls else 20
        counts, bins, patches = ax.hist(pnls, bins=n_bins, alpha=0.7, edgecolor='black')
        
        # Color bars based on positive/negative
        for i, patch in enumerate(patches):
            if bins[i] >= 0:
                patch.set_facecolor(self.colors['success'])
            else:
                patch.set_facecolor(self.colors['danger'])
        
        ax.axvline(x=0, color='black', linestyle='-', alpha=0.8, linewidth=2)
        ax.set_title('P&L Distribution - Trade Outcome Frequency', fontweight='bold', pad=20)
        ax.set_xlabel('P&L per Trade ($)')
        ax.set_ylabel('Number of Trades')
        ax.grid(True, alpha=0.3)
        
        # Format x-axis as currency
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # Add statistics text
        if pnls:
            mean_pnl = np.mean(pnls)
            median_pnl = np.median(pnls)
            std_pnl = np.std(pnls)
            
            stats_text = f'Mean: ${mean_pnl:,.0f}\\nMedian: ${median_pnl:,.0f}\\nStd Dev: ${std_pnl:,.0f}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        filename = os.path.join(self.temp_dir, 'pnl_distribution.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        return filename
    
    def create_direction_performance_chart(self):
        """Create long vs short performance comparison."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Calculate direction statistics
        direction_stats = {}
        for trade in self.trades:
            direction = trade.direction or 'Unknown'
            if direction not in direction_stats:
                direction_stats[direction] = {'pnl': 0, 'trades': 0, 'wins': 0}
            
            direction_stats[direction]['trades'] += 1
            if trade.pnl is not None:
                direction_stats[direction]['pnl'] += trade.pnl
                if trade.pnl > 0:
                    direction_stats[direction]['wins'] += 1
        
        directions = list(direction_stats.keys())
        total_pnls = [direction_stats[d]['pnl'] for d in directions]
        win_rates = [(direction_stats[d]['wins'] / direction_stats[d]['trades'] * 100) 
                    if direction_stats[d]['trades'] > 0 else 0 for d in directions]
        avg_pnls = [direction_stats[d]['pnl'] / direction_stats[d]['trades'] 
                   if direction_stats[d]['trades'] > 0 else 0 for d in directions]
        
        x = np.arange(len(directions))
        width = 0.25
        
        # Create grouped bars
        bars1 = ax.bar(x - width, total_pnls, width, label='Total P&L ($)', 
                      color=self.colors['primary'], alpha=0.8)
        
        ax2 = ax.twinx()
        bars2 = ax2.bar(x, win_rates, width, label='Win Rate (%)', 
                       color=self.colors['success'], alpha=0.8)
        bars3 = ax2.bar(x + width, [rate * max(total_pnls) / 100 for rate in win_rates], width, 
                       label='Avg P&L per Trade', color=self.colors['warning'], alpha=0.8)
        
        ax.set_title('Performance by Trade Direction', fontweight='bold', pad=20)
        ax.set_xlabel('Trade Direction')
        ax.set_ylabel('Total P&L ($)', color=self.colors['primary'])
        ax2.set_ylabel('Win Rate (%) / Scaled Avg P&L', color=self.colors['success'])
        ax.set_xticks(x)
        ax.set_xticklabels(directions)
        ax.grid(True, alpha=0.3)
        
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # Combine legends
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
        
        plt.tight_layout()
        filename = os.path.join(self.temp_dir, 'direction_performance.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        return filename
    
    def create_win_loss_comparison_chart(self):
        """Create average winner vs average loser comparison."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        winning_trades = [t.pnl for t in self.trades if t.pnl and t.pnl > 0]
        losing_trades = [t.pnl for t in self.trades if t.pnl and t.pnl < 0]
        
        avg_winner = np.mean(winning_trades) if winning_trades else 0
        avg_loser = abs(np.mean(losing_trades)) if losing_trades else 0  # Make positive for display
        
        categories = ['Average Winner', 'Average Loser']
        values = [avg_winner, avg_loser]
        colors = [self.colors['success'], self.colors['danger']]
        
        bars = ax.bar(categories, values, color=colors, alpha=0.8)
        ax.set_title('Average Winner vs Average Loser', fontweight='bold', pad=20)
        ax.set_ylabel('Amount ($)')
        ax.grid(True, axis='y', alpha=0.3)
        
        # Format y-axis as currency
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + (height * 0.01),
                   f'${value:,.0f}', ha='center', va='bottom',
                   fontweight='bold', fontsize=12)
        
        # Add profit factor calculation
        profit_factor = avg_winner / avg_loser if avg_loser > 0 else float('inf')
        ax.text(0.5, 0.95, f'Profit Factor: {profit_factor:.2f}', 
               transform=ax.transAxes, ha='center', va='top',
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8),
               fontweight='bold', fontsize=12)
        
        plt.tight_layout()
        filename = os.path.join(self.temp_dir, 'win_loss_comparison.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        return filename
    
    def create_r_multiple_distribution_chart(self):
        """Create R-multiple distribution histogram."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        r_multiples = [trade.pnl_in_r for trade in self.trades if trade.pnl_in_r is not None]
        
        if not r_multiples:
            # Create placeholder chart
            ax.text(0.5, 0.5, 'No R-Multiple Data Available', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=16)
            ax.set_title('R-Multiple Distribution', fontweight='bold', pad=20)
        else:
            # Create histogram with specific bins for R-multiples
            bins = np.arange(-3, 5.5, 0.5)  # From -3R to 5R in 0.5R increments
            counts, bin_edges, patches = ax.hist(r_multiples, bins=bins, alpha=0.7, edgecolor='black')
            
            # Color bars based on positive/negative
            for i, patch in enumerate(patches):
                if bin_edges[i] >= 0:
                    patch.set_facecolor(self.colors['success'])
                else:
                    patch.set_facecolor(self.colors['danger'])
            
            ax.axvline(x=0, color='black', linestyle='-', alpha=0.8, linewidth=2)
            ax.axvline(x=1, color=self.colors['primary'], linestyle='--', alpha=0.8, linewidth=2, label='1R Target')
            ax.set_title('R-Multiple Distribution - Risk-Adjusted Returns', fontweight='bold', pad=20)
            ax.set_xlabel('R-Multiple (Profit/Risk Ratio)')
            ax.set_ylabel('Number of Trades')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Add statistics
            mean_r = np.mean(r_multiples)
            median_r = np.median(r_multiples)
            stats_text = f'Mean R: {mean_r:.2f}\\nMedian R: {median_r:.2f}\\nTotal Trades: {len(r_multiples)}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        filename = os.path.join(self.temp_dir, 'r_multiple_distribution.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        return filename
    
    def create_behavioral_tags_chart(self):
        """Create performance by behavioral tags analysis."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
        
        # Calculate tag performance
        tag_stats = {}
        for trade in self.trades:
            if trade.tags and trade.pnl is not None:
                for tag in trade.tags:
                    tag_name = tag.name
                    if tag_name not in tag_stats:
                        tag_stats[tag_name] = {'pnl': 0, 'trades': 0, 'wins': 0}
                    tag_stats[tag_name]['pnl'] += trade.pnl
                    tag_stats[tag_name]['trades'] += 1
                    if trade.pnl > 0:
                        tag_stats[tag_name]['wins'] += 1
        
        if not tag_stats:
            # Create placeholder chart
            ax1.text(0.5, 0.5, 'No Tag Data Available', 
                    ha='center', va='center', transform=ax1.transAxes, fontsize=16)
            ax1.set_title('Performance by Behavioral Tags', fontweight='bold', pad=20)
            ax2.text(0.5, 0.5, 'No Tag Data Available', 
                    ha='center', va='center', transform=ax2.transAxes, fontsize=16)
        else:
            # Separate positive and negative performing tags
            positive_tags = {k: v for k, v in tag_stats.items() if v['pnl'] >= 0}
            negative_tags = {k: v for k, v in tag_stats.items() if v['pnl'] < 0}
            
            # Positive/Helpful tags chart
            if positive_tags:
                pos_names = list(positive_tags.keys())
                pos_pnls = [positive_tags[tag]['pnl'] for tag in pos_names]
                
                bars1 = ax1.barh(pos_names, pos_pnls, color=self.colors['success'], alpha=0.8)
                ax1.set_title('Positive Behavioral Impact Tags', fontweight='bold', pad=20)
                ax1.set_xlabel('Total P&L ($)')
                ax1.grid(True, axis='x', alpha=0.3)
                ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
                
                # Add value labels
                for bar, pnl in zip(bars1, pos_pnls):
                    width = bar.get_width()
                    ax1.text(width + (max(pos_pnls) * 0.01), bar.get_y() + bar.get_height()/2,
                            f'${pnl:,.0f}', ha='left', va='center', fontweight='bold', fontsize=9)
            else:
                ax1.text(0.5, 0.5, 'No Positive Performing Tags', 
                        ha='center', va='center', transform=ax1.transAxes, fontsize=14)
                ax1.set_title('Positive Behavioral Impact Tags', fontweight='bold', pad=20)
            
            # Negative/Harmful tags chart  
            if negative_tags:
                neg_names = list(negative_tags.keys())
                neg_pnls = [abs(negative_tags[tag]['pnl']) for tag in neg_names]  # Make positive for display
                
                bars2 = ax2.barh(neg_names, neg_pnls, color=self.colors['danger'], alpha=0.8)
                ax2.set_title('Negative Behavioral Impact Tags', fontweight='bold', pad=20)
                ax2.set_xlabel('Total Loss ($) - Absolute Value')
                ax2.grid(True, axis='x', alpha=0.3)
                ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
                
                # Add value labels
                for bar, pnl in zip(bars2, neg_pnls):
                    width = bar.get_width()
                    ax2.text(width + (max(neg_pnls) * 0.01), bar.get_y() + bar.get_height()/2,
                            f'${pnl:,.0f}', ha='left', va='center', fontweight='bold', fontsize=9)
            else:
                ax2.text(0.5, 0.5, 'No Negative Performing Tags', 
                        ha='center', va='center', transform=ax2.transAxes, fontsize=14)
                ax2.set_title('Negative Behavioral Impact Tags', fontweight='bold', pad=20)
        
        plt.tight_layout()
        filename = os.path.join(self.temp_dir, 'behavioral_tags.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        return filename
    
    def create_hourly_heatmap_chart(self):
        """Create optimized hourly performance heatmap showing only active trading periods."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # First pass: collect all active days and hours
        active_days = set()
        active_hours = set()
        trading_data = {}  # {(day_idx, hour): pnl}
        
        all_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for trade in self.trades:
            if trade.pnl is not None and trade.entries.first():
                entry_point = trade.entries.first()
                if entry_point.entry_time:
                    # Handle both datetime and time objects
                    if hasattr(entry_point.entry_time, 'weekday'):
                        # It's a datetime object
                        day_idx = entry_point.entry_time.weekday()  # 0=Monday
                        hour_idx = entry_point.entry_time.hour
                    else:
                        # It's a time object, use trade date for weekday
                        day_idx = trade.trade_date.weekday()
                        hour_idx = entry_point.entry_time.hour
                    
                    active_days.add(day_idx)
                    active_hours.add(hour_idx)
                    
                    key = (day_idx, hour_idx)
                    if key not in trading_data:
                        trading_data[key] = 0
                    trading_data[key] += trade.pnl
        
        if not active_days or not active_hours:
            # No trading data available
            ax.text(0.5, 0.5, 'No Hourly Trading Data Available', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=16)
            ax.set_title('Hourly Performance Heatmap', fontweight='bold', pad=20)
        else:
            # Create optimized lists showing only active periods
            sorted_active_days = sorted(list(active_days))
            sorted_active_hours = sorted(list(active_hours))
            
            # Create labels for active periods
            active_day_labels = [all_days[day_idx] for day_idx in sorted_active_days]
            active_hour_labels = [f'{h:02d}:00' for h in sorted_active_hours]
            
            # Initialize optimized heatmap data
            heatmap_data = np.zeros((len(sorted_active_days), len(sorted_active_hours)))
            
            # Fill heatmap data
            for i, day_idx in enumerate(sorted_active_days):
                for j, hour_idx in enumerate(sorted_active_hours):
                    key = (day_idx, hour_idx)
                    if key in trading_data:
                        heatmap_data[i][j] = trading_data[key]
            
            # Create heatmap
            im = ax.imshow(heatmap_data, cmap='RdYlGn', aspect='auto', interpolation='nearest')
            
            # Set ticks and labels for active periods only
            ax.set_xticks(range(len(sorted_active_hours)))
            ax.set_xticklabels(active_hour_labels, rotation=45)
            ax.set_yticks(range(len(sorted_active_days)))
            ax.set_yticklabels(active_day_labels)
            
            ax.set_title('Hourly Performance Heatmap (Active Trading Periods Only)', fontweight='bold', pad=20)
            ax.set_xlabel('Hour of Day')
            ax.set_ylabel('Day of Week')
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('Total P&L ($)', rotation=270, labelpad=15)
            
            # Add text annotations for all values (since we're showing active periods only)
            for i in range(len(sorted_active_days)):
                for j in range(len(sorted_active_hours)):
                    if abs(heatmap_data[i][j]) > 50:  # Show values above $50
                        # Determine text color for visibility
                        value = heatmap_data[i][j]
                        max_abs_value = np.max(np.abs(heatmap_data)) if np.max(np.abs(heatmap_data)) > 0 else 1
                        text_color = 'white' if abs(value) > max_abs_value * 0.3 else 'black'
                        
                        ax.text(j, i, f'${value:,.0f}',
                               ha='center', va='center', fontsize=9, fontweight='bold',
                               color=text_color)
            
            # Add summary statistics
            total_periods = len(sorted_active_days) * len(sorted_active_hours)
            profitable_periods = len([v for v in trading_data.values() if v > 0])
            summary_text = f'Active Periods: {len(trading_data)}/{total_periods} | Profitable: {profitable_periods}/{len(trading_data)}'
            ax.text(0.02, 0.98, summary_text, transform=ax.transAxes, 
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                   fontsize=10)
        
        plt.tight_layout()
        filename = os.path.join(self.temp_dir, 'hourly_heatmap.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        return filename
    
    def create_trade_duration_chart(self):
        """Create trade duration analysis for winners vs losers."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Calculate trade durations
        winner_durations = []
        loser_durations = []
        
        for trade in self.trades:
            if trade.pnl is not None and trade.entries.first() and trade.exits.first():
                entry_time = trade.entries.first().entry_time
                exit_time = trade.exits.first().exit_time
                
                if entry_time and exit_time:
                    # Handle both datetime and time objects
                    try:
                        if hasattr(entry_time, 'date') and hasattr(exit_time, 'date'):
                            # Both are datetime objects
                            duration_hours = (exit_time - entry_time).total_seconds() / 3600
                        else:
                            # They are time objects, combine with trade date
                            from datetime import datetime, time, timedelta
                            
                            if isinstance(entry_time, time) and isinstance(exit_time, time):
                                entry_dt = datetime.combine(trade.trade_date, entry_time)
                                exit_dt = datetime.combine(trade.trade_date, exit_time)
                                
                                # Handle overnight trades (exit next day)
                                if exit_time < entry_time:
                                    exit_dt += timedelta(days=1)
                                
                                duration_hours = (exit_dt - entry_dt).total_seconds() / 3600
                            else:
                                # Skip if we can't calculate duration
                                continue
                        
                        if trade.pnl > 0:
                            winner_durations.append(duration_hours)
                        elif trade.pnl < 0:
                            loser_durations.append(duration_hours)
                    except Exception:
                        # Skip trades with calculation issues
                        continue
        
        if not winner_durations and not loser_durations:
            ax.text(0.5, 0.5, 'No Trade Duration Data Available', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=16)
            ax.set_title('Trade Duration Analysis', fontweight='bold', pad=20)
        else:
            # Create box plots
            data_to_plot = []
            labels = []
            
            if winner_durations:
                data_to_plot.append(winner_durations)
                labels.append(f'Winners\\n(n={len(winner_durations)})')
            
            if loser_durations:
                data_to_plot.append(loser_durations)
                labels.append(f'Losers\\n(n={len(loser_durations)})')
            
            box_plot = ax.boxplot(data_to_plot, labels=labels, patch_artist=True)
            
            # Color the boxes
            colors = [self.colors['success'], self.colors['danger']]
            for patch, color in zip(box_plot['boxes'], colors[:len(box_plot['boxes'])]):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            
            ax.set_title('Trade Duration: Winners vs Losers', fontweight='bold', pad=20)
            ax.set_ylabel('Duration (Hours)')
            ax.grid(True, axis='y', alpha=0.3)
            
            # Add statistics
            if winner_durations and loser_durations:
                avg_winner_duration = np.mean(winner_durations)
                avg_loser_duration = np.mean(loser_durations)
                
                stats_text = f'Avg Winner Duration: {avg_winner_duration:.1f}h\\n'
                stats_text += f'Avg Loser Duration: {avg_loser_duration:.1f}h\\n'
                stats_text += f'Ratio (W/L): {avg_winner_duration/avg_loser_duration:.2f}'
                
                ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        filename = os.path.join(self.temp_dir, 'trade_duration.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        return filename
    
    def create_position_size_chart(self):
        """Create performance by position size analysis."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Calculate position size performance
        size_stats = {}
        for trade in self.trades:
            if trade.pnl is not None:
                size = trade.total_contracts_entered or 0
                if size not in size_stats:
                    size_stats[size] = {'pnl': 0, 'trades': 0}
                size_stats[size]['pnl'] += trade.pnl
                size_stats[size]['trades'] += 1
        
        if not size_stats:
            ax.text(0.5, 0.5, 'No Position Size Data Available', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=16)
            ax.set_title('Performance by Position Size', fontweight='bold', pad=20)
        else:
            sizes = sorted(size_stats.keys())
            avg_pnls = [size_stats[size]['pnl'] / size_stats[size]['trades'] for size in sizes]
            trade_counts = [size_stats[size]['trades'] for size in sizes]
            
            # Create bar chart with colors based on performance
            colors = [self.colors['success'] if pnl >= 0 else self.colors['danger'] for pnl in avg_pnls]
            bars = ax.bar(sizes, avg_pnls, color=colors, alpha=0.8)
            
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
            ax.set_title('Average P&L per Trade by Position Size', fontweight='bold', pad=20)
            ax.set_xlabel('Position Size (Contracts)')
            ax.set_ylabel('Average P&L per Trade ($)')
            ax.grid(True, axis='y', alpha=0.3)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            # Add value labels and trade counts
            for bar, pnl, count in zip(bars, avg_pnls, trade_counts):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + (abs(height) * 0.01),
                       f'${pnl:,.0f}\\n({count} trades)', ha='center', 
                       va='bottom' if height >= 0 else 'top',
                       fontweight='bold', fontsize=9)
        
        plt.tight_layout()
        filename = os.path.join(self.temp_dir, 'position_size.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        return filename
    
    def create_rolling_metrics_chart(self):
        """Create rolling performance metrics over time."""
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12))
        
        window_size = min(50, len(self.trades) // 4) if self.trades else 20
        
        if len(self.trades) < window_size:
            for ax in [ax1, ax2, ax3]:
                ax.text(0.5, 0.5, f'Need at least {window_size} trades for rolling analysis', 
                       ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax1.set_title('Rolling Performance Metrics', fontweight='bold', pad=20)
        else:
            trade_numbers = []
            rolling_win_rates = []
            rolling_profit_factors = []
            rolling_avg_pnls = []
            
            for i in range(window_size - 1, len(self.trades)):
                window_trades = self.trades[i - window_size + 1:i + 1]
                valid_trades = [t for t in window_trades if t.pnl is not None]
                
                if valid_trades:
                    # Win rate
                    wins = sum(1 for t in valid_trades if t.pnl > 0)
                    win_rate = (wins / len(valid_trades)) * 100
                    
                    # Profit factor
                    gross_profit = sum(t.pnl for t in valid_trades if t.pnl > 0)
                    gross_loss = abs(sum(t.pnl for t in valid_trades if t.pnl < 0))
                    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
                    
                    # Average P&L
                    avg_pnl = sum(t.pnl for t in valid_trades) / len(valid_trades)
                    
                    trade_numbers.append(i + 1)
                    rolling_win_rates.append(win_rate)
                    rolling_profit_factors.append(profit_factor)
                    rolling_avg_pnls.append(avg_pnl)
            
            # Plot rolling win rate
            ax1.plot(trade_numbers, rolling_win_rates, color=self.colors['primary'], linewidth=2)
            ax1.set_title(f'Rolling Win Rate (Last {window_size} Trades)', fontweight='bold')
            ax1.set_ylabel('Win Rate (%)')
            ax1.grid(True, alpha=0.3)
            ax1.set_ylim(0, 100)
            
            # Plot rolling profit factor
            ax2.plot(trade_numbers, rolling_profit_factors, color=self.colors['success'], linewidth=2)
            ax2.axhline(y=1, color='red', linestyle='--', alpha=0.7, label='Breakeven')
            ax2.set_title(f'Rolling Profit Factor (Last {window_size} Trades)', fontweight='bold')
            ax2.set_ylabel('Profit Factor')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            
            # Plot rolling average P&L
            ax3.plot(trade_numbers, rolling_avg_pnls, color=self.colors['info'], linewidth=2)
            ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
            ax3.set_title(f'Rolling Average P&L (Last {window_size} Trades)', fontweight='bold')
            ax3.set_xlabel('Trade Number')
            ax3.set_ylabel('Average P&L ($)')
            ax3.grid(True, alpha=0.3)
            ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        plt.tight_layout()
        filename = os.path.join(self.temp_dir, 'rolling_metrics.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        return filename
    
    def create_mfe_mae_scatter_chart(self):
        """Create MFE vs MAE scatter plot for trade efficiency analysis."""
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Collect MFE and MAE data
        winning_mae = []
        winning_mfe = []
        losing_mae = []
        losing_mfe = []
        
        for trade in self.trades:
            if trade.pnl is not None and trade.mae_price is not None and trade.mfe_price is not None and trade.average_entry_price is not None:
                # Calculate MAE and MFE in points from the price values
                mae_points = abs(trade.mae_price - trade.average_entry_price)
                mfe_points = abs(trade.mfe_price - trade.average_entry_price)
                
                if trade.pnl > 0:
                    winning_mae.append(mae_points)
                    winning_mfe.append(mfe_points)
                elif trade.pnl < 0:
                    losing_mae.append(mae_points)
                    losing_mfe.append(mfe_points)
        
        if not winning_mae and not losing_mae:
            ax.text(0.5, 0.5, 'No MFE/MAE Data Available\\nEnsure trades have Maximum Favorable/Adverse Excursion data', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title('Trade Efficiency: MFE vs MAE Analysis', fontweight='bold', pad=20)
        else:
            # Plot winning trades
            if winning_mae and winning_mfe:
                ax.scatter(winning_mae, winning_mfe, c=self.colors['success'], alpha=0.6, 
                          s=50, label=f'Winners (n={len(winning_mae)})', edgecolors='black', linewidth=0.5)
            
            # Plot losing trades
            if losing_mae and losing_mfe:
                ax.scatter(losing_mae, losing_mfe, c=self.colors['danger'], alpha=0.6, 
                          s=50, label=f'Losers (n={len(losing_mae)})', edgecolors='black', linewidth=0.5)
            
            ax.set_title('Trade Efficiency: Maximum Favorable vs Adverse Excursion', fontweight='bold', pad=20)
            ax.set_xlabel('Maximum Adverse Excursion - MAE ($)')
            ax.set_ylabel('Maximum Favorable Excursion - MFE ($)')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Format axes as currency
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            # Add diagonal reference lines
            if winning_mae or losing_mae:
                max_mae = max((max(winning_mae) if winning_mae else 0), 
                             (max(losing_mae) if losing_mae else 0))
                max_mfe = max((max(winning_mfe) if winning_mfe else 0), 
                             (max(losing_mfe) if losing_mfe else 0))
                
                # 1:1 line
                max_val = max(max_mae, max_mfe)
                ax.plot([0, max_val], [0, max_val], 'k--', alpha=0.5, label='1:1 Ratio')
                
                # 2:1 and 3:1 reward:risk lines
                ax.plot([0, max_mae], [0, max_mae * 2], 'g--', alpha=0.3, label='2:1 R:R')
                ax.plot([0, max_mae], [0, max_mae * 3], 'g:', alpha=0.3, label='3:1 R:R')
                ax.legend()
        
        plt.tight_layout()
        filename = os.path.join(self.temp_dir, 'mfe_mae_scatter.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        return filename
    
    def create_sequential_performance_chart(self):
        """Create sequential performance analysis (post-win/post-loss behavior)."""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Analyze sequential performance
        post_big_win_trades = []
        post_big_loss_trades = []
        all_trades_pnl = []
        
        big_win_threshold = 500  # Define what constitutes a "big" win
        big_loss_threshold = -300  # Define what constitutes a "big" loss
        
        for i in range(1, len(self.trades)):
            current_trade = self.trades[i]
            previous_trade = self.trades[i-1]
            
            if current_trade.pnl is not None and previous_trade.pnl is not None:
                all_trades_pnl.append(current_trade.pnl)
                
                # Check if previous trade was a big win
                if previous_trade.pnl >= big_win_threshold:
                    post_big_win_trades.append(current_trade.pnl)
                
                # Check if previous trade was a big loss
                if previous_trade.pnl <= big_loss_threshold:
                    post_big_loss_trades.append(current_trade.pnl)
        
        if not all_trades_pnl:
            ax.text(0.5, 0.5, 'Insufficient Trade Data for Sequential Analysis', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=16)
            ax.set_title('Sequential Performance Analysis', fontweight='bold', pad=20)
        else:
            # Calculate averages
            overall_avg = np.mean(all_trades_pnl) if all_trades_pnl else 0
            post_win_avg = np.mean(post_big_win_trades) if post_big_win_trades else 0
            post_loss_avg = np.mean(post_big_loss_trades) if post_big_loss_trades else 0
            
            categories = ['Overall Average', f'After Big Win\\n(>${big_win_threshold})', f'After Big Loss\\n(<${big_loss_threshold})']
            values = [overall_avg, post_win_avg, post_loss_avg]
            counts = [len(all_trades_pnl), len(post_big_win_trades), len(post_big_loss_trades)]
            
            # Color bars based on performance relative to overall average
            colors = []
            for val in values:
                if val > overall_avg * 1.1:
                    colors.append(self.colors['success'])
                elif val < overall_avg * 0.9:
                    colors.append(self.colors['danger'])
                else:
                    colors.append(self.colors['primary'])
            
            bars = ax.bar(categories, values, color=colors, alpha=0.8)
            ax.axhline(y=overall_avg, color='black', linestyle='--', alpha=0.7, label='Overall Average')
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            
            ax.set_title('Sequential Performance: Psychological Impact Analysis', fontweight='bold', pad=20)
            ax.set_ylabel('Average P&L per Trade ($)')
            ax.grid(True, axis='y', alpha=0.3)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            ax.legend()
            
            # Add value labels and trade counts
            for bar, val, count in zip(bars, values, counts):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + (abs(height) * 0.01),
                       f'${val:,.0f}\\n({count} trades)', ha='center', 
                       va='bottom' if height >= 0 else 'top',
                       fontweight='bold', fontsize=10)
        
        plt.tight_layout()
        filename = os.path.join(self.temp_dir, 'sequential_performance.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        return filename


class HeaderFooterDocTemplate(BaseDocTemplate):
    """
    Custom document template that supports mixed portrait/landscape pages,
    professional headers, footers, and a large central watermark.
    """
    def __init__(self, filename, **kwargs):
        super().__init__(filename, **kwargs)

        # --- PORTRAIT PAGE ---
        frame_portrait = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='portrait_frame')
        template_portrait = PageTemplate(id='Portrait', frames=[frame_portrait], onPage=self.on_page_portrait)

        # --- LANDSCAPE PAGE ---
        frame_landscape = Frame(self.leftMargin, self.bottomMargin, self.height, self.width, id='landscape_frame')
        template_landscape = PageTemplate(id='Landscape', frames=[frame_landscape], onPage=self.on_page_landscape, pagesize=landscape(self.pagesize))

        self.addPageTemplates([template_portrait, template_landscape])

    def on_page_portrait(self, canvas, doc):
        """ Handler for drawing elements on a portrait page. """
        self.draw_common_elements(canvas, doc, is_landscape=False)

    def on_page_landscape(self, canvas, doc):
        """ Handler for drawing elements on a landscape page. """
        self.draw_common_elements(canvas, doc, is_landscape=True)

    def draw_common_elements(self, canvas, doc, is_landscape):
        """ Draws elements common to all pages (header, footer, watermark). """
        canvas.saveState()
        page_width = self.height if is_landscape else self.width
        page_height = self.width if is_landscape else self.height

        self.add_watermark_background(canvas, doc, page_width, page_height)
        self.draw_header_logo(canvas, doc, page_width, page_height)
        self.draw_footer(canvas, doc, page_width)
        canvas.restoreState()

    def draw_header_logo(self, canvas, doc, page_width, page_height):
        """ Draws the main SVG logo at the top center of the page. """
        try:
            logo_path = os.path.join(current_app.root_path, 'static', 'images', 'logo.svg')
            if REPORTLAB_AVAILABLE and os.path.exists(logo_path):
                drawing = svg2rlg(logo_path)
                desired_width = 2.0 * inch
                scale_factor = desired_width / drawing.width
                drawing.width, drawing.height = desired_width, drawing.height * scale_factor
                drawing.scale(scale_factor, scale_factor)
                x_centered = doc.leftMargin + (page_width - drawing.width) / 2
                y_pos = doc.bottomMargin + page_height + 0.2 * inch
                renderPDF.draw(drawing, canvas, x_centered, y_pos)
            else: # Fallback to text
                canvas.setFont("Helvetica-Bold", 16)
                canvas.setFillColor(colors.HexColor('#003366'))
                canvas.drawCentredString(doc.leftMargin + page_width / 2, doc.bottomMargin + page_height + 0.5 * inch, "THE DAILY PROFILER")
        except Exception as e:
            current_app.logger.error(f"Failed to draw header logo: {e}")

    def draw_footer(self, canvas, doc, page_width):
        """ Draws the professional footer with page numbers. """
        try:
            canvas.setStrokeColor(colors.HexColor('#dee2e6'))
            canvas.setLineWidth(0.5)
            canvas.line(doc.leftMargin, doc.bottomMargin, doc.leftMargin + page_width, doc.bottomMargin)
            canvas.setFont("Helvetica", 9)
            canvas.setFillColor(colors.HexColor('#6c757d'))
            canvas.drawRightString(doc.leftMargin + page_width, doc.bottomMargin - 0.25 * inch, f"Page {doc.page}")
            canvas.drawString(doc.leftMargin, doc.bottomMargin - 0.25 * inch, "Confidential Trading Analysis Report")
        except Exception as e:
            current_app.logger.error(f"Failed to draw footer: {e}")

    def add_watermark_background(self, canvas, doc, page_width, page_height):
        """ Adds a larger, subtle logo watermark to the page center. """
        try:
            watermark_path = os.path.join(current_app.root_path, 'static', 'images', 'Pack_Trade_Group_Logo.png')
            if os.path.exists(watermark_path):
                canvas.saveState()
                canvas.setFillAlpha(0.08)
                img_width, img_height = 7 * inch, 7 * inch
                center_x = doc.leftMargin + (page_width - img_width) / 2
                center_y = doc.bottomMargin + (page_height - img_height) / 2
                canvas.drawImage(watermark_path, center_x, center_y, width=img_width, height=img_height, preserveAspectRatio=True, mask='auto')
                canvas.restoreState()
        except Exception as e:
            current_app.logger.error(f"Failed to draw watermark: {e}")


@trades_bp.route('/export_performance_report_pdf', methods=['GET'])
@login_required
def export_performance_report_pdf():
    """
    Export a comprehensive, multi-section performance analysis report as a
    professionally formatted PDF with a cover page, landscape sections for wide tables,
    a branded header/footer, and a watermark.
    """
    if not REPORTLAB_AVAILABLE:
        flash('PDF export is not available. Please install `reportlab` and `svglib` libraries.', 'warning')
        return redirect(url_for('trades.view_trades_list'))

    try:
        # Create and populate filter form properly
        filter_form = TradeFilterForm(request.args, meta={'csrf': False})
        filter_form, categorized_tags = _populate_filter_form_choices(filter_form)
        
        # Create base query for current user
        query = Trade.query.filter_by(user_id=current_user.id)
        
        # Apply filters directly (same logic as main view)
        active_filters = {}
        if filter_form.start_date.data:
            query = query.filter(Trade.trade_date >= filter_form.start_date.data)
            active_filters['start_date'] = filter_form.start_date.data
        if filter_form.end_date.data:
            query = query.filter(Trade.trade_date <= filter_form.end_date.data)
            active_filters['end_date'] = filter_form.end_date.data
        if filter_form.instrument.data:
            if filter_form.instrument.data.isdigit():
                instrument_id = int(filter_form.instrument.data)
                query = query.filter(Trade.instrument_id == instrument_id)
            else:
                query = query.filter(Trade.instrument_legacy == filter_form.instrument.data)
            active_filters['instrument'] = filter_form.instrument.data
        if filter_form.direction.data:
            query = query.filter(Trade.direction == filter_form.direction.data)
            active_filters['direction'] = filter_form.direction.data
        if filter_form.trading_model_id.data and filter_form.trading_model_id.data != 0:
            query = query.filter(Trade.trading_model_id == filter_form.trading_model_id.data)
            active_filters['trading_model_id'] = filter_form.trading_model_id.data
        
        # Handle additional filters from request.args
        how_closed_filter = request.args.get('how_closed')
        if how_closed_filter:
            query = query.filter(Trade.how_closed == how_closed_filter)
            active_filters['how_closed'] = how_closed_filter
        
        pnl_filter = request.args.get('pnl_filter')
        if pnl_filter:
            if pnl_filter == 'winners':
                query = query.filter(Trade.pnl > 0)
            elif pnl_filter == 'losers':
                query = query.filter(Trade.pnl < 0)
            elif pnl_filter == 'breakeven':
                query = query.filter(Trade.pnl == 0)
            active_filters['pnl_filter'] = pnl_filter
        
        # Debug: Log filter status
        current_app.logger.info(f"PDF Export - Active filters: {active_filters}")
        current_app.logger.info(f"PDF Export - Request args: {dict(request.args)}")
        
        trades = query.order_by(Trade.trade_date.desc()).all()
        current_app.logger.info(f"PDF Export - Total trades found: {len(trades)}")

        if not trades:
            flash('No trades found to generate a performance report.', 'warning')
            return redirect(url_for('trades.view_trades_list'))

        # Generate charts
        temp_dir = tempfile.mkdtemp()
        chart_generator = TradingChartsGenerator(trades, temp_dir)
        
        try:
            # Generate all charts
            chart_files = {}
            # Core performance charts
            chart_files['equity_curve'] = chart_generator.create_equity_curve_chart()
            chart_files['monthly_pnl'] = chart_generator.create_monthly_pnl_chart() 
            chart_files['model_performance'] = chart_generator.create_model_performance_chart()
            chart_files['pnl_distribution'] = chart_generator.create_pnl_distribution_chart()
            chart_files['direction_performance'] = chart_generator.create_direction_performance_chart()
            chart_files['win_loss_comparison'] = chart_generator.create_win_loss_comparison_chart()
            chart_files['r_multiple_distribution'] = chart_generator.create_r_multiple_distribution_chart()
            
            # Advanced behavioral and timing charts
            chart_files['behavioral_tags'] = chart_generator.create_behavioral_tags_chart()
            chart_files['hourly_heatmap'] = chart_generator.create_hourly_heatmap_chart()
            chart_files['trade_duration'] = chart_generator.create_trade_duration_chart()
            chart_files['position_size'] = chart_generator.create_position_size_chart()
            chart_files['rolling_metrics'] = chart_generator.create_rolling_metrics_chart()
            chart_files['mfe_mae_scatter'] = chart_generator.create_mfe_mae_scatter_chart()
            chart_files['sequential_performance'] = chart_generator.create_sequential_performance_chart()
            
        except Exception as chart_error:
            current_app.logger.warning(f"Chart generation error: {chart_error}")
            chart_files = {}

        buffer = io.BytesIO()
        doc = HeaderFooterDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=70, bottomMargin=50)

        # ======================================================================
        # STYLES DEFINITION
        # ======================================================================
        styles = getSampleStyleSheet()

        # --- Cover Page Styles ---
        cover_title_style = ParagraphStyle('CoverTitle', parent=styles['h1'], fontSize=28, alignment=1, spaceAfter=20,
                                           fontName='Helvetica-Bold', textColor=colors.HexColor('#003366'))
        cover_subtitle_style = ParagraphStyle('CoverSubtitle', parent=styles['h2'], fontSize=16, alignment=1,
                                              spaceAfter=40, fontName='Helvetica', textColor=colors.HexColor('#333333'))
        cover_info_style = ParagraphStyle('CoverInfo', parent=styles['Normal'], fontSize=11, alignment=1, spaceAfter=12,
                                          fontName='Helvetica', leading=16)
        cover_footer_style = ParagraphStyle('CoverFooter', parent=styles['Normal'], fontSize=9, alignment=1,
                                            textColor=colors.grey, fontName='Helvetica-Oblique')

        # --- Content Styles ---
        heading_style = ParagraphStyle('CustomHeading', parent=styles['h2'], fontSize=14, spaceBefore=18, spaceAfter=12,
                                       textColor=colors.HexColor('#003366'))
        subheading_style = ParagraphStyle('CustomSubHeading', parent=styles['h3'], fontSize=11, spaceBefore=6,
                                          spaceAfter=6, textColor=colors.HexColor('#333333'))

        # --- Table Styles ---
        cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=7.5, leading=10)
        header_cell_style = ParagraphStyle('HeaderCellStyle', parent=styles['Normal'], fontSize=8,
                                           fontName='Helvetica-Bold', textColor=colors.white)

        def create_pro_table_style():
            return TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#495057')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.darkgrey),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ])

        story = []

        # ======================================================================
        # COVER PAGE
        # ======================================================================
        story.append(Spacer(1, 2 * inch))
        story.append(Paragraph("Comprehensive Trading", cover_title_style))
        
        # Add filter status indicator to title
        if active_filters:
            story.append(Paragraph("Performance Analysis (Filtered Dataset)", cover_title_style))
        else:
            story.append(Paragraph("Performance Analysis (Complete Dataset)", cover_title_style))
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph("The Daily Profiler Trading Journal", cover_subtitle_style))
        story.append(Spacer(1, 1 * inch))

        story.append(Paragraph(f"<b>Account:</b> {current_user.username}", cover_info_style))
        story.append(Paragraph(
            f"<b>Analysis Period:</b> {trades[0].trade_date.strftime('%B %d, %Y')} to {trades[-1].trade_date.strftime('%B %d, %Y')}",
            cover_info_style))
        story.append(
            Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", cover_info_style))
        story.append(Paragraph(f"<b>Total Trades Analyzed:</b> {len(trades):,}", cover_info_style))

        story.append(Spacer(1, 2.5 * inch))
        story.append(Paragraph("This report contains proprietary and confidential trading data.", cover_footer_style))
        story.append(PageBreak())

        # ======================================================================
        # CALCULATE BASE STATISTICS
        # ======================================================================
        total_trades = len(trades)
        trades_with_pnl = [t for t in trades if t.pnl is not None]
        profitable_trades = len([t for t in trades_with_pnl if t.pnl > 0])
        losing_trades = len([t for t in trades_with_pnl if t.pnl < 0])
        breakeven_trades = len([t for t in trades_with_pnl if t.pnl == 0])
        strike_rate = (profitable_trades / len(trades_with_pnl) * 100) if trades_with_pnl else 0
        total_pnl = sum(t.pnl for t in trades_with_pnl)

        winning_pnls = [t.pnl for t in trades_with_pnl if t.pnl > 0]
        losing_pnls = [t.pnl for t in trades_with_pnl if t.pnl < 0]
        avg_winner = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
        avg_loser = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0
        profit_factor = abs(sum(winning_pnls) / sum(losing_pnls)) if losing_pnls and sum(losing_pnls) != 0 else float(
            'inf')

        # ======================================================================
        # EXECUTIVE SUMMARY
        # ======================================================================
        story.append(Paragraph("Executive Summary Statistics", heading_style))
        summary_data = [
            ['Metric', 'Value', 'Analysis'],
            ['Total Trades', f'{total_trades:,}', 'Total sample size of trading activity.'],
            ['Profitable Trades', f'{profitable_trades:,}',
             f'{profitable_trades / total_trades * 100:.1f}% of all trades.'],
            ['Losing Trades', f'{losing_trades:,}', f'{losing_trades / total_trades * 100:.1f}% of all trades.'],
            ['Breakeven Trades', f'{breakeven_trades:,}',
             f'{breakeven_trades / total_trades * 100:.1f}% of all trades.'],
            ['Strike Rate', f'{strike_rate:.2f}%', 'Percentage of trades that were profitable.'],
            ['Total Net P&L', f'${total_pnl:,.2f}', 'Cumulative profit and loss over the period.'],
            ['Average Winner', f'${avg_winner:,.2f}', 'The average gain from a winning trade.'],
            ['Average Loser', f'${avg_loser:,.2f}', 'The average loss from a losing trade.'],
            ['Largest Winner', f'${max(winning_pnls, default=0):,.2f}', 'The best single trade performance.'],
            ['Largest Loser', f'${min(losing_pnls, default=0):,.2f}', 'The worst single trade performance.'],
            ['Profit Factor', f'{profit_factor:.2f}', 'Gross profit divided by gross loss.']
        ]
        summary_table = Table(summary_data, colWidths=[2.0 * inch, 1.7 * inch, 3.3 * inch])
        summary_table.setStyle(create_pro_table_style())
        story.append(summary_table)
        story.append(PageBreak())

        # ======================================================================
        # PERFORMANCE VISUALIZATION SECTION
        # ======================================================================
        story.append(Paragraph("Performance Visualization & Analysis", heading_style))
        story.append(Spacer(1, 12))
        
        # Add charts if they were generated successfully
        if chart_files:
            # Equity Curve - Most Important Chart
            if 'equity_curve' in chart_files and os.path.exists(chart_files['equity_curve']):
                story.append(Paragraph("Equity Curve Analysis", subheading_style))
                story.append(Paragraph("The equity curve shows your account's growth trajectory over time, with the drawdown chart below showing risk periods.", 
                                     styles['Normal']))
                equity_img = Image(chart_files['equity_curve'], width=7*inch, height=5*inch)
                story.append(equity_img)
                story.append(Spacer(1, 12))
            
            # Monthly Performance
            if 'monthly_pnl' in chart_files and os.path.exists(chart_files['monthly_pnl']):
                story.append(Paragraph("Monthly Performance Breakdown", subheading_style))
                story.append(Paragraph("Monthly P&L shows consistency and seasonality patterns in your trading performance.", 
                                     styles['Normal']))
                monthly_img = Image(chart_files['monthly_pnl'], width=7*inch, height=4*inch)
                story.append(monthly_img)
                story.append(Spacer(1, 12))
            
            story.append(PageBreak())
            
            # Model Performance Comparison
            if 'model_performance' in chart_files and os.path.exists(chart_files['model_performance']):
                story.append(Paragraph("Trading Model Performance Analysis", subheading_style))
                story.append(Paragraph("This analysis compares the profitability and win rates of your different trading strategies.", 
                                     styles['Normal']))
                model_img = Image(chart_files['model_performance'], width=7*inch, height=4*inch)
                story.append(model_img)
                story.append(Spacer(1, 12))
            
            # P&L Distribution
            if 'pnl_distribution' in chart_files and os.path.exists(chart_files['pnl_distribution']):
                story.append(Paragraph("Trade Outcome Distribution", subheading_style))
                story.append(Paragraph("The P&L distribution histogram reveals the frequency and size of your winning and losing trades.", 
                                     styles['Normal']))
                pnl_dist_img = Image(chart_files['pnl_distribution'], width=7*inch, height=4*inch)
                story.append(pnl_dist_img)
                story.append(Spacer(1, 12))
            
            story.append(PageBreak())
            
            # Direction Performance
            if 'direction_performance' in chart_files and os.path.exists(chart_files['direction_performance']):
                story.append(Paragraph("Long vs Short Performance Analysis", subheading_style))
                story.append(Paragraph("This chart compares your performance when trading long versus short positions.", 
                                     styles['Normal']))
                direction_img = Image(chart_files['direction_performance'], width=7*inch, height=4*inch)
                story.append(direction_img)
                story.append(Spacer(1, 12))
            
            # Win/Loss Comparison
            if 'win_loss_comparison' in chart_files and os.path.exists(chart_files['win_loss_comparison']):
                story.append(Paragraph("Average Winner vs Average Loser", subheading_style))
                story.append(Paragraph("This comparison shows the risk-reward relationship in your trading system.", 
                                     styles['Normal']))
                winloss_img = Image(chart_files['win_loss_comparison'], width=7*inch, height=4*inch)
                story.append(winloss_img)
                story.append(Spacer(1, 12))
            
            story.append(PageBreak())
            
            # R-Multiple Distribution
            if 'r_multiple_distribution' in chart_files and os.path.exists(chart_files['r_multiple_distribution']):
                story.append(Paragraph("Risk-Adjusted Returns (R-Multiple) Analysis", subheading_style))
                story.append(Paragraph("R-multiples normalize trade outcomes by initial risk, showing how many 'R' units of profit or loss each trade generated.", 
                                     styles['Normal']))
                r_mult_img = Image(chart_files['r_multiple_distribution'], width=7*inch, height=4*inch)
                story.append(r_mult_img)
                story.append(Spacer(1, 12))
            
            story.append(PageBreak())
            
            # ======================================================================
            # BEHAVIORAL & PSYCHOLOGICAL ANALYSIS SECTION
            # ======================================================================
            story.append(Paragraph("Behavioral & Psychological Analysis", heading_style))
            story.append(Spacer(1, 12))
            
            # Behavioral Tags Performance
            if 'behavioral_tags' in chart_files and os.path.exists(chart_files['behavioral_tags']):
                story.append(Paragraph("Performance by Behavioral Tags", subheading_style))
                story.append(Paragraph("This analysis reveals the financial impact of different trading behaviors and psychological states.", 
                                     styles['Normal']))
                tags_img = Image(chart_files['behavioral_tags'], width=7*inch, height=6*inch)
                story.append(tags_img)
                story.append(Spacer(1, 12))
            
            # Sequential Performance Analysis
            if 'sequential_performance' in chart_files and os.path.exists(chart_files['sequential_performance']):
                story.append(Paragraph("Sequential Performance: Post-Win/Post-Loss Analysis", subheading_style))
                story.append(Paragraph("This chart investigates revenge trading and overconfidence by analyzing performance after big wins and losses.", 
                                     styles['Normal']))
                seq_img = Image(chart_files['sequential_performance'], width=7*inch, height=4*inch)
                story.append(seq_img)
                story.append(Spacer(1, 12))
            
            story.append(PageBreak())
            
            # ======================================================================
            # TIMING & EXECUTION ANALYSIS SECTION
            # ======================================================================
            story.append(Paragraph("Timing & Execution Analysis", heading_style))
            story.append(Spacer(1, 12))
            
            # Hourly Performance Heatmap
            if 'hourly_heatmap' in chart_files and os.path.exists(chart_files['hourly_heatmap']):
                story.append(Paragraph("Hourly Performance Heatmap", subheading_style))
                story.append(Paragraph("This heatmap identifies your most profitable hours and days, revealing optimal trading windows.", 
                                     styles['Normal']))
                heatmap_img = Image(chart_files['hourly_heatmap'], width=7*inch, height=4*inch)
                story.append(heatmap_img)
                story.append(Spacer(1, 12))
            
            # Trade Duration Analysis
            if 'trade_duration' in chart_files and os.path.exists(chart_files['trade_duration']):
                story.append(Paragraph("Trade Duration: Winners vs Losers", subheading_style))
                story.append(Paragraph("This analysis shows whether you're letting winners run and cutting losers quickly.", 
                                     styles['Normal']))
                duration_img = Image(chart_files['trade_duration'], width=7*inch, height=4*inch)
                story.append(duration_img)
                story.append(Spacer(1, 12))
            
            story.append(PageBreak())
            
            # ======================================================================
            # RISK & SIZING ANALYSIS SECTION
            # ======================================================================
            story.append(Paragraph("Risk & Position Sizing Analysis", heading_style))
            story.append(Spacer(1, 12))
            
            # Position Size Performance
            if 'position_size' in chart_files and os.path.exists(chart_files['position_size']):
                story.append(Paragraph("Performance by Position Size", subheading_style))
                story.append(Paragraph("This chart reveals how your performance changes with different position sizes and whether psychological factors affect larger trades.", 
                                     styles['Normal']))
                size_img = Image(chart_files['position_size'], width=7*inch, height=4*inch)
                story.append(size_img)
                story.append(Spacer(1, 12))
            
            # MFE vs MAE Scatter Plot
            if 'mfe_mae_scatter' in chart_files and os.path.exists(chart_files['mfe_mae_scatter']):
                story.append(Paragraph("Trade Efficiency: Maximum Favorable vs Adverse Excursion", subheading_style))
                story.append(Paragraph("This professional scatter plot shows how much profit you're leaving on the table and optimal stop-loss placement.", 
                                     styles['Normal']))
                mfe_mae_img = Image(chart_files['mfe_mae_scatter'], width=7*inch, height=5*inch)
                story.append(mfe_mae_img)
                story.append(Spacer(1, 12))
            
            story.append(PageBreak())
            
            # ======================================================================
            # PERFORMANCE EVOLUTION SECTION
            # ======================================================================
            story.append(Paragraph("Performance Evolution & Consistency", heading_style))
            story.append(Spacer(1, 12))
            
            # Rolling Performance Metrics
            if 'rolling_metrics' in chart_files and os.path.exists(chart_files['rolling_metrics']):
                story.append(Paragraph("Rolling Performance Metrics Over Time", subheading_style))
                story.append(Paragraph("These rolling metrics show whether your trading edge is improving, declining, or remaining consistent over time.", 
                                     styles['Normal']))
                rolling_img = Image(chart_files['rolling_metrics'], width=7*inch, height=6*inch)
                story.append(rolling_img)
                story.append(Spacer(1, 12))
            
            story.append(PageBreak())
        
        else:
            story.append(Paragraph("Charts could not be generated for this report. Statistical analysis continues below.", 
                                 styles['Normal']))
            story.append(PageBreak())

        # ======================================================================
        # COMPREHENSIVE TRADE DETAILS (LANDSCAPE SECTION)
        # ======================================================================
        story.append(Paragraph("Comprehensive Trade Details", heading_style))
        story.append(Paragraph("Complete record of all trading activity with detailed metrics.", subheading_style))
        story.append(NextPageTemplate('Landscape'))
        story.append(PageBreak())

        trade_headers = ['Date', 'Day', 'Inst', 'Dir', 'Pos', 'Avg Entry', 'Avg Exit',
                         'P&L', 'R-Val', 'Risk', 'W/L', 'SL', 'Target', 'Model', 'Tags']

        trade_data = [[Paragraph(h, header_cell_style) for h in trade_headers]]
        for trade in trades:
            tags_str = ', '.join([tag.name for tag in trade.tags])
            win_loss = 'W' if (trade.pnl or 0) > 0 else ('L' if (trade.pnl or 0) < 0 else 'B/E')
            row = [
                Paragraph(trade.trade_date.strftime('%d-%b-%y'), cell_style),
                Paragraph(trade.trade_date.strftime('%a'), cell_style),
                Paragraph(str(trade.instrument or trade.instrument_legacy or 'N/A'), cell_style),
                Paragraph(str(trade.direction)[:4], cell_style),
                Paragraph(str(trade.total_contracts_entered or 0), cell_style),
                Paragraph(f"{trade.average_entry_price or 0:.2f}", cell_style),
                Paragraph(f"{trade.average_exit_price or 0:.2f}", cell_style),
                Paragraph(f"${trade.pnl or 0:,.2f}", cell_style),
                Paragraph(f"{trade.pnl_in_r or 0:.2f}", cell_style),
                Paragraph(f"${trade.dollar_risk or 0:,.0f}", cell_style),
                Paragraph(win_loss, cell_style),
                Paragraph(f"{trade.initial_stop_loss or 0:.2f}", cell_style),
                Paragraph(f"{trade.terminus_target or 0:.2f}", cell_style),
                Paragraph(trade.trading_model.name if trade.trading_model else 'N/A', cell_style),
                Paragraph(tags_str, cell_style),
            ]
            trade_data.append(row)

        col_widths_landscape = [0.7 * inch, 0.4 * inch, 0.4 * inch, 0.4 * inch, 0.4 * inch, 0.7 * inch,
                                0.7 * inch, 0.7 * inch, 0.5 * inch, 0.7 * inch, 0.4 * inch, 0.7 * inch,
                                0.7 * inch, 1.7 * inch, 1.7 * inch]
        trade_detail_table = Table(trade_data, colWidths=col_widths_landscape, repeatRows=1)
        trade_detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#495057')),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.darkgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
        ]))
        story.append(trade_detail_table)

        # --- Switch back to Portrait for remaining sections ---
        story.append(NextPageTemplate('Portrait'))
        story.append(PageBreak())

        # ======================================================================
        # MODEL PERFORMANCE ANALYSIS
        # ======================================================================
        story.append(Paragraph("Model Performance Analysis", heading_style))
        model_stats = {}
        for trade in trades:
            model_name = trade.trading_model.name if trade.trading_model else 'No Model'
            if model_name not in model_stats:
                model_stats[model_name] = {'trades': 0, 'pnl': 0, 'wins': 0, 'all_pnls': []}
            stats = model_stats[model_name]
            stats['trades'] += 1
            if trade.pnl is not None:
                stats['pnl'] += trade.pnl
                stats['all_pnls'].append(trade.pnl)
                if trade.pnl > 0:
                    stats['wins'] += 1

        model_data = [['Model', 'Trades', 'Total P&L', 'Win Rate', 'Avg P&L', 'Best Trade', 'Worst Trade']]
        for model, stats in sorted(model_stats.items()):
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] else 0
            avg_pnl = stats['pnl'] / stats['trades'] if stats['trades'] else 0
            best_trade = max(stats['all_pnls']) if stats['all_pnls'] else 0
            worst_trade = min(stats['all_pnls']) if stats['all_pnls'] else 0
            model_data.append([
                model, f"{stats['trades']}", f"${stats['pnl']:,.2f}", f"{win_rate:.1f}%",
                f"${avg_pnl:,.2f}", f"${best_trade:,.2f}", f"${worst_trade:,.2f}"
            ])
        model_table = Table(model_data,
                            colWidths=[1.7 * inch, 0.8 * inch, 1.2 * inch, 1.0 * inch, 1.0 * inch, 1.1 * inch,
                                       1.2 * inch])
        model_table.setStyle(create_pro_table_style())
        story.append(model_table)
        story.append(Spacer(1, 0.2 * inch))

        # ======================================================================
        # DAY OF WEEK & TIME OF DAY ANALYSIS
        # ======================================================================
        story.append(Paragraph("Performance by Time", heading_style))
        story.append(
            Paragraph("Analysis of performance based on the day of the week and hour of entry.", subheading_style))

        # Day of Week
        dow_stats = {d: {'trades': 0, 'pnl': 0, 'wins': 0} for d in
                     ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']}
        for trade in trades:
            dow = trade.trade_date.strftime('%A')
            if dow in dow_stats:
                dow_stats[dow]['trades'] += 1
                if trade.pnl is not None:
                    dow_stats[dow]['pnl'] += trade.pnl
                    if trade.pnl > 0: dow_stats[dow]['wins'] += 1

        dow_data = [['Day', 'Trades', 'Total P&L', 'Win Rate', 'Avg P&L']]
        for day, stats in dow_stats.items():
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            avg_pnl = stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
            dow_data.append(
                [day, f"{stats['trades']}", f"${stats['pnl']:,.2f}", f"{win_rate:.1f}%", f"${avg_pnl:,.2f}"])
        dow_table = Table(dow_data)
        dow_table.setStyle(create_pro_table_style())
        story.append(dow_table)
        story.append(PageBreak())

        # ======================================================================
        # RISK AND STREAK ANALYSIS
        # ======================================================================
        story.append(Paragraph("Risk & Drawdown Analysis", heading_style))

        # Max Drawdown & Risk Metrics
        all_pnls = [t.pnl for t in trades_with_pnl]
        if all_pnls:
            std_dev = statistics.stdev(all_pnls) if len(all_pnls) > 1 else 0
            avg_pnl_per_trade = statistics.mean(all_pnls)
            sharpe_ratio = avg_pnl_per_trade / std_dev if std_dev > 0 else 0

            running_total, peak, max_drawdown = 0, 0, 0
            for pnl in all_pnls:
                running_total += pnl
                if running_total > peak: peak = running_total
                drawdown = peak - running_total
                if drawdown > max_drawdown: max_drawdown = drawdown

            risk_data = [
                ['Risk Metric', 'Value', 'Interpretation'],
                ['Standard Deviation of P&L', f'${std_dev:,.2f}', 'Volatility of returns.'],
                ['Maximum Drawdown', f'${max_drawdown:,.2f}', 'Largest peak-to-trough decline in equity.'],
                ['Sharpe Ratio (Simplified)', f'{sharpe_ratio:.3f}', 'Risk-adjusted return (higher is better).'],
            ]
            risk_table = Table(risk_data, colWidths=[2.0 * inch, 1.7 * inch, 3.3 * inch])
            risk_table.setStyle(create_pro_table_style())
            story.append(risk_table)
            story.append(Spacer(1, 0.3 * inch))

        # Streak Analysis
        story.append(Paragraph("Winning & Losing Streaks", subheading_style))
        win_streak, loss_streak, max_win_streak, max_loss_streak = 0, 0, 0, 0
        for trade in trades_with_pnl:
            if trade.pnl > 0:
                win_streak += 1
                loss_streak = 0
            elif trade.pnl < 0:
                loss_streak += 1
                win_streak = 0
            max_win_streak = max(max_win_streak, win_streak)
            max_loss_streak = max(max_loss_streak, loss_streak)

        streak_data = [['Streak Type', 'Maximum Consecutive'], ['Winning Streaks', f'{max_win_streak} Trades'],
                       ['Losing Streaks', f'{max_loss_streak} Trades']]
        streak_table = Table(streak_data)
        streak_table.setStyle(create_pro_table_style())
        story.append(streak_table)

        # ======================================================================
        # BUILD THE PDF
        # ======================================================================
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Clean up temporary chart files
        try:
            if 'temp_dir' in locals():
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as cleanup_error:
            current_app.logger.warning(f"Failed to clean up temp files: {cleanup_error}")

        # Create filename based on filter status
        if active_filters:
            filename = f"professional_performance_analysis_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        else:
            filename = f"professional_performance_analysis_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return Response(pdf_data, mimetype="application/pdf",
                        headers={"Content-Disposition": f"attachment;filename={filename}"})

    except Exception as e:
        # Clean up temporary files on error
        try:
            if 'temp_dir' in locals():
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as cleanup_error:
            current_app.logger.warning(f"Failed to clean up temp files on error: {cleanup_error}")
            
        current_app.logger.error(f'Error generating comprehensive PDF report: {e}', exc_info=True)
        flash(f'An error occurred while generating the PDF report: {str(e)}', 'danger')
        return redirect(url_for('trades.view_trades_list'))


@trades_bp.route('/image/<int:image_id>/delete', methods=['POST', 'DELETE'])
@login_required
def delete_trade_image(image_id):
    """Delete an individual trade image."""
    try:
        # Get the trade image
        trade_image = TradeImage.query.get_or_404(image_id)
        
        # Security check: ensure user owns the trade or is admin
        if trade_image.user_id != current_user.id and current_user.role.name != 'ADMIN':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        # Get the file path for deletion
        file_path = trade_image.full_disk_path
        
        # Delete the database record
        db.session.delete(trade_image)
        db.session.commit()
        
        # Delete the physical file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                current_app.logger.info(f'Deleted trade image file: {file_path}')
            except Exception as file_error:
                current_app.logger.warning(f'Failed to delete image file {file_path}: {file_error}')
        
        return jsonify({
            'success': True,
            'message': 'Trade image deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting trade image {image_id}: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'An error occurred while deleting the image'
        }), 500


@trades_bp.route('/chart-screenshot/<int:trade_id>')
@login_required
def generate_chart_screenshot(trade_id):
    """Generate a screenshot of the chart URL for preview purposes."""
    try:
        # Get the trade and verify ownership
        trade = Trade.query.get_or_404(trade_id)
        if trade.user_id != current_user.id and current_user.role.name != 'ADMIN':
            abort(403)
        
        if not trade.screenshot_link:
            return jsonify({'success': False, 'error': 'No chart URL available'}), 400
        
        # Try different screenshot services
        screenshot_services = [
            f"https://api.microlink.io/screenshot?url={trade.screenshot_link}&viewport.width=1200&viewport.height=800&type=png",
            f"https://image.thum.io/get/width/1200/crop/800/noanimate/{trade.screenshot_link}",
            f"https://mini.s-shot.ru/1200x800/PNG/1200/Z100/?{trade.screenshot_link}"
        ]
        
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        # Configure session with retries
        session = requests.Session()
        retry_strategy = Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Try each service
        for service_url in screenshot_services:
            try:
                current_app.logger.info(f"Trying screenshot service: {service_url}")
                response = session.get(service_url, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200 and response.headers.get('content-type', '').startswith('image/'):
                    current_app.logger.info(f"Screenshot generated successfully")
                    return Response(
                        response.content,
                        mimetype=response.headers.get('content-type', 'image/png'),
                        headers={
                            'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                            'Content-Disposition': f'inline; filename="chart-{trade_id}.png"'
                        }
                    )
                    
            except requests.RequestException as e:
                current_app.logger.warning(f"Screenshot service failed: {e}")
                continue
        
        # If all services fail, return error
        current_app.logger.warning("All screenshot services failed")
        return jsonify({'success': False, 'error': 'Screenshot generation failed'}), 503
        
    except Exception as e:
        current_app.logger.error(f'Error generating chart screenshot: {str(e)}')
        return jsonify({'success': False, 'error': 'Internal server error'}), 500