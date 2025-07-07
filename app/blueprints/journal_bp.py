from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app, abort, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import date as py_date, datetime as py_datetime, timedelta

from app.extensions import db
from app.models import DailyJournal, DailyJournalImage, Trade, P12UsageStats, P12Scenario
from app.forms import DailyJournalForm  # Assuming DailyJournalForm is in app.forms
from app.utils import record_activity  # Assuming record_activity is in app.utils

journal_bp = Blueprint('journal', __name__,
                       template_folder='../templates/journal',
                       url_prefix='/journal')


def _is_allowed_image(filename):
    """Checks if the filename has an allowed image extension."""
    # Duplicated from trades_bp for now, consider moving to utils.py if widely used
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config.get('ALLOWED_IMAGE_EXTENSIONS',
                                                                     {'png', 'jpg', 'jpeg', 'gif'})


def _handle_daily_journal_image_uploads(form, daily_journal_instance, image_field_name, image_type_tag):
    """Helper to handle image uploads for a daily journal field."""
    if form[image_field_name].data:
        for image_file in form[image_field_name].data:
            if image_file and _is_allowed_image(image_file.filename):
                original_filename = secure_filename(image_file.filename)
                file_ext = os.path.splitext(original_filename)[1].lower()
                unique_filename = f"{uuid.uuid4().hex}{file_ext}"
                upload_folder = current_app.config['UPLOAD_FOLDER']
                # Consider a subfolder for journal images:
                # journal_image_upload_folder = os.path.join(upload_folder, 'daily_journal_images')
                # if not os.path.exists(journal_image_upload_folder): os.makedirs(journal_image_upload_folder)
                # file_path = os.path.join(journal_image_upload_folder, unique_filename)
                file_path = os.path.join(upload_folder, unique_filename)  # Using main UPLOAD_FOLDER for now

                try:
                    image_file.save(file_path)
                    dj_image = DailyJournalImage(
                        daily_journal_id=daily_journal_instance.id,
                        user_id=current_user.id,
                        filename=original_filename,
                        filepath=unique_filename,
                        filesize=os.path.getsize(file_path),
                        mime_type=image_file.mimetype,
                        image_type=image_type_tag
                    )
                    db.session.add(dj_image)
                except Exception as e_save:
                    current_app.logger.error(
                        f"Failed to save journal image {original_filename} for journal {daily_journal_instance.id}: {e_save}",
                        exc_info=True)
                    flash(f"Could not save image: {original_filename}", "warning")
            elif image_file:
                flash(f"Image type not allowed for journal image: {image_file.filename}", "warning")


