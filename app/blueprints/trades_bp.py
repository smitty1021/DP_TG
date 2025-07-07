
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app, Response, abort)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from flask_wtf.csrf import generate_csrf
import os
import uuid
import csv
import io
from datetime import date as py_date, datetime as py_datetime, time as py_time
from datetime import datetime
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


def _populate_trade_form_choices(form):
    form.trading_model_id.choices = [(0, 'Select Model')] + \
                                    [(tm.id, tm.name) for tm in
                                     TradingModel.query.filter_by(user_id=current_user.id, is_active=True).order_by(
                                         TradingModel.name).all()]
    if hasattr(form, 'news_event_select'):
        form.news_event_select.choices = [('', '-- None --')] + [(event, event) for event in get_news_event_options() if
                                                                 event and event.lower() != 'none']
    return form


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


    # Handle tags filter - support multiple tags with AND logic
    selected_tags = request.args.getlist('tags')  # Get list of selected tag IDs
    if selected_tags and any(tag.strip() for tag in selected_tags if tag):  # Check if any non-empty tags
        # Filter tags to only non-empty values
        valid_tag_ids = [int(tag) for tag in selected_tags if tag.strip() and tag.isdigit()]

        if valid_tag_ids:
            # Use AND logic - show trades that have ALL of the selected tags
            for tag_id in valid_tag_ids:
                query = query.filter(Trade.tags.any(Tag.id == tag_id))

    selected_tag_details = []
    if selected_tags:
        valid_tag_ids = [int(tag) for tag in selected_tags if tag.strip() and tag.isdigit()]
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
                                       default_trade_date=py_date.today().strftime('%Y-%m-%d'))

            # Get the instrument object
            instrument_obj = Instrument.query.get(int(instrument_id))
            if not instrument_obj:
                flash('Invalid instrument selected.', 'danger')
                return render_template('trades/add_trade.html',
                                       title='Log New Trade',
                                       form=form,
                                       instrument_point_values=instrument_point_values,
                                       default_trade_date=py_date.today().strftime('%Y-%m-%d'))

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
            new_trade.mae = _parse_form_float(form.mae.data)
            new_trade.mfe = _parse_form_float(form.mfe.data)
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
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(file_path)

                        new_image = TradeImage(
                            trade_id=new_trade.id,
                            filename=filename,
                            filepath=unique_filename
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
                           default_trade_date=py_date.today().strftime('%Y-%m-%d'))

# --- VIEW TRADE DETAIL ---
@trades_bp.route('/<int:trade_id>/view')
@login_required
def view_trade_detail(trade_id):
    trade = db.get_or_404(Trade, trade_id)
    if trade.user_id != current_user.id:
        abort(403)
    return render_template('trades/view_trade_detail.html', title="Trade Details", trade=trade)


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
            trade_to_edit.mae = _parse_form_float(form.mae.data)
            trade_to_edit.mfe = _parse_form_float(form.mfe.data)
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
                        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(file_path)

                        new_image = TradeImage(
                            trade_id=trade_to_edit.id,
                            filename=filename,
                            filepath=unique_filename
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

    return render_template('trades/edit_trade.html',
                           title="Edit Trade",
                           form=form,
                           trade=trade_to_edit,
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
    filter_form = TradeFilterForm(request.args, meta={'csrf': False})
    _populate_filter_form_choices(filter_form)

    query = Trade.query.filter_by(user_id=current_user.id)
    if filter_form.start_date.data: query = query.filter(Trade.trade_date >= filter_form.start_date.data)
    if filter_form.end_date.data: query = query.filter(Trade.trade_date <= filter_form.end_date.data)
    if filter_form.instrument.data: query = query.filter(Trade.instrument == filter_form.instrument.data)
    if filter_form.direction.data: query = query.filter(Trade.direction == filter_form.direction.data)
    if filter_form.trading_model_id.data and filter_form.trading_model_id.data != 0:
        query = query.filter(Trade.trading_model_id == filter_form.trading_model_id.data)
    if filter_form.tags.data: query = query.filter(Trade.tags == filter_form.tags.data)

    trades_to_export = query.order_by(Trade.trade_date.asc()).all()

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
            trade.initial_stop_loss, trade.terminus_target, trade.mae, trade.mfe,
            trade.how_closed, trade.trading_model.name if trade.trading_model else '',
            ', '.join([tag.name for tag in trade.tags]) if trade.tags else '', trade.trade_notes, trade.overall_analysis_notes, trade.trade_management_notes,
            trade.errors_notes, trade.improvements_notes, trade.screenshot_link
        ])
    output.seek(0)
    return Response(output, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=trades_export.csv"})


# --- IMPORT TRADES ---
# In app/blueprints/trades_bp.py

# ... (other imports and routes as before) ...

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
                    new_trade.mae = _parse_form_float(row.get(header_map['mae']))
                    new_trade.mfe = _parse_form_float(row.get(header_map['mfe']))
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