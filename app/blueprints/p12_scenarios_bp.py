# ====================================================================
# COMPLETE P12 SCENARIOS BLUEPRINT
# File: app/blueprints/p12_scenarios_bp.py
# ====================================================================

import os
import uuid
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, current_app, jsonify, abort, send_file
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import P12Scenario
from app.forms import P12ScenarioForm


def admin_required(f):
    """Decorator to require admin permissions."""
    from functools import wraps
    from flask import abort
    from flask_login import current_user
    from app.models import UserRole

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            abort(403)  # Forbidden
        return f(*args, **kwargs)

    return decorated_function

p12_scenarios_bp = Blueprint('p12_scenarios', __name__, url_prefix='/admin/p12-scenarios')


def allowed_file(filename):
    """Check if file extension is allowed."""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_scenario_image(file):
    """Save uploaded scenario image and return the file path."""
    if not file or not allowed_file(file.filename):
        return None

    # Create unique filename
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"

    # Create upload directory if it doesn't exist
    upload_folder = current_app.config.get('UPLOAD_FOLDER',
                                           os.path.join(current_app.instance_path, 'uploads'))
    p12_folder = os.path.join(upload_folder, 'p12_scenarios')
    os.makedirs(p12_folder, exist_ok=True)

    # Save file
    file_path = os.path.join(p12_folder, unique_filename)
    file.save(file_path)

    return unique_filename


@p12_scenarios_bp.route('/')
@login_required
@admin_required
def list_scenarios():
    """List all P12 scenarios."""
    scenarios = P12Scenario.query.order_by(P12Scenario.scenario_number).all()
    return render_template('admin/p12_scenarios/list_scenarios.html',
                           scenarios=scenarios, title="Manage P12 Scenarios")


# Replace your create_scenario and edit_scenario routes with these updated versions:

@p12_scenarios_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_scenario():
    """Create a new P12 scenario."""
    form = P12ScenarioForm()

    if form.validate_on_submit():
        # Check if scenario number already exists
        existing = P12Scenario.query.filter_by(scenario_number=form.scenario_number.data).first()
        if existing:
            flash(f'Scenario {form.scenario_number.data} already exists!', 'danger')
            return render_template('admin/p12_scenarios/edit_scenario.html',
                                   form=form, title="Create P12 Scenario")

        # Handle image upload
        image_filename = None
        if form.scenario_image.data:
            image_filename = save_scenario_image(form.scenario_image.data)

        # Create new scenario with ALL fields including model recommendations
        scenario = P12Scenario(
            scenario_number=form.scenario_number.data,
            scenario_name=form.scenario_name.data,
            short_description=form.short_description.data,
            detailed_description=form.detailed_description.data,
            hod_lod_implication=form.hod_lod_implication.data,
            directional_bias=form.directional_bias.data or None,
            alert_criteria=form.alert_criteria.data,
            confirmation_criteria=form.confirmation_criteria.data,
            entry_strategy=form.entry_strategy.data,
            typical_targets=form.typical_targets.data or None,
            stop_loss_guidance=form.stop_loss_guidance.data or None,
            risk_percentage=form.risk_percentage.data,
            image_filename=image_filename,
            image_path=image_filename,
            is_active=form.is_active.data,

            # NEW: Model recommendation fields
            models_to_activate=form.models_to_activate.data if form.models_to_activate.data else [],
            models_to_avoid=form.models_to_avoid.data if form.models_to_avoid.data else [],
            risk_guidance=form.risk_guidance.data or None,
            preferred_timeframes=form.preferred_timeframes.data if form.preferred_timeframes.data else [],
            key_considerations=form.key_considerations.data or None
        )

        try:
            db.session.add(scenario)
            db.session.commit()
            flash(f'P12 Scenario {scenario.scenario_number} created successfully!', 'success')
            return redirect(url_for('p12_scenarios.list_scenarios'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating scenario: {str(e)}', 'danger')

    return render_template('admin/p12_scenarios/edit_scenario.html',
                           form=form, title="Create P12 Scenario")


@p12_scenarios_bp.route('/edit/<int:scenario_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_scenario(scenario_id):
    """Edit an existing P12 scenario."""
    scenario = P12Scenario.query.get_or_404(scenario_id)
    form = P12ScenarioForm(obj=scenario)

    if form.validate_on_submit():
        # Check if scenario number conflicts (only if changed)
        if form.scenario_number.data != scenario.scenario_number:
            existing = P12Scenario.query.filter_by(scenario_number=form.scenario_number.data).first()
            if existing:
                flash(f'Scenario {form.scenario_number.data} already exists!', 'danger')
                return render_template('admin/p12_scenarios/edit_scenario.html',
                                       form=form, scenario=scenario, title="Edit P12 Scenario")

        # Handle image upload
        if form.scenario_image.data:
            new_image = save_scenario_image(form.scenario_image.data)
            if new_image:
                # Delete old image if it exists
                if scenario.image_path:
                    old_path = scenario.full_image_path
                    if old_path and os.path.exists(old_path):
                        os.remove(old_path)

                scenario.image_filename = new_image
                scenario.image_path = new_image

        # Update ALL scenario fields including model recommendations
        scenario.scenario_number = form.scenario_number.data
        scenario.scenario_name = form.scenario_name.data
        scenario.short_description = form.short_description.data
        scenario.detailed_description = form.detailed_description.data
        scenario.hod_lod_implication = form.hod_lod_implication.data
        scenario.directional_bias = form.directional_bias.data or None
        scenario.alert_criteria = form.alert_criteria.data
        scenario.confirmation_criteria = form.confirmation_criteria.data
        scenario.entry_strategy = form.entry_strategy.data
        scenario.typical_targets = form.typical_targets.data or None
        scenario.stop_loss_guidance = form.stop_loss_guidance.data or None
        scenario.risk_percentage = form.risk_percentage.data
        scenario.is_active = form.is_active.data
        scenario.updated_date = datetime.utcnow()

        # NEW: Update model recommendation fields
        scenario.models_to_activate = form.models_to_activate.data if form.models_to_activate.data else []
        scenario.models_to_avoid = form.models_to_avoid.data if form.models_to_avoid.data else []
        scenario.risk_guidance = form.risk_guidance.data or None
        scenario.preferred_timeframes = form.preferred_timeframes.data if form.preferred_timeframes.data else []
        scenario.key_considerations = form.key_considerations.data or None

        try:
            db.session.commit()
            flash(f'P12 Scenario {scenario.scenario_number} updated successfully!', 'success')
            return redirect(url_for('p12_scenarios.list_scenarios'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating scenario: {str(e)}', 'danger')

    return render_template('admin/p12_scenarios/edit_scenario.html',
                           form=form, scenario=scenario, title="Edit P12 Scenario")


@p12_scenarios_bp.route('/delete/<int:scenario_id>', methods=['POST'])
@login_required
@admin_required
def delete_scenario(scenario_id):
    """Delete a P12 scenario."""
    scenario = P12Scenario.query.get_or_404(scenario_id)

    try:
        # Delete associated image
        if scenario.image_path:
            image_path = scenario.full_image_path
            if image_path and os.path.exists(image_path):
                os.remove(image_path)

        scenario_number = scenario.scenario_number
        db.session.delete(scenario)
        db.session.commit()
        flash(f'P12 Scenario {scenario_number} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting scenario: {str(e)}', 'danger')

    return redirect(url_for('p12_scenarios.list_scenarios'))


@p12_scenarios_bp.route('/view/<int:scenario_id>')
@login_required
@admin_required
def view_scenario(scenario_id):
    """View a P12 scenario in detail."""
    scenario = P12Scenario.query.get_or_404(scenario_id)
    return render_template('admin/p12_scenarios/view_scenario.html',
                           scenario=scenario, title=f"P12 Scenario {scenario.scenario_number}")


# API endpoints for daily journal integration
@p12_scenarios_bp.route('/api/scenarios')
@login_required
def api_get_scenarios():
    """API endpoint to get active scenarios for daily journal."""
    scenarios = P12Scenario.query.filter_by(is_active=True).order_by(P12Scenario.scenario_number).all()

    scenario_data = []
    for scenario in scenarios:
        scenario_data.append({
            'id': scenario.id,
            'scenario_number': scenario.scenario_number,
            'scenario_name': scenario.scenario_name,
            'short_description': scenario.short_description,
            'detailed_description': scenario.detailed_description,
            'hod_lod_implication': scenario.hod_lod_implication,
            'directional_bias': scenario.directional_bias,
            'alert_criteria': scenario.alert_criteria,
            'confirmation_criteria': scenario.confirmation_criteria,
            'entry_strategy': scenario.entry_strategy,
            'typical_targets': scenario.typical_targets,
            'stop_loss_guidance': scenario.stop_loss_guidance,
            'risk_percentage': float(scenario.risk_percentage) if scenario.risk_percentage else None,

            # NEW: Model recommendations from database
            'models_to_activate': scenario.models_to_activate or [],
            'models_to_avoid': scenario.models_to_avoid or [],
            'risk_guidance': scenario.risk_guidance,
            'preferred_timeframes': scenario.preferred_timeframes or [],
            'key_considerations': scenario.key_considerations,

            'image_url': url_for('p12_scenarios.serve_image', scenario_id=scenario.id) if scenario.image_path else None
        })

    return jsonify(scenario_data)

@p12_scenarios_bp.route('/image/<int:scenario_id>')
@login_required
def serve_image(scenario_id):
    """Serve scenario images."""
    scenario = P12Scenario.query.get_or_404(scenario_id)
    if not scenario.image_path:
        abort(404)

    upload_folder = current_app.config.get('UPLOAD_FOLDER',
                                           os.path.join(current_app.instance_path, 'uploads'))
    image_path = os.path.join(upload_folder, 'p12_scenarios', scenario.image_path)

    if not os.path.exists(image_path):
        abort(404)

    return send_file(image_path)


@p12_scenarios_bp.route('/api/scenarios/<int:scenario_id>/increment', methods=['POST'])
@login_required
def increment_scenario_usage(scenario_id):
    """Track when a scenario is selected in daily journal."""
    scenario = P12Scenario.query.get_or_404(scenario_id)
    scenario.increment_usage()
    return jsonify({'success': True})