@journal_bp.route('/daily', methods=['GET'])
@journal_bp.route('/daily/<string:date_str>', methods=['GET', 'POST'])
@login_required
def manage_daily_journal(date_str=None):
    if date_str is None:
        # Default to today's date if no date is provided
        target_date = py_date.today()
        # Redirect to the date-specific URL to make it bookmarkable and consistent
        return redirect(url_for('journal.manage_daily_journal', date_str=target_date.strftime('%Y-%m-%d')))
    else:
        try:
            target_date = py_datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
            return redirect(url_for('journal.manage_daily_journal', date_str=py_date.today().strftime('%Y-%m-%d')))

    # Try to find existing journal for this date and user
    daily_journal = DailyJournal.query.filter_by(user_id=current_user.id, journal_date=target_date).first()

    form_obj = daily_journal if daily_journal else None  # Pass existing journal to form for pre-population
    form = DailyJournalForm(obj=form_obj)

    if request.method == 'POST' and form.validate_on_submit():
        if daily_journal is None:  # Create new journal entry
            daily_journal = DailyJournal(user_id=current_user.id, journal_date=target_date)
            db.session.add(daily_journal)
            action_desc = "created"
        else:  # Update existing
            action_desc = "updated"

        # Store previous scenario ID for comparison
        previous_scenario_id = daily_journal.p12_scenario_id

        # Populate DailyJournal object from form
        form.populate_obj(daily_journal)
        daily_journal.journal_date = target_date

        # Handle P12 scenario selection and track usage
        if form.p12_scenario_id.data and form.p12_scenario_id.data != 0:
            daily_journal.p12_scenario_id = form.p12_scenario_id.data

            # Track usage - only if this is a NEW selection or change
            if form.p12_scenario_id.data != previous_scenario_id:
                from app.models import P12Scenario
                scenario = P12Scenario.query.get(form.p12_scenario_id.data)
                if scenario:
                    # Increment the basic counter
                    scenario.increment_usage()

                    # Create detailed usage stats record
                    usage_stat = P12UsageStats(
                        user_id=current_user.id,
                        p12_scenario_id=form.p12_scenario_id.data,
                        journal_date=target_date,
                        market_session='pre-market',  # Assuming this is selected during pre-market prep
                        p12_high=form.p12_high.data,
                        p12_mid=form.p12_mid.data,
                        p12_low=form.p12_low.data
                    )
                    db.session.add(usage_stat)
        else:
            daily_journal.p12_scenario_id = None

        # Handle P12 levels
        daily_journal.p12_high = form.p12_high.data
        daily_journal.p12_mid = form.p12_mid.data
        daily_journal.p12_low = form.p12_low.data
        daily_journal.p12_notes = form.p12_notes.data

        try:
            db.session.flush()  # To get daily_journal.id if it's new

            # Handle image uploads
            _handle_daily_journal_image_uploads(form, daily_journal, 'pre_market_screenshots', 'pre_market')
            _handle_daily_journal_image_uploads(form, daily_journal, 'eod_chart_screenshots', 'eod_chart')

            # Handle deletion of existing images (if checkboxes are added to the form)
            if daily_journal.id:  # Only if journal entry exists
                for image in daily_journal.images:
                    if request.form.get(f'delete_dj_image_{image.id}'):
                        if image.filepath:
                            try:
                                image_path_to_delete = os.path.join(current_app.config['UPLOAD_FOLDER'], image.filepath)
                                if os.path.exists(image_path_to_delete):
                                    os.remove(image_path_to_delete)
                            except OSError:
                                current_app.logger.warning(
                                    f"Could not delete daily journal image file on disk: {image.filepath}")
                        db.session.delete(image)

            db.session.commit()
            record_activity('daily_journal_save',
                            f"Daily journal for {target_date.strftime('%Y-%m-%d')} {action_desc}.")
            flash(f'Daily journal for {target_date.strftime("%d-%b-%Y")} has been {action_desc}!', 'success')
            return redirect(url_for('journal.manage_daily_journal', date_str=target_date.strftime('%Y-%m-%d')))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error saving daily journal for {target_date}: {e}", exc_info=True)
            flash(f'An error occurred while saving the daily journal: {str(e)}', 'danger')

    elif request.method == 'POST':  # Form validation failed
        flash('Please correct the errors in the form and try again.', 'warning')

    # Fetch trades for this specific day to display in the "Daily Trading Log"
    trades_for_day = Trade.query.filter_by(user_id=current_user.id, trade_date=target_date) \
        .order_by(Trade.id.asc()).all()

    # Calculate cumulative PNL for the day
    cumulative_daily_pnl = sum(trade.gross_pnl for trade in trades_for_day if trade.gross_pnl is not None)

    # Prepare data for psych scorecard radar chart
    # The DailyJournal model has review_psych_..._rating fields for the day, and an average_review_psych_rating property.
    psych_labels = ["Discipline", "Motivation", "Focus", "Mastery", "Composure", "Resilience", "Mind", "Energy"]
    psych_values = [
        daily_journal.review_psych_discipline_rating if daily_journal else None,
        daily_journal.review_psych_motivation_rating if daily_journal else None,
        daily_journal.review_psych_focus_rating if daily_journal else None,
        daily_journal.review_psych_mastery_rating if daily_journal else None,
        daily_journal.review_psych_composure_rating if daily_journal else None,
        daily_journal.review_psych_resilience_rating if daily_journal else None,
        daily_journal.review_psych_mind_rating if daily_journal else None,
        daily_journal.review_psych_energy_rating if daily_journal else None,
    ]
    # Filter out None values if chart library requires it, or handle in JS
    valid_psych_values = [v if v is not None else 0 for v in psych_values]  # Default to 0 for chart if None

    # Previous and next day for navigation
    prev_day = target_date - timedelta(days=1)
    next_day = target_date + timedelta(days=1)

    return render_template('journal/manage_daily_journal.html',
                           title=f"Daily Journal - {target_date.strftime('%A, %d %b %Y')}",
                           form=form,
                           daily_journal_entry=daily_journal,  # Pass the existing entry if any
                           journal_date=target_date,
                           trades_for_day=trades_for_day,
                           cumulative_daily_pnl=cumulative_daily_pnl,
                           psych_labels=psych_labels,
                           psych_values=valid_psych_values,  # Pass processed values for chart
                           prev_day_str=prev_day.strftime('%Y-%m-%d'),
                           next_day_str=next_day.strftime('%Y-%m-%d'),
                           today_str=py_date.today().strftime('%Y-%m-%d'))


@journal_bp.route('/p12-statistics')
@login_required
def p12_statistics():
    """Display P12 scenario usage statistics and analytics."""
    try:
        from datetime import date, timedelta
        from sqlalchemy import func, extract

        # Calculate date ranges
        thirty_days_ago = date.today() - timedelta(days=30)
        six_months_ago = date.today() - timedelta(days=180)
        ninety_days_ago = date.today() - timedelta(days=90)

        # Get user's most popular scenarios (last 30 days) from DailyJournal
        popular_scenarios_30d_raw = db.session.query(
            P12Scenario.scenario_number,
            P12Scenario.scenario_name,
            func.count(DailyJournal.id).label('usage_count')
        ).join(
            DailyJournal, P12Scenario.id == DailyJournal.p12_scenario_id
        ).filter(
            DailyJournal.user_id == current_user.id,
            DailyJournal.journal_date >= thirty_days_ago,
            DailyJournal.p12_scenario_id.isnot(None)
        ).group_by(
            P12Scenario.id, P12Scenario.scenario_number, P12Scenario.scenario_name
        ).order_by(func.count(DailyJournal.id).desc()).limit(5).all()

        # Convert to dictionaries
        popular_scenarios_30d = [
            {
                'scenario_number': row.scenario_number,
                'scenario_name': row.scenario_name,
                'usage_count': row.usage_count
            }
            for row in popular_scenarios_30d_raw
        ]

        # Get overall most popular scenarios (all users, last 30 days)
        popular_scenarios_overall_raw = db.session.query(
            P12Scenario.scenario_number,
            P12Scenario.scenario_name,
            func.count(DailyJournal.id).label('usage_count')
        ).join(
            DailyJournal, P12Scenario.id == DailyJournal.p12_scenario_id
        ).filter(
            DailyJournal.journal_date >= thirty_days_ago,
            DailyJournal.p12_scenario_id.isnot(None)
        ).group_by(
            P12Scenario.id, P12Scenario.scenario_number, P12Scenario.scenario_name
        ).order_by(func.count(DailyJournal.id).desc()).limit(5).all()

        # Convert to dictionaries
        popular_scenarios_overall = [
            {
                'scenario_number': row.scenario_number,
                'scenario_name': row.scenario_name,
                'usage_count': row.usage_count
            }
            for row in popular_scenarios_overall_raw
        ]

        # Get user's recent scenario usage from DailyJournal
        recent_usage_raw = db.session.query(
            DailyJournal.journal_date,
            P12Scenario.scenario_number,
            P12Scenario.scenario_name
        ).join(
            P12Scenario, DailyJournal.p12_scenario_id == P12Scenario.id
        ).filter(
            DailyJournal.user_id == current_user.id,
            DailyJournal.p12_scenario_id.isnot(None)
        ).order_by(DailyJournal.journal_date.desc()).limit(20).all()

        # Convert to format template expects
        recent_usage = []
        for usage in recent_usage_raw:
            recent_usage.append({
                'journal_date': usage.journal_date,  # Keep as date object for strftime
                'journal_date_str': usage.journal_date.strftime('%Y-%m-%d'),  # String version if needed
                'scenario': {
                    'scenario_number': usage.scenario_number,
                    'scenario_name': usage.scenario_name
                }
            })

        # Get scenarios user has used
        user_scenarios = db.session.query(P12Scenario).join(
            DailyJournal, P12Scenario.id == DailyJournal.p12_scenario_id
        ).filter(
            DailyJournal.user_id == current_user.id
        ).distinct().all()

        # Calculate success rates (placeholder for now)
        scenario_success_rates = []
        for scenario in user_scenarios:
            scenario_success_rates.append({
                'scenario': {
                    'scenario_number': scenario.scenario_number,
                    'scenario_name': scenario.scenario_name
                },
                'success_rate': 65.0  # Placeholder - implement real calculation later
            })

        # Calculate monthly usage trends from DailyJournal
        monthly_usage_raw = db.session.query(
            func.extract('year', DailyJournal.journal_date).label('year'),
            func.extract('month', DailyJournal.journal_date).label('month'),
            func.count(DailyJournal.id).label('usage_count')
        ).filter(
            DailyJournal.user_id == current_user.id,
            DailyJournal.journal_date >= six_months_ago,
            DailyJournal.p12_scenario_id.isnot(None)
        ).group_by(
            func.extract('year', DailyJournal.journal_date),
            func.extract('month', DailyJournal.journal_date)
        ).order_by('year', 'month').all()

        # Convert to JSON-serializable format
        monthly_usage = [
            {
                'year': int(row.year),
                'month': int(row.month),
                'usage_count': row.usage_count
            }
            for row in monthly_usage_raw
        ]

        # Calculate summary statistics for dashboard cards
        total_p12_uses_6m = DailyJournal.query.filter(
            DailyJournal.user_id == current_user.id,
            DailyJournal.journal_date >= six_months_ago,
            DailyJournal.p12_scenario_id.isnot(None)
        ).count()

        scenarios_used_30d = db.session.query(P12Scenario.id).join(
            DailyJournal, P12Scenario.id == DailyJournal.p12_scenario_id
        ).filter(
            DailyJournal.user_id == current_user.id,
            DailyJournal.journal_date >= thirty_days_ago
        ).distinct().count()

        # Calculate average success rate (placeholder)
        avg_success_rate = 65.0  # Placeholder

        # Get most used scenario
        most_used_scenario_raw = db.session.query(
            P12Scenario.scenario_number
        ).join(
            DailyJournal, P12Scenario.id == DailyJournal.p12_scenario_id
        ).filter(
            DailyJournal.user_id == current_user.id,
            DailyJournal.journal_date >= thirty_days_ago
        ).group_by(P12Scenario.id, P12Scenario.scenario_number).order_by(
            func.count(DailyJournal.id).desc()
        ).first()

        most_used_scenario = most_used_scenario_raw[0] if most_used_scenario_raw else None

        return render_template('journal/p12_statistics.html',
                               title="P12 Scenario Statistics",
                               popular_scenarios_30d=popular_scenarios_30d,
                               popular_scenarios_overall=popular_scenarios_overall,
                               recent_usage=recent_usage,
                               scenario_success_rates=scenario_success_rates,
                               monthly_usage=monthly_usage,
                               total_p12_uses_6m=total_p12_uses_6m,
                               scenarios_used_30d=scenarios_used_30d,
                               avg_success_rate=avg_success_rate,
                               most_used_scenario=most_used_scenario)

    except Exception as e:
        current_app.logger.error(f"Error loading P12 statistics: {e}", exc_info=True)
        flash('Error loading P12 statistics.', 'danger')
        return redirect(url_for('journal.manage_daily_journal'))


# Add route to update scenario outcome
@journal_bp.route('/p12-outcome/<int:usage_id>', methods=['POST'])
@login_required
def update_p12_outcome(usage_id):
    """Update the outcome of a P12 scenario usage."""
    try:
        usage_stat = P12UsageStats.query.filter_by(
            id=usage_id,
            user_id=current_user.id
        ).first_or_404()

        data = request.get_json()
        usage_stat.outcome_successful = data.get('successful')
        usage_stat.outcome_notes = data.get('notes', '')

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Outcome updated successfully'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating P12 outcome: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Error updating outcome'
        }), 500