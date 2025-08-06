from flask import (Blueprint, render_template, current_app, request,
                   redirect, url_for, flash, abort, jsonify)  # Added abort
from flask_login import login_required, current_user

from app.extensions import db
from app.utils import admin_required, record_activity, generate_token, send_email, smart_flash  # Added generate_token, send_email
from app.models import User, UserRole, Activity, Instrument, Tag, TagCategory  # Add TagCategory here
from datetime import datetime

from app.forms import AdminCreateUserForm, AdminEditUserForm, InstrumentForm, InstrumentFilterForm  # Add Instrument forms
from app.models import Tag, TagCategory  # Add to existing imports
from app.forms import AdminDefaultTagForm
from app.models import Instrument  # Add to existing imports
from app.forms import InstrumentForm, InstrumentFilterForm  # Add to existing imports
from app.models import TradingModel

from flask import (Blueprint, render_template, current_app, request,
                   redirect, url_for, flash, abort, jsonify)
from flask_login import login_required, current_user
from app.extensions import db
from app.utils import admin_required, record_activity, generate_token, send_email, smart_flash
from datetime import datetime
import os
from app.forms import TradingModelForm
from app.models import User, UserRole, Activity, Instrument, Tag, TagCategory, TradingModel, P12Scenario, DiscordRolePermission, GlobalImage, Backtest, BacktestTrade, BacktestStatus, BacktestExitReason
from app.utils.image_manager import ImageManager
from app.forms import BacktestForm, BacktestTradeForm, BacktestFilterForm
admin_bp = Blueprint('admin', __name__,
                     template_folder='../templates/admin',
                     url_prefix='/admin')

@admin_bp.route('/default-trading-models')
@login_required
@admin_required
def manage_default_trading_models():
    """Admin page to manage default trading models"""
    models = TradingModel.query.filter_by(is_default=True).order_by(TradingModel.name).all()
    return render_template('admin/default_trading_models.html',
                           title='Manage Default Trading Models',
                           models=models)


@admin_bp.route('/default-trading-models/<int:model_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_default_trading_model(model_id):
    """Edit a default trading model"""
    model = TradingModel.query.get_or_404(model_id)
    if not model.is_default:
        flash('This is not a default model.', 'warning')
        return redirect(url_for('admin.manage_default_trading_models'))

    form = TradingModelForm(obj=model)

    if form.validate_on_submit():
        # Handle image uploads first
        if form.chart_examples.data:
            image_manager = ImageManager('trading_model')
            
            for uploaded_file in form.chart_examples.data:
                if uploaded_file and uploaded_file.filename:
                    # Save the image file
                    save_result = image_manager.save_image(uploaded_file, entity_id=model.id)
                    
                    if save_result['success']:
                        # Create GlobalImage database record
                        global_image = GlobalImage(
                            entity_type='trading_model',
                            entity_id=model.id,
                            user_id=current_user.id,
                            filename=save_result['filename'],
                            original_filename=uploaded_file.filename,
                            relative_path=save_result['relative_path'],
                            file_size=save_result['file_size'],
                            mime_type=save_result['mime_type'],
                            has_thumbnail=save_result.get('thumbnail_path') is not None,
                            caption=f'Chart example for {model.name}',
                            is_optimized=True
                        )
                        
                        # Get image dimensions if possible
                        try:
                            from PIL import Image
                            with Image.open(save_result['file_path']) as img:
                                global_image.image_width, global_image.image_height = img.size
                        except:
                            pass  # Not critical if we can't get dimensions
                        
                        db.session.add(global_image)
                    else:
                        flash(f'Failed to upload {uploaded_file.filename}: {save_result.get("errors", ["Unknown error"])[0]}', 'warning')

        # Update the model
        form.populate_obj(model)
        model.created_by_admin_user_id = current_user.id
        
        try:
            db.session.commit()
            flash(f"Default model '{model.name}' updated successfully!", 'success')
            return redirect(url_for('admin.manage_default_trading_models'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating model: {str(e)}', 'danger')

    # Get existing images for display
    existing_images = GlobalImage.query.filter_by(
        entity_type='trading_model', 
        entity_id=model.id
    ).order_by(GlobalImage.upload_date.desc()).all()

    return render_template('admin/create_default_trading_model.html',
                           title=f'Edit Default Model: {model.name}',
                           form=form, model=model, existing_images=existing_images)


@admin_bp.route('/default-trading-models/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_default_trading_model():
    """Create a new default trading model"""
    form = TradingModelForm()

    if form.validate_on_submit():
        model = TradingModel()
        form.populate_obj(model)
        model.is_default = True
        model.user_id = current_user.id  # Still needs a user_id for FK constraint
        model.created_by_admin_user_id = current_user.id
        
        try:
            db.session.add(model)
            db.session.flush()  # Get the model ID without committing
            
            # Handle image uploads
            if form.chart_examples.data:
                image_manager = ImageManager('trading_model')
                
                for uploaded_file in form.chart_examples.data:
                    if uploaded_file and uploaded_file.filename:
                        # Save the image file
                        save_result = image_manager.save_image(uploaded_file, entity_id=model.id)
                        
                        if save_result['success']:
                            # Create GlobalImage database record
                            global_image = GlobalImage(
                                entity_type='trading_model',
                                entity_id=model.id,
                                user_id=current_user.id,
                                filename=save_result['filename'],
                                original_filename=uploaded_file.filename,
                                relative_path=save_result['relative_path'],
                                file_size=save_result['file_size'],
                                mime_type=save_result['mime_type'],
                                has_thumbnail=save_result.get('thumbnail_path') is not None,
                                caption=f'Chart example for {model.name}',
                                is_optimized=True
                            )
                            
                            # Get image dimensions if possible
                            try:
                                from PIL import Image
                                with Image.open(save_result['file_path']) as img:
                                    global_image.image_width, global_image.image_height = img.size
                            except:
                                pass  # Not critical if we can't get dimensions
                            
                            db.session.add(global_image)
                        else:
                            flash(f'Failed to upload {uploaded_file.filename}: {save_result.get("errors", ["Unknown error"])[0]}', 'warning')
            
            db.session.commit()
            flash(f"Default model '{model.name}' created successfully!", 'success')
            return redirect(url_for('admin.manage_default_trading_models'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating model: {str(e)}', 'danger')

    return render_template('admin/create_default_trading_model.html',
                           title='Create Default Trading Model',
                           form=form)


@admin_bp.route('/default-trading-models/<int:model_id>/view')
@login_required
@admin_required
def view_default_trading_model(model_id):
    """View a default trading model"""
    model = TradingModel.query.get_or_404(model_id)
    if not model.is_default:
        flash("This is not a default model.", 'warning')
        return redirect(url_for('admin.manage_default_trading_models'))

    # Get chart examples for this model
    chart_examples = GlobalImage.query.filter_by(
        entity_type='trading_model', 
        entity_id=model.id
    ).order_by(GlobalImage.upload_date.desc()).all()

    return render_template('admin/view_default_trading_model.html',
                           title=f'View Default Model: {model.name}',
                           model=model, chart_examples=chart_examples)


@admin_bp.route('/default-trading-models/<int:model_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_default_trading_model(model_id):
    """Delete a default trading model."""
    model = TradingModel.query.get_or_404(model_id)

    # Verify it's actually a default model
    if not model.is_default:
        flash('This is not a default model and cannot be deleted through this interface.', 'warning')
        return redirect(url_for('admin.manage_default_trading_models'))

    try:
        model_name = model.name
        db.session.delete(model)
        db.session.commit()

        # Log the deletion
        record_activity(f'Deleted default trading model: {model_name}')
        current_app.logger.info(f"Admin {current_user.username} deleted default trading model {model_name}.")

        flash(f'Strategic framework "{model_name}" has been removed successfully.', 'success')

        # Check if request wants JSON response (for AJAX calls)
        if request.headers.get('Content-Type') == 'application/json' or request.is_json:
            return jsonify({
                'success': True,
                'message': f"Strategic framework '{model_name}' has been removed successfully."
            })

    except Exception as e:
        db.session.rollback()
        error_msg = f'Error removing configuration: {str(e)}'
        current_app.logger.error(f"Error deleting default trading model {model_id}: {e}", exc_info=True)
        flash(error_msg, 'danger')

        # Check if request wants JSON response (for AJAX calls)
        if request.headers.get('Content-Type') == 'application/json' or request.is_json:
            return jsonify({
                'success': False,
                'message': error_msg
            }), 500

    return redirect(url_for('admin.manage_default_trading_models'))


@admin_bp.route('/default-trading-models/<int:model_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_default_trading_model_status(model_id):
    """Toggle the active status of a default trading model."""
    model = TradingModel.query.get_or_404(model_id)

    if not model.is_default:
        flash("This is not a default model.", 'warning')
        return redirect(url_for('admin.manage_default_trading_models'))

    try:
        model.is_active = not model.is_active
        status_text = "activated" if model.is_active else "deactivated"

        db.session.commit()
        flash(f"Strategic framework '{model.name}' has been {status_text} successfully.", 'success')

    except Exception as e:
        db.session.rollback()
        flash(f"Error updating status: {str(e)}", 'danger')

    return redirect(url_for('admin.manage_default_trading_models'))


@admin_bp.route('/default-trading-models/<int:model_id>/export-pdf', methods=['POST'])
@login_required
@admin_required
def export_trading_model_pdf(model_id):
    """Export a single trading model to PDF."""
    try:
        model = TradingModel.query.get_or_404(model_id)
        
        if not model.is_default:
            flash('Access denied: This is not a default trading model.', 'warning')
            return redirect(url_for('admin.manage_default_trading_models'))
        
        # Get chart examples
        chart_examples = GlobalImage.query.filter_by(
            entity_type='trading_model', 
            entity_id=model.id
        ).all()
        
        # Create PDF content
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from io import BytesIO
        import os
        from PIL import Image as PILImage
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)
        
        # Build story
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            textColor=colors.HexColor('#0066cc'),
            alignment=1  # Center
        )
        story.append(Paragraph(f"Trading Model: {model.name}", title_style))
        story.append(Spacer(1, 12))
        
        # Version and Status
        if model.version:
            story.append(Paragraph(f"<b>Version:</b> {model.version}", styles['Normal']))
        story.append(Paragraph(f"<b>Status:</b> {'Active' if model.is_active else 'Inactive'}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Overview Logic
        if model.overview_logic:
            story.append(Paragraph("<b>Strategic Framework Overview</b>", styles['Heading2']))
            story.append(Paragraph(model.overview_logic, styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Timeframes
        if model.primary_chart_tf or model.execution_chart_tf or model.context_chart_tf:
            story.append(Paragraph("<b>Operational Timeframes</b>", styles['Heading2']))
            timeframe_data = []
            if model.primary_chart_tf:
                timeframe_data.append(['Primary Analysis', model.primary_chart_tf])
            if model.execution_chart_tf:
                timeframe_data.append(['Execution', model.execution_chart_tf])
            if model.context_chart_tf:
                timeframe_data.append(['Context Analysis', model.context_chart_tf])
            
            if timeframe_data:
                t = Table(timeframe_data)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(t)
                story.append(Spacer(1, 12))
        
        # Technical Framework
        sections = [
            ('Technical Indicators', model.technical_indicators_used),
            ('Chart Patterns', model.chart_patterns_used),
            ('Price Action Signals', model.price_action_signals),
            ('Key Levels Identification', model.key_levels_identification),
            ('Volume Analysis', model.volume_analysis_notes),
            ('Fundamental Analysis', model.fundamental_analysis_notes),
            ('Entry Triggers', model.entry_trigger_description),
            ('Optimal Market Conditions', model.optimal_market_conditions),
            ('Instrument Applicability', model.instrument_applicability),
            ('Session Applicability', model.session_applicability),
            ('Sub-Optimal Conditions', model.sub_optimal_market_conditions),
            ('Stop Loss Strategy', model.stop_loss_strategy),
            ('Take Profit Strategy', model.take_profit_strategy),
            ('Position Sizing Rules', model.position_sizing_rules),
            ('Scaling In/Out Rules', model.scaling_in_out_rules),
            ('Pre-Trade Checklist', model.pre_trade_checklist),
            ('Order Types Used', model.order_types_used),
            ('Broker/Platform Notes', model.broker_platform_notes),
            ('Strengths', model.strengths),
            ('Weaknesses', model.weaknesses),
            ('Backtesting Notes', model.backtesting_forwardtesting_notes),
            ('Refinements & Learnings', model.refinements_learnings)
        ]
        
        for section_title, content in sections:
            if content:
                story.append(Paragraph(f"<b>{section_title}</b>", styles['Heading3']))
                story.append(Paragraph(content, styles['Normal']))
                story.append(Spacer(1, 8))
        
        # Risk Parameters
        risk_params = []
        if model.min_risk_reward_ratio:
            risk_params.append(['Min Risk:Reward Ratio', f"{model.min_risk_reward_ratio}:1"])
        if model.model_max_loss_per_trade:
            risk_params.append(['Max Loss Per Trade', model.model_max_loss_per_trade])
        if model.model_max_daily_loss:
            risk_params.append(['Max Daily Loss', model.model_max_daily_loss])
        if model.model_max_weekly_loss:
            risk_params.append(['Max Weekly Loss', model.model_max_weekly_loss])
        if model.model_consecutive_loss_limit:
            risk_params.append(['Consecutive Loss Limit', str(model.model_consecutive_loss_limit)])
        
        if risk_params:
            story.append(Paragraph("<b>Risk Parameters</b>", styles['Heading2']))
            t = Table(risk_params)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(t)
        
        # Chart Examples
        if chart_examples:
            story.append(Paragraph("<b>Chart Examples</b>", styles['Heading2']))
            story.append(Spacer(1, 12))
            
            for i, chart_image in enumerate(chart_examples, 1):
                try:
                    # Get the image file path using the model's full_disk_path property
                    image_path = chart_image.full_disk_path
                    
                    if os.path.exists(image_path):
                        # Add image title/caption
                        if chart_image.caption:
                            story.append(Paragraph(f"<b>Chart Example {i}: {chart_image.caption}</b>", styles['Heading3']))
                        else:
                            story.append(Paragraph(f"<b>Chart Example {i}</b>", styles['Heading3']))
                        story.append(Spacer(1, 6))
                        
                        # Add image to PDF with proper sizing
                        img = Image(image_path)
                        # Scale image to fit page width (max 6 inches wide)
                        img_width, img_height = img.drawWidth, img.drawHeight
                        max_width = 7 * inch
                        max_height = 5 * inch
                        
                        # Calculate scaling to fit within max dimensions
                        scale_w = max_width / img_width if img_width > max_width else 1
                        scale_h = max_height / img_height if img_height > max_height else 1
                        scale = min(scale_w, scale_h)
                        
                        img.drawWidth = img_width * scale
                        img.drawHeight = img_height * scale
                        
                        story.append(img)
                        story.append(Spacer(1, 12))
                        
                except Exception as img_error:
                    # If image fails, add a note instead
                    story.append(Paragraph(f"<b>Chart Example {i}:</b> Image not available", styles['Normal']))
                    story.append(Spacer(1, 8))
                    current_app.logger.warning(f"Failed to include image {chart_image.id} in PDF: {img_error}")
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Create response
        from flask import make_response
        response = make_response(buffer.getvalue())
        buffer.close()
        
        filename = f"Trading_Model_{model.name.replace(' ', '_')}_Export.pdf"
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Log activity
        record_activity(f'Exported trading model "{model.name}" to PDF')
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error exporting trading model {model_id} to PDF: {e}", exc_info=True)
        flash(f'Error exporting to PDF: {str(e)}', 'danger')
        return redirect(url_for('admin.view_default_trading_model', model_id=model_id))


@admin_bp.route('/default-trading-models/<int:model_id>/export-csv', methods=['POST'])
@login_required
@admin_required
def export_trading_model_csv(model_id):
    """Export a single trading model to CSV."""
    try:
        model = TradingModel.query.get_or_404(model_id)
        
        if not model.is_default:
            flash('Access denied: This is not a default trading model.', 'warning')
            return redirect(url_for('admin.manage_default_trading_models'))
        
        import csv
        from io import StringIO
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Trading Model Export', model.name])
        writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])  # Empty row
        
        # Model details
        fields = [
            ('Name', model.name),
            ('Version', model.version),
            ('Status', 'Active' if model.is_active else 'Inactive'),
            ('Overview Logic', model.overview_logic),
            ('Primary Chart Timeframe', model.primary_chart_tf),
            ('Execution Chart Timeframe', model.execution_chart_tf),
            ('Context Chart Timeframe', model.context_chart_tf),
            ('Technical Indicators Used', model.technical_indicators_used),
            ('Chart Patterns Used', model.chart_patterns_used),
            ('Price Action Signals', model.price_action_signals),
            ('Key Levels Identification', model.key_levels_identification),
            ('Volume Analysis Notes', model.volume_analysis_notes),
            ('Fundamental Analysis Notes', model.fundamental_analysis_notes),
            ('Entry Trigger Description', model.entry_trigger_description),
            ('Optimal Market Conditions', model.optimal_market_conditions),
            ('Instrument Applicability', model.instrument_applicability),
            ('Session Applicability', model.session_applicability),
            ('Sub-Optimal Market Conditions', model.sub_optimal_market_conditions),
            ('Stop Loss Strategy', model.stop_loss_strategy),
            ('Take Profit Strategy', model.take_profit_strategy),
            ('Min Risk Reward Ratio', model.min_risk_reward_ratio),
            ('Model Max Loss Per Trade', model.model_max_loss_per_trade),
            ('Model Max Daily Loss', model.model_max_daily_loss),
            ('Model Max Weekly Loss', model.model_max_weekly_loss),
            ('Model Consecutive Loss Limit', model.model_consecutive_loss_limit),
            ('Model Action on Max Drawdown', model.model_action_on_max_drawdown),
            ('Position Sizing Rules', model.position_sizing_rules),
            ('Scaling In/Out Rules', model.scaling_in_out_rules),
            ('Trade Management Breakeven Rules', model.trade_management_breakeven_rules),
            ('Trade Management Trailing Stop Rules', model.trade_management_trailing_stop_rules),
            ('Trade Management Partial Profit Rules', model.trade_management_partial_profit_rules),
            ('Trade Management Adverse Price Action', model.trade_management_adverse_price_action),
            ('Pre-Trade Checklist', model.pre_trade_checklist),
            ('Order Types Used', model.order_types_used),
            ('Broker Platform Notes', model.broker_platform_notes),
            ('Execution Confirmation Notes', model.execution_confirmation_notes),
            ('Post Trade Routine Model', model.post_trade_routine_model),
            ('Strengths', model.strengths),
            ('Weaknesses', model.weaknesses),
            ('Backtesting Forward Testing Notes', model.backtesting_forwardtesting_notes),
            ('Refinements Learnings', model.refinements_learnings),
            ('Created At', model.created_at.strftime('%Y-%m-%d %H:%M:%S') if model.created_at else ''),
            ('Updated At', model.updated_at.strftime('%Y-%m-%d %H:%M:%S') if model.updated_at else '')
        ]
        
        writer.writerow(['Field', 'Value'])
        for field_name, field_value in fields:
            writer.writerow([field_name, field_value or ''])
        
        # Create response
        from flask import make_response
        response = make_response(output.getvalue())
        output.close()
        
        filename = f"Trading_Model_{model.name.replace(' ', '_')}_Export.csv"
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Log activity
        record_activity(f'Exported trading model "{model.name}" to CSV')
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error exporting trading model {model_id} to CSV: {e}", exc_info=True)
        flash(f'Error exporting to CSV: {str(e)}', 'danger')
        return redirect(url_for('admin.view_default_trading_model', model_id=model_id))


@admin_bp.route('/default-trading-models/export-pdf', methods=['POST'])
@login_required
@admin_required
def export_all_trading_models_pdf():
    """Export all default trading models to PDF."""
    try:
        models = TradingModel.query.filter_by(is_default=True).order_by(TradingModel.name).all()
        
        if not models:
            flash('No default trading models found to export.', 'warning')
            return redirect(url_for('admin.manage_default_trading_models'))
        
        # Create PDF content
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from io import BytesIO
        import os
        from PIL import Image as PILImage
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)
        
        # Build story
        story = []
        styles = getSampleStyleSheet()
        
        # Main Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#0066cc'),
            alignment=1  # Center
        )
        story.append(Paragraph("Trading Models Export", title_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Paragraph(f"Total Models: {len(models)}", styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Table of Contents
        story.append(Paragraph("Table of Contents", styles['Heading2']))
        for i, model in enumerate(models, 1):
            story.append(Paragraph(f"{i}. {model.name} (Version: {model.version or 'N/A'})", styles['Normal']))
        story.append(PageBreak())
        
        # Individual Models
        for i, model in enumerate(models, 1):
            # Model Title
            model_title_style = ParagraphStyle(
                'ModelTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=20,
                textColor=colors.HexColor('#0066cc')
            )
            story.append(Paragraph(f"{i}. {model.name}", model_title_style))
            
            # Basic Info
            if model.version:
                story.append(Paragraph(f"<b>Version:</b> {model.version}", styles['Normal']))
            story.append(Paragraph(f"<b>Status:</b> {'Active' if model.is_active else 'Inactive'}", styles['Normal']))
            story.append(Spacer(1, 12))
            
            # Overview
            if model.overview_logic:
                story.append(Paragraph("<b>Strategic Framework Overview</b>", styles['Heading3']))
                story.append(Paragraph(model.overview_logic, styles['Normal']))
                story.append(Spacer(1, 8))
            
            # Key sections
            key_sections = [
                ('Technical Indicators', model.technical_indicators_used),
                ('Entry Triggers', model.entry_trigger_description),
                ('Stop Loss Strategy', model.stop_loss_strategy),
                ('Take Profit Strategy', model.take_profit_strategy),
                ('Strengths', model.strengths),
                ('Weaknesses', model.weaknesses)
            ]
            
            for section_title, content in key_sections:
                if content:
                    story.append(Paragraph(f"<b>{section_title}:</b> {content}", styles['Normal']))
                    story.append(Spacer(1, 4))
            
            # Chart Examples for this model
            chart_examples = GlobalImage.query.filter_by(
                entity_type='trading_model', 
                entity_id=model.id
            ).all()
            
            if chart_examples:
                story.append(Spacer(1, 8))
                story.append(Paragraph("<b>Chart Examples</b>", styles['Heading3']))
                story.append(Spacer(1, 6))
                
                for j, chart_image in enumerate(chart_examples, 1):
                    try:
                        # Get the image file path using the model's full_disk_path property
                        image_path = chart_image.full_disk_path
                        
                        if os.path.exists(image_path):
                            # Add image title/caption
                            if chart_image.caption:
                                story.append(Paragraph(f"<b>Chart {j}: {chart_image.caption}</b>", styles['Normal']))
                            else:
                                story.append(Paragraph(f"<b>Chart {j}</b>", styles['Normal']))
                            story.append(Spacer(1, 4))
                            
                            # Add image to PDF with proper sizing (smaller for bulk export)
                            img = Image(image_path)
                            # Scale image smaller for bulk export (max 4 inches wide)
                            img_width, img_height = img.drawWidth, img.drawHeight
                            max_width = 7 * inch
                            max_height = 5 * inch
                            
                            # Calculate scaling to fit within max dimensions
                            scale_w = max_width / img_width if img_width > max_width else 1
                            scale_h = max_height / img_height if img_height > max_height else 1
                            scale = min(scale_w, scale_h)
                            
                            img.drawWidth = img_width * scale
                            img.drawHeight = img_height * scale
                            
                            story.append(img)
                            story.append(Spacer(1, 6))
                            
                    except Exception as img_error:
                        # If image fails, add a note instead
                        story.append(Paragraph(f"<b>Chart {j}:</b> Image not available", styles['Normal']))
                        story.append(Spacer(1, 4))
                        current_app.logger.warning(f"Failed to include image {chart_image.id} in bulk PDF: {img_error}")
            
            # Add page break except for last model
            if i < len(models):
                story.append(PageBreak())
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Create response
        from flask import make_response
        response = make_response(buffer.getvalue())
        buffer.close()
        
        filename = f"All_Trading_Models_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Log activity
        record_activity(f'Exported {len(models)} trading models to PDF')
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error exporting all trading models to PDF: {e}", exc_info=True)
        flash(f'Error exporting to PDF: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_default_trading_models'))


@admin_bp.route('/default-trading-models/export-csv', methods=['POST'])
@login_required
@admin_required
def export_all_trading_models_csv():
    """Export all default trading models to CSV."""
    try:
        models = TradingModel.query.filter_by(is_default=True).order_by(TradingModel.name).all()
        
        if not models:
            flash('No default trading models found to export.', 'warning')
            return redirect(url_for('admin.manage_default_trading_models'))
        
        import csv
        from io import StringIO
        
        # Create CSV content
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Trading Models Export - All Models'])
        writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['Total Models', len(models)])
        writer.writerow([])  # Empty row
        
        # Column headers
        headers = [
            'Model Name', 'Version', 'Status', 'Overview Logic', 
            'Primary Chart TF', 'Execution Chart TF', 'Context Chart TF',
            'Technical Indicators', 'Chart Patterns', 'Price Action Signals',
            'Entry Triggers', 'Optimal Conditions', 'Stop Loss Strategy',
            'Take Profit Strategy', 'Min Risk Reward', 'Position Sizing',
            'Strengths', 'Weaknesses', 'Created At', 'Updated At'
        ]
        writer.writerow(headers)
        
        # Model data
        for model in models:
            row = [
                model.name,
                model.version or '',
                'Active' if model.is_active else 'Inactive',
                model.overview_logic or '',
                model.primary_chart_tf or '',
                model.execution_chart_tf or '',
                model.context_chart_tf or '',
                model.technical_indicators_used or '',
                model.chart_patterns_used or '',
                model.price_action_signals or '',
                model.entry_trigger_description or '',
                model.optimal_market_conditions or '',
                model.stop_loss_strategy or '',
                model.take_profit_strategy or '',
                model.min_risk_reward_ratio or '',
                model.position_sizing_rules or '',
                model.strengths or '',
                model.weaknesses or '',
                model.created_at.strftime('%Y-%m-%d %H:%M:%S') if model.created_at else '',
                model.updated_at.strftime('%Y-%m-%d %H:%M:%S') if model.updated_at else ''
            ]
            writer.writerow(row)
        
        # Create response
        from flask import make_response
        response = make_response(output.getvalue())
        output.close()
        
        filename = f"All_Trading_Models_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Log activity
        record_activity(f'Exported {len(models)} trading models to CSV')
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error exporting all trading models to CSV: {e}", exc_info=True)
        flash(f'Error exporting to CSV: {str(e)}', 'danger')
        return redirect(url_for('admin.manage_default_trading_models'))


@admin_bp.route('/delete-image/<int:image_id>', methods=['POST'])
@login_required
@admin_required
def delete_image(image_id):
    """Delete a GlobalImage and its associated file."""
    try:
        image = GlobalImage.query.get_or_404(image_id)
        
        # Check if user has permission (admin or owner)
        if current_user.role != UserRole.ADMIN and image.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
        # Store filename for response
        filename = image.original_filename
        
        # Delete the physical file
        try:
            file_path = os.path.join(current_app.instance_path, image.relative_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as file_error:
            current_app.logger.warning(f"Could not delete physical file {image.relative_path}: {file_error}")
        
        # Delete from database
        db.session.delete(image)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Image "{filename}" deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting image {image_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Error deleting image'
        }), 500


@admin_bp.route('/default-tags/create', methods=['POST'])
@login_required
@admin_required
def create_default_tag():
    """Create a new default tag from a standard form submission."""
    try:
        # --- MODIFICATION START ---
        # Read from the submitted form data instead of JSON
        name = request.form.get('name', '').strip()
        category_name = request.form.get('category', '')
        color_category = request.form.get('color_category', 'neutral')
        # Convert the form's string 'true'/'false' to a Python boolean
        is_active = request.form.get('is_active') == 'true'
        # --- MODIFICATION END ---

        if not name or not category_name:
            flash("Name and category are required.", 'danger')
            return redirect(url_for('admin.manage_default_tags'))

        # Validate category
        try:
            category = TagCategory[category_name]
        except KeyError:
            flash('Invalid category specified.', 'danger')
            return redirect(url_for('admin.manage_default_tags'))

        # Check for duplicates
        existing = Tag.query.filter_by(name=name, is_default=True).first()
        if existing:
            flash(f"A default tag named '{name}' already exists.", 'warning')
            return redirect(url_for('admin.manage_default_tags'))

        # Create new default tag
        new_tag = Tag(
            name=name,
            category=category,
            color_category=color_category,
            is_default=True,
            is_active=is_active
        )

        db.session.add(new_tag)
        db.session.commit()

        # Flash a success message and redirect back to the tags page
        flash(f"Tag '{new_tag.name}' was created successfully.", 'success')
        return redirect(url_for('admin.manage_default_tags'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating default tag: {e}", exc_info=True)
        flash(f"An unexpected error occurred while creating the tag.", 'danger')
        return redirect(url_for('admin.manage_default_tags'))


@admin_bp.route('/default-tags/<int:tag_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_default_tag(tag_id):
    """Edit a default tag via AJAX or Form submission"""
    try:
        tag = Tag.query.get_or_404(tag_id)

        if not tag.is_default:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Can only edit default tags'})
            else:
                flash("Can only edit default tags", 'danger')
                return redirect(url_for('admin.manage_default_tags'))

        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            name = data.get('name', '').strip()
            category_name = data.get('category', '')
            is_active = data.get('is_active', True)
            color_category = data.get('color_category', 'neutral')
        else:
            # Form data
            name = request.form.get('name', '').strip()
            category_name = request.form.get('category', '')
            is_active = request.form.get('is_active', 'false').lower() == 'true'
            color_category = request.form.get('color_category', 'neutral')

        if not name or not category_name:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Name and category are required'})
            else:
                flash("Name and category are required", 'danger')
                return redirect(url_for('admin.manage_default_tags'))

        # Validate category
        try:
            category = TagCategory[category_name]
        except KeyError:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Invalid category'})
            else:
                flash("Invalid category", 'danger')
                return redirect(url_for('admin.manage_default_tags'))

        # Check for duplicates (excluding current tag)
        existing = Tag.query.filter_by(name=name, is_default=True).filter(Tag.id != tag_id).first()
        if existing:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Another default tag with this name already exists'})
            else:
                flash('Another default tag with this name already exists', 'danger')
                return redirect(url_for('admin.manage_default_tags'))

        # Update tag
        tag.name = name
        tag.category = category
        tag.is_active = is_active
        tag.color_category = color_category

        db.session.commit()

        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Tag updated successfully',
                'tag': {
                    'id': tag.id,
                    'name': tag.name,
                    'category': tag.category.name,
                    'is_active': tag.is_active,
                    'color_category': tag.color_category
                }
            })
        else:
            flash(f"Configuration '{tag.name}' updated successfully", 'success')
            return redirect(url_for('admin.manage_default_tags'))

    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'message': f'Error updating tag: {str(e)}'})
        else:
            flash("Error updating configuration", 'danger')
            return redirect(url_for('admin.manage_default_tags'))


@admin_bp.route('/default-tags/<int:tag_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_default_tag(tag_id):
    """Delete a default tag via AJAX or Form submission"""
    try:
        tag = Tag.query.get_or_404(tag_id)

        if not tag.is_default:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Can only delete default tags'})
            else:
                flash('Can only delete default tags', 'danger')
                return redirect(url_for('admin.manage_default_tags'))

        tag_name = tag.name

        # Note: This will also remove the tag from any user's collection who had it
        db.session.delete(tag)
        db.session.commit()

        current_app.logger.info(f"Admin {current_user.username} deleted default tag: {tag_name}")

        if request.is_json:
            return jsonify({
                'success': True,
                'message': f"Default tag '{tag_name}' deleted successfully"
            })
        else:
            flash(f"Configuration '{tag_name}' removed successfully", 'success')
            return redirect(url_for('admin.manage_default_tags'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting default tag {tag_id}: {e}")
        if request.is_json:
            return jsonify({'success': False, 'message': 'Error deleting default tag'})
        else:
            flash("Error removing configuration", 'danger')
            return redirect(url_for('admin.manage_default_tags'))


@admin_bp.route('/default-tags/bulk-actions', methods=['POST'])
@login_required
@admin_required
def bulk_default_tags_actions():
    """Handle bulk actions on default tags from a standard form submission."""
    # Read from the submitted form data instead of JSON
    action = request.form.get('action')
    # Use getlist to receive multiple inputs with the same name ('tag_ids')
    tag_ids = request.form.getlist('tag_ids')

    if not tag_ids:
        flash("No tags were selected for the bulk action.", 'warning')
        return redirect(url_for('admin.manage_default_tags'))

    if action == 'delete_selected':
        deleted_count = 0
        for tag_id in tag_ids:
            tag = Tag.query.get(tag_id)
            if tag and tag.is_default:
                db.session.delete(tag)
                deleted_count += 1
        db.session.commit()
        flash(f"Successfully deleted {deleted_count} tags.", 'success')

    elif action == 'toggle_status':
        updated_count = 0
        for tag_id in tag_ids:
            tag = Tag.query.get(tag_id)
            if tag and tag.is_default:
                tag.is_active = not tag.is_active
                updated_count += 1
        db.session.commit()
        flash(f"Successfully updated the status for {updated_count} tags.", 'success')

    else:
        flash('An invalid bulk action was specified.', 'danger')

    # Redirect back to the tags page, where the flashed message will be displayed
    return redirect(url_for('admin.manage_default_tags'))


@admin_bp.route('/default-tags/seed', methods=['POST'])
@login_required
@admin_required
def seed_default_tags():
    """Seed Random's trading methodology default tags"""
    try:
        # Clear existing default tags
        Tag.query.filter_by(is_default=True).delete()

        # Create Random's tag system
        created_count = Tag.create_default_tags()

        db.session.commit()
        flash(f"Successfully created {created_count} trading tags!", 'success')
        current_app.logger.info(f"Admin {current_user.username} seeded default tags")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error seeding default tags: {e}")
        flash("Error creating default tags. Please try again.", 'danger')

    return redirect(url_for('admin.manage_default_tags'))


@admin_bp.route('/dashboard')
@login_required
@admin_required
def show_admin_dashboard():
    """Admin comprehensive dashboard with all system statistics and real-time health monitoring"""
    from datetime import datetime, timedelta
    import pytz

    def get_est_timestamp():
        """Get current time in EST/EDT timezone."""
        try:
            utc_now = datetime.utcnow()
            utc = pytz.utc
            est = pytz.timezone('US/Eastern')

            # Convert UTC to EST/EDT
            utc_now = utc.localize(utc_now)
            est_now = utc_now.astimezone(est)

            return est_now
        except:
            # Fallback if pytz not available
            utc_now = datetime.utcnow()
            est_offset = timedelta(hours=-5)  # Approximate EST
            return utc_now + est_offset

    def format_est_timestamp(dt=None):
        """Format timestamp as 24-hour EST/EDT time string."""
        if dt is None:
            dt = get_est_timestamp()

        try:
            return dt.strftime('%H:%M:%S EST')
        except:
            return datetime.now().strftime('%H:%M:%S EST')

    # Initialize default values
    total_users = "N/A"
    active_users_count = "N/A"
    admin_users_count = "N/A"
    total_instruments = 0
    active_instruments = 0
    inactive_instruments = 0
    instruments_by_class = []
    total_tags = 0
    active_tags = 0
    inactive_tags = 0
    tags_by_category = []
    default_models_count = 0
    current_timestamp = datetime.now()

    # Default system health data (fallback)
    system_health = {
        'overall_status': 'unknown',
        'components': {},
        'resources': {
            'instruments': {'active': 0, 'total': 0, 'percentage': 0},
            'tags': {'active': 0, 'total': 0, 'percentage': 0},
            'users': {'current': 0, 'capacity': 100, 'percentage': 0}
        },
        'last_updated_est': format_est_timestamp()
    }
    formatted_health = {}
    system_info = {
        'version': 'v2.1.0',
        'environment': 'Production',
        'last_updated': 'Today',
        'uptime_hours': 'N/A'
    }
    p12_active_count = p12_total_count = 0

    try:
        # Try to import system health monitoring
        try:
            from app.utils.system_health import get_system_health, format_status_display
            system_health_available = True
        except ImportError as e:
            current_app.logger.warning(f"System health monitoring not available: {e}")
            system_health_available = False

        # User statistics
        total_users = User.query.count()
        active_users_count = User.query.filter_by(is_active=True).count()
        admin_users_count = User.query.filter_by(role=UserRole.ADMIN).count()

        # Instrument statistics
        total_instruments = Instrument.query.count()
        active_instruments = Instrument.query.filter_by(is_active=True).count()
        inactive_instruments = total_instruments - active_instruments

        # Get instruments by asset class (active only)
        instruments_by_class = db.session.query(
            Instrument.asset_class,
            db.func.count(Instrument.id)
        ).filter_by(is_active=True).group_by(Instrument.asset_class).all()

        # Tag statistics
        total_tags = Tag.query.filter_by(is_default=True).count()
        active_tags = Tag.query.filter_by(is_default=True, is_active=True).count()
        inactive_tags = total_tags - active_tags

        # Get tags by category (active default tags only)
        from app.models import TagCategory
        tags_by_category = []
        for category in TagCategory:
            count = Tag.query.filter_by(
                is_default=True,
                is_active=True,
                category=category
            ).count()
            if count > 0:  # Only include categories with tags
                # Convert enum to display name
                category_name = category.value.replace(' & ', ' ').replace(' Factors', '')
                if len(category_name) > 15:  # Shorten long category names
                    category_name = category_name.replace('Psychological Emotional', 'Psychology')
                    category_name = category_name.replace('Execution Management', 'Execution')
                    category_name = category_name.replace('Market Conditions', 'Market')
                tags_by_category.append((category_name, count))

        # Trading Models count
        default_models_count = TradingModel.query.filter_by(is_default=True).count()

        # P12 scenario count
        p12_active_count = P12Scenario.query.filter_by(is_active=True).count()
        p12_total_count = P12Scenario.query.count()

        # ===== SYSTEM HEALTH MONITORING (with fallback) =====
        if system_health_available:
            try:
                # Get comprehensive system health status
                system_health = get_system_health()

                # Add EST timestamp
                system_health['last_updated_est'] = format_est_timestamp()

                # Format system health for template display
                formatted_health = {}
                for component_name, component_data in system_health.get('components', {}).items():
                    formatted_health[component_name] = {
                        'data': component_data,
                        'display': format_status_display(component_name, component_data)
                    }

                # System version info
                system_info = {
                    'version': 'v2.1.0',
                    'environment': current_app.config.get('ENVIRONMENT', 'Production'),
                    'last_updated': current_timestamp.strftime('%b %d, %Y'),
                    'uptime_hours': system_health.get('components', {}).get('application', {}).get('uptime_hours',
                                                                                                   'N/A')
                }

            except Exception as health_error:
                current_app.logger.warning(f"System health check failed: {health_error}")
                # Use fallback system health data (already initialized above)
                system_health['last_updated_est'] = format_est_timestamp()
        else:
            # Create basic system health data without advanced monitoring
            system_health = {
                'overall_status': 'operational',
                'components': {
                    'application': {'status': 'operational', 'details': 'Application running'},
                    'database': {'status': 'operational', 'details': 'Connected'},
                    'p12_engine': {'status': 'operational', 'details': f'{p12_active_count} Scenarios Active'},
                    'analytics_engine': {'status': 'maintenance', 'details': 'Scheduled Deployment'}
                },
                'resources': {
                    'instruments': {
                        'active': active_instruments,
                        'total': total_instruments,
                        'percentage': round((active_instruments / max(total_instruments, 1)) * 100, 1)
                    },
                    'tags': {
                        'active': active_tags,
                        'total': total_tags,
                        'percentage': round((active_tags / max(total_tags, 1)) * 100, 1)
                    },
                    'users': {
                        'current': total_users,
                        'capacity': 100,
                        'percentage': round((total_users / 100) * 100, 1) if isinstance(total_users, int) else 0
                    }
                },
                'last_updated_est': format_est_timestamp()
            }

            # Create basic formatted health data
            status_mapping = {
                'operational': {'class': 'status-operational', 'label': 'Operational'},
                'maintenance': {'class': 'status-maintenance', 'label': 'Maintenance'},
                'error': {'class': 'status-error', 'label': 'Error'}
            }

            formatted_health = {}
            for component_name, component_data in system_health['components'].items():
                status = component_data.get('status', 'operational')
                formatted_health[component_name] = {
                    'data': component_data,
                    'display': status_mapping.get(status, status_mapping['operational'])
                }

        current_app.logger.info(f"Admin {current_user.username} accessed comprehensive admin dashboard.")

    except Exception as e:
        current_app.logger.error(f"Error fetching admin dashboard stats: {e}", exc_info=True)
        flash("Could not load all dashboard statistics.", "warning")

        # Keep existing fallback values (already initialized above)
        system_health['last_updated_est'] = format_est_timestamp()

    # Get resource data from system_health
    resources = system_health.get('resources', {})


    return render_template('admin/dashboard.html',
                           title='Administration Center',
                           # Existing stats
                           total_users=total_users,
                           active_users_count=active_users_count,
                           admin_users_count=admin_users_count,
                           total_instruments=total_instruments,
                           active_instruments=active_instruments,
                           inactive_instruments=inactive_instruments,
                           instruments_by_class=instruments_by_class,
                           total_tags=total_tags,
                           active_tags=active_tags,
                           inactive_tags=inactive_tags,
                           tags_by_category=tags_by_category,
                           default_models_count=default_models_count,
                           current_timestamp=current_timestamp,
                           # New system health data
                           system_health=system_health,
                           formatted_health=formatted_health,
                           system_info=system_info,
                           resources=resources,
                           p12_active_count=p12_active_count,
                           p12_total_count=p12_total_count)


@admin_bp.route('/users')
@login_required
@admin_required
def admin_users_list():
    """Enhanced user list with search, filters, and sorting"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    # Get search and filter parameters
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '').strip()
    status_filter = request.args.get('status', '').strip()
    verified_filter = request.args.get('verified', '').strip()

    # Get sorting parameters
    sort_field = request.args.get('sort', 'username')  # Default sort by username
    sort_order = request.args.get('order', 'asc')  # Default ascending

    users_on_page, users_pagination, total_users_count, active_users_count, admin_users_count = [], None, 0, 0, 0

    try:
        # Start building the query
        query = User.query

        # Apply search filter
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                db.or_(
                    User.username.ilike(search_term),
                    User.email.ilike(search_term),
                    User.name.ilike(search_term),
                    User.discord_username.ilike(search_term)
                )
            )

        # Apply role filter
        if role_filter:
            try:
                role_enum = UserRole[role_filter.upper()]
                query = query.filter(User.role == role_enum)
            except KeyError:
                current_app.logger.warning(f"Invalid role filter: {role_filter}")

        # Apply status filter
        if status_filter:
            if status_filter.lower() == 'active':
                query = query.filter(User.is_active == True)
            elif status_filter.lower() == 'inactive':
                query = query.filter(User.is_active == False)

        # Apply verification filter
        if verified_filter:
            if verified_filter.lower() == 'verified':
                query = query.filter(User.is_email_verified == True)
            elif verified_filter.lower() == 'unverified':
                query = query.filter(User.is_email_verified == False)

        # Apply sorting
        if sort_field and hasattr(User, sort_field):
            sort_column = getattr(User, sort_field)
            if sort_order.lower() == 'desc':
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            # Default sorting
            query = query.order_by(User.username.asc())

        # Execute paginated query
        users_pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        users_on_page = users_pagination.items

        # Get overall counts (for KPI cards)
        total_users_count = User.query.count()
        active_users_count = User.query.filter_by(is_active=True).count()
        admin_users_count = User.query.filter_by(role=UserRole.ADMIN).count()  # Still needed for delete logic
        
        # New enhanced KPI metrics
        discord_connected_count = User.query.filter_by(discord_linked=True).count()
        
        # Recent activity (last 7 days)
        from datetime import datetime, timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_activity_count = User.query.filter(User.last_login >= seven_days_ago).count()
        
        # New users this month
        first_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_users_this_month = User.query.filter(User.created_at >= first_of_month).count()
        
        # Inactive accounts (90+ days)
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        inactive_accounts_count = User.query.filter(
            db.or_(
                User.last_login.is_(None),
                User.last_login < ninety_days_ago
            ),
            User.is_active == True  # Only count active accounts that are inactive
        ).count()

        # Log the admin action
        search_info = f" with search='{search}'" if search else ""
        filter_info = f" with filters: role={role_filter}, status={status_filter}, verified={verified_filter}" if any(
            [role_filter, status_filter, verified_filter]) else ""
        current_app.logger.info(
            f"Admin {current_user.username} accessed user list page {page}{search_info}{filter_info}.")

    except Exception as e:
        current_app.logger.error(f"Error fetching user list for admin: {e}", exc_info=True)
        flash("Could not load user list.", "danger")
        total_users_count = active_users_count = admin_users_count = discord_connected_count = recent_activity_count = new_users_this_month = inactive_accounts_count = "Error"

    return render_template('admin/users.html',
                           title='User Administration Console',
                           users=users_on_page,
                           pagination=users_pagination,
                           total_users_count=total_users_count,
                           active_users_count=active_users_count,
                           admin_users_count=admin_users_count,
                           discord_connected_count=discord_connected_count,
                           recent_activity_count=recent_activity_count,
                           new_users_this_month=new_users_this_month,
                           inactive_accounts_count=inactive_accounts_count,
                           UserRole=UserRole)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_user():
    form = AdminCreateUserForm()
    if form.validate_on_submit():
        if User.find_by_username(form.username.data):
            flash('Username already exists.', 'danger')
        elif User.find_by_email(form.email.data):
            flash('Email address is already registered.', 'danger')
        else:
            try:
                new_user = User(
                    username=form.username.data,
                    email=form.email.data.lower(),
                    name=form.name.data if form.name.data else None,
                    role=UserRole(form.role.data),
                    is_active=form.is_active.data,
                    is_email_verified=form.is_email_verified.data
                )
                new_user.set_password(form.password.data)
                db.session.add(new_user)
                db.session.commit()
                flash_message = f"User {new_user.username} created successfully"
                flash_category = 'success'
                if not new_user.is_email_verified:
                    token = generate_token(new_user.email, salt='email-verification-salt')
                    verification_url = url_for('auth.verify_email', token=token, _external=True)
                    email_sent = send_email(
                        to=new_user.email,
                        subject="Your Account Was Created - Verify Your Email",
                        template_name="verify_email.html",
                        username=new_user.username,
                        verification_url=verification_url
                    )
                    if email_sent:
                        flash_message += ". A verification email has been sent."
                    else:
                        flash_message += ". Verification email could not be sent."
                        flash_category = 'warning'
                record_activity('admin_user_create', f"Admin {current_user.username} created user: {new_user.username}",
                                user_id_for_activity=current_user.id)
                flash(flash_message, flash_category)
                return redirect(url_for('admin.admin_users_list'))
            except ValueError:
                flash('Invalid role selected.', 'danger')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error creating user by admin {current_user.username}: {e}", exc_info=True)
                flash(f'An error occurred: {str(e)}', 'danger')
    elif request.method == 'POST':
        flash('Please correct form errors.', 'warning')
    return render_template('create_user.html', title='Create New User', form=form)


@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    user_to_edit = User.query.get_or_404(user_id)
    form = AdminEditUserForm(obj=user_to_edit)
    if request.method == 'GET':  # Pre-populate role correctly for GET
        form.role.data = user_to_edit.role.value if user_to_edit.role else None

    if form.validate_on_submit():
        if form.username.data != user_to_edit.username and User.query.filter(User.username == form.username.data,
                                                                             User.id != user_id).first():
            flash('That username is already taken.', 'danger')
        elif form.email.data.lower() != user_to_edit.email and User.query.filter(User.email == form.email.data.lower(),
                                                                                 User.id != user_id).first():
            flash('That email address is already registered.', 'danger')
        else:
            try:
                user_to_edit.username = form.username.data
                if user_to_edit.email != form.email.data.lower():  # If email changed
                    user_to_edit.email = form.email.data.lower()
                    user_to_edit.is_email_verified = False  # Require re-verification if admin doesn't check the box
                    # Or send new verification email
                user_to_edit.name = form.name.data if form.name.data else None
                user_to_edit.role = UserRole(form.role.data)
                user_to_edit.is_active = form.is_active.data
                user_to_edit.is_email_verified = form.is_email_verified.data  # Allow admin to set this

                if form.new_password.data:
                    user_to_edit.set_password(form.new_password.data)
                    flash('User password has been updated.', 'info')

                db.session.commit()
                record_activity('admin_user_edit',
                                f"Admin {current_user.username} edited user: {user_to_edit.username}",
                                user_id_for_activity=current_user.id)
                flash(f"User {user_to_edit.username} updated.", 'success')
                return redirect(url_for('admin.admin_users_list'))
            except ValueError:
                flash('Invalid role selected.', 'danger')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error editing user {user_id} by admin {current_user.username}: {e}",
                                         exc_info=True)
                flash(f'An error occurred: {str(e)}', 'danger')
    elif request.method == 'POST':
        flash('Please correct form errors.', 'warning')
    return render_template('edit_user.html', title='Edit User', form=form, user_id=user_id,
                           username=user_to_edit.username)


@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user_to_delete = User.query.get_or_404(user_id)
    if user_to_delete.id == current_user.id:
        flash("You cannot delete your own account.", 'danger')
        return redirect(url_for('admin.admin_users_list'))
    if user_to_delete.is_admin() and User.query.filter_by(role=UserRole.ADMIN).count() <= 1:
        flash("Cannot delete the last admin account.", 'warning')
        return redirect(url_for('admin.admin_users_list'))

    try:
        username_for_log = user_to_delete.username
        current_app.logger.info(f"Deleting related records for user {user_id}")
        
        # Delete related records first (avoid foreign key constraints)
        Activity.query.filter_by(user_id=user_id).delete()

        # Delete P12UsageStats records to avoid NOT NULL constraint error
        from app.models import P12UsageStats
        P12UsageStats.query.filter_by(user_id=user_id).delete()

        # Delete other user-related records to avoid foreign key constraints
        from app.models import GlobalImage, TagUsageStats, UserSession, UserAccessLog, TradeImage, DailyJournalImage
        GlobalImage.query.filter_by(user_id=user_id).delete()
        TagUsageStats.query.filter_by(user_id=user_id).delete()
        UserSession.query.filter_by(user_id=user_id).delete()
        UserAccessLog.query.filter_by(user_id=user_id).delete()
        TradeImage.query.filter_by(user_id=user_id).delete()
        DailyJournalImage.query.filter_by(user_id=user_id).delete()

        # Note: Other models with proper cascade relationships will be handled automatically
        current_app.logger.info(f"Deleting user record: {username_for_log}")
        db.session.delete(user_to_delete)
        db.session.commit()
        record_activity('admin_user_delete', f"Admin {current_user.username} deleted user: {username_for_log}",
                        user_id_for_activity=current_user.id)
        flash('User resource ' + username_for_log + ' has been successfully deprovisioned.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user {user_id} by admin {current_user.username}: {e}", exc_info=True)
        flash(f'Error deleting user: {str(e)}', 'danger')
    return redirect(url_for('admin.admin_users_list'))

@admin_bp.route('/users/bulk_delete', methods=['POST'])
@login_required
@admin_required
def admin_bulk_delete_users():
    """Handles bulk deletion of users by an admin."""
    try:
        current_app.logger.info(f"Bulk delete called by {current_user.username}")

        # Get JSON data
        data = request.get_json()
        current_app.logger.info(f"Received data: {data}")

        if not data or 'user_ids' not in data:
            current_app.logger.error("Missing user_ids parameter")
            return jsonify({'status': 'error', 'message': 'Missing user_ids parameter.'}), 400

        user_ids_to_delete_str = data['user_ids']
        if not isinstance(user_ids_to_delete_str, list):
            current_app.logger.error("user_ids must be a list")
            return jsonify({'status': 'error', 'message': 'user_ids must be a list.'}), 400

        deleted_count = 0
        skipped_count = 0
        skipped_users_info = []

        # Convert string IDs to integers
        user_ids_to_delete = []
        for user_id_str_item in user_ids_to_delete_str:
            try:
                user_ids_to_delete.append(int(user_id_str_item))
            except ValueError:
                skipped_count += 1
                skipped_users_info.append(f"Invalid User ID format: {user_id_str_item}")

        if not user_ids_to_delete:
            return jsonify({'status': 'error', 'message': 'No valid user IDs provided for deletion.'}), 400

        # Get current admin count
        admin_users_total_in_db = User.query.filter_by(role=UserRole.ADMIN).count()
        current_app.logger.info(f"Current admin count: {admin_users_total_in_db}")

        # Process each user for deletion
        for user_id in user_ids_to_delete:
            current_app.logger.info(f"Processing user ID: {user_id}")

            # Check if trying to delete self
            if user_id == current_user.id:
                skipped_count += 1
                skipped_users_info.append(f"User ID {user_id} (cannot delete self)")
                current_app.logger.warning(f"User {current_user.username} tried to delete themselves")
                continue

            # Get the user
            user_to_delete = User.query.get(user_id)
            if not user_to_delete:
                skipped_count += 1
                skipped_users_info.append(f"User ID {user_id} (not found)")
                current_app.logger.warning(f"User ID {user_id} not found")
                continue

            # Check if it's the last admin
            if user_to_delete.is_admin() and admin_users_total_in_db <= 1:
                skipped_count += 1
                skipped_users_info.append(f"{user_to_delete.username} (cannot delete last admin)")
                current_app.logger.warning(f"Cannot delete last admin: {user_to_delete.username}")
                continue

            username_for_log = user_to_delete.username
            current_app.logger.info(f"Attempting to delete user: {username_for_log} (ID: {user_id})")

            try:
                # Delete related records first (avoid foreign key constraints)
                current_app.logger.info(f"Deleting activities for user {user_id}")
                Activity.query.filter_by(user_id=user_id).delete()

                # Delete P12UsageStats records to avoid NOT NULL constraint error
                current_app.logger.info(f"Deleting P12 usage stats for user {user_id}")
                from app.models import P12UsageStats
                P12UsageStats.query.filter_by(user_id=user_id).delete()

                # Delete other user-related records to avoid foreign key constraints
                current_app.logger.info(f"Deleting global images for user {user_id}")
                from app.models import GlobalImage
                GlobalImage.query.filter_by(user_id=user_id).delete()

                current_app.logger.info(f"Deleting tag usage stats for user {user_id}")
                from app.models import TagUsageStats
                TagUsageStats.query.filter_by(user_id=user_id).delete()

                # Delete session and access log records
                current_app.logger.info(f"Deleting user sessions for user {user_id}")
                from app.models import UserSession, UserAccessLog
                UserSession.query.filter_by(user_id=user_id).delete()
                UserAccessLog.query.filter_by(user_id=user_id).delete()

                # Delete image records that might not cascade properly
                current_app.logger.info(f"Deleting trade images for user {user_id}")
                from app.models import TradeImage, DailyJournalImage
                TradeImage.query.filter_by(user_id=user_id).delete()
                DailyJournalImage.query.filter_by(user_id=user_id).delete()

                # Note: Other models with proper cascade relationships will be handled automatically
                # These include: TradingModel, Trade, DailyJournal, Files, Settings, etc.

                # Delete the user
                current_app.logger.info(f"Deleting user record: {username_for_log}")
                db.session.delete(user_to_delete)

                # Update admin count if this was an admin
                if user_to_delete.is_admin():
                    admin_users_total_in_db -= 1
                    current_app.logger.info(f"Admin count reduced to: {admin_users_total_in_db}")

                # Log the activity (but don't commit yet)
                record_activity('admin_bulk_user_delete',
                                f"Admin {current_user.username} bulk deleted user: {username_for_log} (ID: {user_id})",
                                user_id_for_activity=current_user.id)

                deleted_count += 1
                current_app.logger.info(f"Successfully processed deletion for: {username_for_log}")

            except Exception as e:
                current_app.logger.error(f"Error deleting user {username_for_log}: {str(e)}", exc_info=True)
                skipped_count += 1
                skipped_users_info.append(f"{username_for_log} (error: {str(e)})")
                # Continue processing other users

        # Commit all changes at once
        try:
            if deleted_count > 0:
                current_app.logger.info(f"Committing deletion of {deleted_count} users")
                db.session.commit()
                message = f"Successfully deleted {deleted_count} user(s)."
                status = 'success'
                current_app.logger.info(f"Bulk delete successful: {deleted_count} users deleted")
            else:
                current_app.logger.info("No users were deleted")
                message = "No users were deleted."
                status = 'success'

        except Exception as e:
            current_app.logger.error(f"Error committing bulk delete: {str(e)}", exc_info=True)
            db.session.rollback()
            message = f'Error during deletion: {str(e)}'
            status = 'error'

        # Add skipped info to message
        if skipped_count > 0:
            message += f" Skipped {skipped_count} user(s)."

        response_data = {
            'status': status,
            'message': message,
            'deleted_count': deleted_count,
            'skipped_count': skipped_count,
            'skipped_info': skipped_users_info
        }

        current_app.logger.info(f"Bulk delete response: {response_data}")
        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Unexpected error in bulk delete: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'Unexpected error: {str(e)}'}), 500


@admin_bp.route('/users/bulk_activate', methods=['POST'])
@login_required
@admin_required
def admin_bulk_activate_users():
    """Handles bulk activation of users by an admin."""
    try:
        current_app.logger.info(f"Bulk activate called by {current_user.username}")

        data = request.get_json()
        current_app.logger.info(f"Received data: {data}")

        if not data or 'user_ids' not in data:
            return jsonify({'status': 'error', 'message': 'Missing user_ids parameter.'}), 400

        user_ids_to_activate_str = data['user_ids']
        if not isinstance(user_ids_to_activate_str, list):
            return jsonify({'status': 'error', 'message': 'user_ids must be a list.'}), 400

        activated_count = 0
        skipped_count = 0
        skipped_users_info = []

        user_ids_to_activate = []
        for user_id_str_item in user_ids_to_activate_str:
            try:
                user_ids_to_activate.append(int(user_id_str_item))
            except ValueError:
                skipped_count += 1
                skipped_users_info.append(f"Invalid User ID format: {user_id_str_item}")

        if not user_ids_to_activate:
            return jsonify({'status': 'error', 'message': 'No valid user IDs provided.'}), 400

        for user_id in user_ids_to_activate:
            try:
                user_to_activate = User.query.get(user_id)
                if not user_to_activate:
                    skipped_count += 1
                    skipped_users_info.append(f"User ID {user_id} (not found)")
                    continue

                if user_to_activate.is_active:
                    skipped_count += 1
                    skipped_users_info.append(f"User {user_to_activate.username} (already active)")
                    continue

                user_to_activate.is_active = True
                activated_count += 1

            except Exception as e:
                skipped_count += 1
                skipped_users_info.append(f"User ID {user_id} (error: {str(e)})")

        db.session.commit()
        record_activity('admin_bulk_activate_users',
                        f"Admin {current_user.username} activated {activated_count} users",
                        user_id_for_activity=current_user.id)

        message = f"Successfully activated {activated_count} user(s)."
        if skipped_count > 0:
            message += f" Skipped {skipped_count} user(s)."

        return jsonify({
            'status': 'success',
            'message': message,
            'activated_count': activated_count,
            'skipped_count': skipped_count,
            'skipped_info': skipped_users_info
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk user activation: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'Bulk activation failed: {str(e)}'}), 500


@admin_bp.route('/users/bulk_deactivate', methods=['POST'])
@login_required
@admin_required
def admin_bulk_deactivate_users():
    """Handles bulk deactivation of users by an admin."""
    try:
        current_app.logger.info(f"Bulk deactivate called by {current_user.username}")

        data = request.get_json()
        current_app.logger.info(f"Received data: {data}")

        if not data or 'user_ids' not in data:
            return jsonify({'status': 'error', 'message': 'Missing user_ids parameter.'}), 400

        user_ids_to_deactivate_str = data['user_ids']
        if not isinstance(user_ids_to_deactivate_str, list):
            return jsonify({'status': 'error', 'message': 'user_ids must be a list.'}), 400

        deactivated_count = 0
        skipped_count = 0
        skipped_users_info = []

        user_ids_to_deactivate = []
        for user_id_str_item in user_ids_to_deactivate_str:
            try:
                user_ids_to_deactivate.append(int(user_id_str_item))
            except ValueError:
                skipped_count += 1
                skipped_users_info.append(f"Invalid User ID format: {user_id_str_item}")

        if not user_ids_to_deactivate:
            return jsonify({'status': 'error', 'message': 'No valid user IDs provided.'}), 400

        admin_users_total_in_db = User.query.filter_by(role=UserRole.ADMIN).count()

        for user_id in user_ids_to_deactivate:
            try:
                user_to_deactivate = User.query.get(user_id)
                if not user_to_deactivate:
                    skipped_count += 1
                    skipped_users_info.append(f"User ID {user_id} (not found)")
                    continue

                if user_id == current_user.id:
                    skipped_count += 1
                    skipped_users_info.append(f"User {user_to_deactivate.username} (cannot deactivate self)")
                    continue

                if user_to_deactivate.is_admin() and admin_users_total_in_db <= 1:
                    skipped_count += 1
                    skipped_users_info.append(f"User {user_to_deactivate.username} (cannot deactivate last admin)")
                    continue

                if not user_to_deactivate.is_active:
                    skipped_count += 1
                    skipped_users_info.append(f"User {user_to_deactivate.username} (already inactive)")
                    continue

                user_to_deactivate.is_active = False
                deactivated_count += 1

            except Exception as e:
                skipped_count += 1
                skipped_users_info.append(f"User ID {user_id} (error: {str(e)})")

        db.session.commit()
        record_activity('admin_bulk_deactivate_users',
                        f"Admin {current_user.username} deactivated {deactivated_count} users",
                        user_id_for_activity=current_user.id)

        message = f"Successfully deactivated {deactivated_count} user(s)."
        if skipped_count > 0:
            message += f" Skipped {skipped_count} user(s)."

        return jsonify({
            'status': 'success',
            'message': message,
            'deactivated_count': deactivated_count,
            'skipped_count': skipped_count,
            'skipped_info': skipped_users_info
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk user deactivation: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'Bulk deactivation failed: {str(e)}'}), 500


@admin_bp.route('/users/bulk_reset_passwords', methods=['POST'])
@login_required
@admin_required
def admin_bulk_reset_passwords():
    """Handles bulk password reset for users by an admin."""
    try:
        current_app.logger.info(f"Bulk password reset called by {current_user.username}")

        data = request.get_json()
        current_app.logger.info(f"Received data: {data}")

        if not data or 'user_ids' not in data:
            return jsonify({'status': 'error', 'message': 'Missing user_ids parameter.'}), 400

        user_ids_to_reset_str = data['user_ids']
        if not isinstance(user_ids_to_reset_str, list):
            return jsonify({'status': 'error', 'message': 'user_ids must be a list.'}), 400

        reset_count = 0
        skipped_count = 0
        skipped_users_info = []

        user_ids_to_reset = []
        for user_id_str_item in user_ids_to_reset_str:
            try:
                user_ids_to_reset.append(int(user_id_str_item))
            except ValueError:
                skipped_count += 1
                skipped_users_info.append(f"Invalid User ID format: {user_id_str_item}")

        if not user_ids_to_reset:
            return jsonify({'status': 'error', 'message': 'No valid user IDs provided.'}), 400

        for user_id in user_ids_to_reset:
            try:
                user_to_reset = User.query.get(user_id)
                if not user_to_reset:
                    skipped_count += 1
                    skipped_users_info.append(f"User ID {user_id} (not found)")
                    continue

                # Generate new password
                import secrets
                import string
                new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))

                # Set new password
                user_to_reset.set_password(new_password)

                # Try to send email (skip if email fails)
                try:
                    email_sent = send_email(
                        to=user_to_reset.email,
                        subject="Your Password Has Been Reset - Trading Journal",
                        template_name="password_reset_by_admin.html",
                        username=user_to_reset.username,
                        new_password=new_password,
                        reset_by_admin=current_user.username
                    )
                    reset_count += 1
                except:
                    # Still count as success even if email fails
                    reset_count += 1
                    skipped_users_info.append(f"User {user_to_reset.username} (password reset, email failed)")

            except Exception as e:
                skipped_count += 1
                skipped_users_info.append(f"User ID {user_id} (error: {str(e)})")

        db.session.commit()
        record_activity('admin_bulk_reset_passwords',
                        f"Admin {current_user.username} reset passwords for {reset_count} users",
                        user_id_for_activity=current_user.id)

        message = f"Successfully reset passwords for {reset_count} user(s)."
        if skipped_count > 0:
            message += f" Skipped {skipped_count} user(s)."

        return jsonify({
            'status': 'success',
            'message': message,
            'reset_count': reset_count,
            'skipped_count': skipped_count,
            'skipped_info': skipped_users_info
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk password reset: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'Password reset failed: {str(e)}'}), 500


@admin_bp.route('/users/bulk_verify_emails', methods=['POST'])
@login_required
@admin_required
def admin_bulk_verify_emails():
    """Handles bulk email verification for users by an admin."""
    try:
        current_app.logger.info(f"Bulk email verification called by {current_user.username}")

        data = request.get_json()
        current_app.logger.info(f"Received data: {data}")

        if not data or 'user_ids' not in data:
            return jsonify({'status': 'error', 'message': 'Missing user_ids parameter.'}), 400

        user_ids_to_verify_str = data['user_ids']
        if not isinstance(user_ids_to_verify_str, list):
            return jsonify({'status': 'error', 'message': 'user_ids must be a list.'}), 400

        verified_count = 0
        skipped_count = 0
        skipped_users_info = []

        user_ids_to_verify = []
        for user_id_str_item in user_ids_to_verify_str:
            try:
                user_ids_to_verify.append(int(user_id_str_item))
            except ValueError:
                skipped_count += 1
                skipped_users_info.append(f"Invalid User ID format: {user_id_str_item}")

        if not user_ids_to_verify:
            return jsonify({'status': 'error', 'message': 'No valid user IDs provided.'}), 400

        for user_id in user_ids_to_verify:
            try:
                user_to_verify = User.query.get(user_id)
                if not user_to_verify:
                    skipped_count += 1
                    skipped_users_info.append(f"User ID {user_id} (not found)")
                    continue

                if user_to_verify.is_email_verified:
                    skipped_count += 1
                    skipped_users_info.append(f"User {user_to_verify.username} (email already verified)")
                    continue

                user_to_verify.is_email_verified = True
                verified_count += 1

            except Exception as e:
                skipped_count += 1
                skipped_users_info.append(f"User ID {user_id} (error: {str(e)})")

        db.session.commit()
        record_activity('admin_bulk_verify_emails',
                        f"Admin {current_user.username} verified emails for {verified_count} users",
                        user_id_for_activity=current_user.id)

        message = f"Successfully verified emails for {verified_count} user(s)."
        if skipped_count > 0:
            message += f" Skipped {skipped_count} user(s)."

        return jsonify({
            'status': 'success',
            'message': message,
            'verified_count': verified_count,
            'skipped_count': skipped_count,
            'skipped_info': skipped_users_info
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk email verification: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'Email verification failed: {str(e)}'}), 500

@admin_bp.route('/system-config')
@login_required
@admin_required
def system_config():
    """Admin system configuration dashboard"""
    try:
        # Existing instrument statistics
        total_instruments = Instrument.query.count()
        active_instruments = Instrument.query.filter_by(is_active=True).count()
        inactive_instruments = total_instruments - active_instruments
        default_models_count = TradingModel.query.filter_by(is_default=True).count()

        # Get instruments by asset class (active only)
        instruments_by_class = db.session.query(
            Instrument.asset_class,
            db.func.count(Instrument.id)
        ).filter_by(is_active=True).group_by(Instrument.asset_class).all()

        # NEW: Tag statistics
        total_tags = Tag.query.filter_by(is_default=True).count()
        active_tags = Tag.query.filter_by(is_default=True, is_active=True).count()
        inactive_tags = total_tags - active_tags

        # Get tags by category (active default tags only)
        from app.models import TagCategory
        tags_by_category = []
        for category in TagCategory:
            count = Tag.query.filter_by(
                is_default=True,
                is_active=True,
                category=category
            ).count()
            if count > 0:  # Only include categories with tags
                # Convert enum to display name
                category_name = category.value.replace(' & ', ' ').replace(' Factors', '')
                if len(category_name) > 15:  # Shorten long category names
                    category_name = category_name.replace('Psychological Emotional', 'Psychology')
                    category_name = category_name.replace('Execution Management', 'Execution')
                    category_name = category_name.replace('Market Conditions', 'Market')
                tags_by_category.append((category_name, count))

        current_app.logger.info(f"Admin {current_user.username} accessed system configuration")

        return render_template('admin/system_config.html',
                               title='System Configuration',
                               total_instruments=total_instruments,
                               active_instruments=active_instruments,
                               inactive_instruments=inactive_instruments,
                               instruments_by_class=instruments_by_class,
                               total_tags=total_tags,
                               active_tags=active_tags,
                               inactive_tags=inactive_tags,
                               tags_by_category=tags_by_category,
                               default_models_count=default_models_count)

    except Exception as e:
        current_app.logger.error(f"Error loading system configuration: {e}", exc_info=True)
        flash("Could not load system configuration data.", "danger")
        return redirect(url_for('admin.show_admin_dashboard'))


@admin_bp.route('/instruments')
@login_required
@admin_required
def instruments_list():
    """List all instruments with filtering and sorting"""
    try:
        from app.models import Instrument
        from app.forms import InstrumentFilterForm

        filter_form = InstrumentFilterForm(request.args, meta={'csrf': False})

        # Build query with filters
        query = Instrument.query

        # Search filter
        if filter_form.search.data:
            search_term = f"%{filter_form.search.data}%"
            query = query.filter(
                db.or_(
                    Instrument.symbol.ilike(search_term),
                    Instrument.name.ilike(search_term)
                )
            )

        # Exchange filter
        if filter_form.exchange.data:
            query = query.filter(Instrument.exchange == filter_form.exchange.data)

        # Asset class filter
        if filter_form.asset_class.data:
            query = query.filter(Instrument.asset_class == filter_form.asset_class.data)

        # Status filter
        if filter_form.status.data == 'active':
            query = query.filter(Instrument.is_active == True)
        elif filter_form.status.data == 'inactive':
            query = query.filter(Instrument.is_active == False)

        # Calculate KPI data from FULL dataset (before filtering)
        all_instruments = Instrument.query.all()
        active_instruments_count = len([i for i in all_instruments if i.is_active])
        unique_asset_classes_count = len(set(i.asset_class for i in all_instruments if i.asset_class))
        unique_exchanges_count = len(set(i.exchange for i in all_instruments if i.exchange))
        total_count = len(all_instruments)

        # Sorting
        sort_field = request.args.get('sort', 'symbol')
        sort_order = request.args.get('order', 'asc')
        
        # Map sort fields to model attributes
        sort_mapping = {
            'symbol': Instrument.symbol,
            'name': Instrument.name,
            'exchange': Instrument.exchange,
            'asset_class': Instrument.asset_class,
            'point_value': Instrument.point_value,
            'is_active': Instrument.is_active
        }
        
        sort_column = sort_mapping.get(sort_field, Instrument.symbol)
        
        if sort_order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)  # Default 10, allow override
        
        # Ensure per_page is within reasonable limits
        per_page = max(10, min(per_page, 100))

        instruments_pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )

        current_app.logger.info(f"Admin {current_user.username} accessed instruments list (page {page}, {per_page} per page).")

        return render_template('admin/instruments_list.html',
                               title='Instrument Management',
                               instruments=instruments_pagination.items,
                               pagination=instruments_pagination,
                               filter_form=filter_form,
                               total_count=total_count,
                               # KPI data for cards
                               active_instruments_count=active_instruments_count,
                               unique_asset_classes_count=unique_asset_classes_count,
                               unique_exchanges_count=unique_exchanges_count)

    except Exception as e:
        current_app.logger.error(f"Error loading instruments list: {e}", exc_info=True)
        flash("Could not load instruments list.", "danger")
        return redirect(url_for('admin.show_admin_dashboard'))


@admin_bp.route('/instruments/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_instrument():
    """Create a new instrument"""
    try:
        from app.models import Instrument
        from app.forms import InstrumentForm

        form = InstrumentForm()

        if form.validate_on_submit():
            # Check if symbol already exists
            existing_instrument = Instrument.query.filter_by(symbol=form.symbol.data.upper()).first()
            if existing_instrument:
                flash(f'Instrument with symbol \'{form.symbol.data.upper()}\' already exists.', 'danger')
                return render_template('create_instrument.html', title='Create Instrument', form=form)

            # Create new instrument
            instrument = Instrument(
                symbol=form.symbol.data.upper(),
                name=form.name.data,
                exchange=form.exchange.data,
                asset_class=form.asset_class.data,
                product_group=form.product_group.data,
                point_value=form.point_value.data,
                tick_size=form.tick_size.data,
                currency=form.currency.data,
                is_active=form.is_active.data
            )

            db.session.add(instrument)
            db.session.commit()

            flash(f'Instrument \'{instrument.symbol}\' created successfully!', 'success')
            current_app.logger.info(f"Admin {current_user.username} created instrument {instrument.symbol}.")

            return redirect(url_for('admin.instruments_list'))

        return render_template('create_instrument.html', title='Create Instrument', form=form)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in create_instrument: {e}", exc_info=True)
        flash('An error occurred while creating the instrument.', 'danger')
        return redirect(url_for('admin.instruments_list'))


@admin_bp.route('/instruments/<int:instrument_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_instrument(instrument_id):
    """Edit an existing instrument"""
    try:
        from app.models import Instrument
        from app.forms import InstrumentForm

        instrument = Instrument.query.get_or_404(instrument_id)
        form = InstrumentForm(obj=instrument)

        if form.validate_on_submit():
            # Check if changing symbol to an existing one
            if form.symbol.data.upper() != instrument.symbol:
                existing_instrument = Instrument.query.filter_by(symbol=form.symbol.data.upper()).first()
                if existing_instrument:
                    flash(f'Instrument with symbol "{form.symbol.data.upper()}" already exists.', 'danger')
                    return render_template('edit_instrument.html',
                                           title=f'Edit Instrument - {instrument.symbol}',
                                           form=form, instrument=instrument)

            # Update instrument
            instrument.symbol = form.symbol.data.upper()
            instrument.name = form.name.data
            instrument.exchange = form.exchange.data
            instrument.asset_class = form.asset_class.data
            instrument.product_group = form.product_group.data
            instrument.point_value = form.point_value.data
            instrument.tick_size = form.tick_size.data
            instrument.currency = form.currency.data
            instrument.is_active = form.is_active.data

            from datetime import datetime
            instrument.updated_at = datetime.utcnow()

            db.session.commit()

            flash(f"Instrument '{instrument.symbol}' updated successfully!", 'success')
            current_app.logger.info(f"Admin {current_user.username} updated instrument {instrument.symbol}.")

            return redirect(url_for('admin.instruments_list'))

        return render_template('edit_instrument.html',
                               title=f'Edit Instrument - {instrument.symbol}',
                               form=form, instrument=instrument)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error editing instrument {instrument_id}: {e}", exc_info=True)
        flash('An error occurred while updating the instrument.', 'danger')
        return redirect(url_for('admin.instruments_list'))


@admin_bp.route('/instruments/<int:instrument_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_instrument_status(instrument_id):
    """Toggle instrument active/inactive status"""
    try:
        from app.models import Instrument
        from datetime import datetime

        instrument = Instrument.query.get_or_404(instrument_id)
        old_status = "active" if instrument.is_active else "inactive"
        instrument.is_active = not instrument.is_active
        instrument.updated_at = datetime.utcnow()

        db.session.commit()

        new_status = "active" if instrument.is_active else "inactive"
        flash(f"Instrument '{instrument.symbol}' changed from {old_status} to {new_status}!", 'success')
        current_app.logger.info(
            f"Admin {current_user.username} toggled instrument {instrument.symbol} status to {new_status}.")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling instrument status {instrument_id}: {e}", exc_info=True)
        flash('An error occurred while updating the instrument status.', 'danger')

    return redirect(url_for('admin.instruments_list'))


@admin_bp.route('/instruments/<int:instrument_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_instrument(instrument_id):
    """Delete an instrument (only if no trades exist)"""
    try:
        from app.models import Instrument

        instrument = Instrument.query.get_or_404(instrument_id)

        # Check if any trades exist for this instrument
        trades_count = instrument.trades.count()
        if trades_count > 0:
            flash(f'Cannot delete instrument \'{instrument.symbol}\'. It has {trades_count} associated trades. '
                  f'Deactivate it instead if you want to stop using it.', 'warning')
            return redirect(url_for('admin.instruments_list'))

        symbol = instrument.symbol
        db.session.delete(instrument)
        db.session.commit()

        flash(f'Instrument \'{symbol}\' deleted successfully!', 'success')
        current_app.logger.info(f"Admin {current_user.username} deleted instrument {symbol}.")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting instrument {instrument_id}: {e}", exc_info=True)
        flash('An error occurred while deleting the instrument.', 'danger')

    return redirect(url_for('admin.instruments_list'))


@admin_bp.route('/default-tags')
@login_required
@admin_required
def manage_default_tags():
    """Admin page to manage default tags"""
    # Get ALL default tags (both active and inactive) for admin management
    tags = Tag.query.filter_by(is_default=True).order_by(Tag.category, Tag.name).all()

    # Organize by category manually since we're not using the model method
    from app.models import TagCategory
    tags_by_category = {}
    for category in TagCategory:
        tags_by_category[category.value] = [tag for tag in tags if tag.category == category]

    return render_template('admin/default_tags.html',
                           title='Manage Default Tags',
                           tags_by_category=tags_by_category,
                           TagCategory=TagCategory)


@admin_bp.route('/default-tags/add-category', methods=['POST'])
@login_required
@admin_required
def add_tag_category():
    """Add a new tag category (this would require enum modification)"""
    # For now, return a message that this requires code changes
    return jsonify({
        'success': False,
        'message': 'Adding new categories requires code deployment. Current categories are fixed in the TagCategory enum.'
    })


@admin_bp.route('/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """Enhanced administration center with real-time system health monitoring."""
    try:
        # Import system health monitoring
        from app.utils.system_health import get_system_health, format_status_display

        # Get current timestamp
        current_timestamp = datetime.utcnow()

        # ===== EXISTING STATS COLLECTION =====

        # User statistics
        total_users = User.query.filter_by(is_active=True).count()
        active_users_count = User.query.filter(
            User.is_active == True,
            User.last_login >= datetime.utcnow() - timedelta(days=30)
        ).count()
        admin_users_count = User.query.filter_by(role=UserRole.ADMIN, is_active=True).count()

        # Instrument statistics
        total_instruments = Instrument.query.count()
        active_instruments = Instrument.query.filter_by(is_active=True).count()
        inactive_instruments = total_instruments - active_instruments

        # Get instruments by asset class
        instruments_by_class = db.session.query(
            Instrument.asset_class,
            func.count(Instrument.id).label('count')
        ).group_by(Instrument.asset_class).all()

        # Tag statistics
        total_tags = Tag.query.filter_by(is_default=True).count()
        active_tags = Tag.query.filter_by(is_default=True, is_active=True).count()
        inactive_tags = total_tags - active_tags

        # Get tags by category
        tags_by_category = db.session.query(
            Tag.category,
            func.count(Tag.id).label('count')
        ).filter_by(is_default=True).group_by(Tag.category).all()

        # Trading Model statistics
        default_models_count = TradingModel.query.filter_by(is_default=True).count()
        configured_roles_count = DiscordRolePermission.query.count()

        # ===== NEW SYSTEM HEALTH MONITORING =====

        # Get comprehensive system health status
        system_health = get_system_health()

        # Format system health for template display
        formatted_health = {}
        for component_name, component_data in system_health.get('components', {}).items():
            formatted_health[component_name] = {
                'data': component_data,
                'display': format_status_display(component_name, component_data)
            }

        # Get P12 scenario count (real-time)
        p12_active_count = P12Scenario.query.filter_by(is_active=True).count()
        p12_total_count = P12Scenario.query.count()

        # System version info (you can make this dynamic)
        system_info = {
            'version': 'v2.1.0',
            'environment': current_app.config.get('ENVIRONMENT', 'Production'),
            'last_updated': current_timestamp.strftime('%b %d, %Y'),
            'uptime_hours': system_health.get('components', {}).get('application', {}).get('uptime_hours', 'N/A')
        }

        # Resource utilization from system health
        resources = system_health.get('resources', {})

        current_app.logger.info(f"Admin dashboard accessed by {current_user.username}")

    except Exception as e:
        current_app.logger.error(f"Error fetching admin dashboard stats: {e}", exc_info=True)
        flash("Could not load all dashboard statistics.", "warning")

        # Fallback values
        total_users = active_users_count = admin_users_count = 0
        total_instruments = active_instruments = inactive_instruments = 0
        instruments_by_class = []
        total_tags = active_tags = inactive_tags = 0
        tags_by_category = []
        default_models_count = 0
        p12_active_count = p12_total_count = 0

        # Fallback system health
        system_health = {
            'overall_status': 'unknown',
            'components': {},
            'resources': {
                'instruments': {'active': 0, 'total': 0, 'percentage': 0},
                'tags': {'active': 0, 'total': 0, 'percentage': 0},
                'users': {'current': 0, 'capacity': 100, 'percentage': 0}
            }
        }
        formatted_health = {}
        system_info = {
            'version': 'v2.1.0',
            'environment': 'Production',
            'last_updated': 'Today',
            'uptime_hours': 'N/A'
        }
        resources = system_health['resources']

    return render_template('admin/dashboard.html',
                           title='Administration Center',
                           # Existing stats
                           total_users=total_users,
                           active_users_count=active_users_count,
                           admin_users_count=admin_users_count,
                           total_instruments=total_instruments,
                           active_instruments=active_instruments,
                           inactive_instruments=inactive_instruments,
                           instruments_by_class=instruments_by_class,
                           total_tags=total_tags,
                           active_tags=active_tags,
                           inactive_tags=inactive_tags,
                           tags_by_category=tags_by_category,
                           default_models_count=default_models_count,
                           current_timestamp=current_timestamp,
                           configured_roles_count=configured_roles_count,
                           # New system health data
                           system_health=system_health,
                           formatted_health=formatted_health,
                           system_info=system_info,
                           resources=resources,
                           p12_active_count=p12_active_count,
                           p12_total_count=p12_total_count)


# ===== NEW API ENDPOINT FOR REAL-TIME UPDATES =====

@admin_bp.route('/api/system-health')
@login_required
@admin_required
def api_system_health():
    """API endpoint for real-time system health updates (AJAX)."""
    try:
        # Try to import system health monitoring
        try:
            from app.utils.system_health import get_system_health, format_status_display
            system_health_available = True
        except ImportError:
            system_health_available = False

        if system_health_available:
            # Get fresh system health data
            system_health = get_system_health()

            # Format for JSON response
            response_data = {
                'success': True,
                'overall_status': system_health.get('overall_status'),
                'components': {},
                'resources': system_health.get('resources', {}),
                'metrics': system_health.get('metrics', {}),
                'last_updated': system_health.get('last_updated'),
                'timestamp': datetime.utcnow().isoformat()
            }

            # Format component data for frontend
            for component_name, component_data in system_health.get('components', {}).items():
                display_info = format_status_display(component_name, component_data)
                response_data['components'][component_name] = {
                    'status': component_data.get('status'),
                    'details': component_data.get('details'),
                    'display_class': display_info['class'],
                    'display_label': display_info['label'],
                    'display_icon': display_info['icon'],
                    'raw_data': component_data
                }
        else:
            # Fallback response without advanced monitoring
            p12_active_count = P12Scenario.query.filter_by(is_active=True).count()

            response_data = {
                'success': True,
                'overall_status': 'operational',
                'components': {
                    'application': {
                        'status': 'operational',
                        'details': 'Application running',
                        'display_class': 'status-operational',
                        'display_label': 'Operational',
                        'display_icon': 'fas fa-check-circle'
                    },
                    'database': {
                        'status': 'operational',
                        'details': 'Connected',
                        'display_class': 'status-operational',
                        'display_label': 'Operational',
                        'display_icon': 'fas fa-check-circle'
                    },
                    'p12_engine': {
                        'status': 'operational',
                        'details': f'{p12_active_count} Scenarios Active',
                        'display_class': 'status-operational',
                        'display_label': 'Operational',
                        'display_icon': 'fas fa-check-circle'
                    },
                    'analytics_engine': {
                        'status': 'maintenance',
                        'details': 'Scheduled Deployment',
                        'display_class': 'status-maintenance',
                        'display_label': 'Maintenance',
                        'display_icon': 'fas fa-tools'
                    }
                },
                'resources': {},
                'metrics': {},
                'timestamp': datetime.utcnow().isoformat()
            }

        # Add P12 engine real-time data
        p12_active_count = P12Scenario.query.filter_by(is_active=True).count()
        response_data['p12_scenarios'] = {
            'active_count': p12_active_count,
            'display_text': f'{p12_active_count} Scenarios Active'
        }

        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Error fetching system health API: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'overall_status': 'error'
        }), 500


@admin_bp.route('/api/system-metrics')
@login_required
@admin_required
def api_system_metrics():
    """API endpoint for detailed system metrics (for monitoring dashboards)."""
    try:
        from app.utils.system_health import get_system_health

        system_health = get_system_health()

        # Extract detailed metrics
        metrics = system_health.get('metrics', {})
        resources = system_health.get('resources', {})

        # Add database performance metrics
        db_component = system_health.get('components', {}).get('database', {})

        response = {
            'success': True,
            'performance': {
                'cpu_usage': metrics.get('cpu_usage_percent'),
                'memory_usage': metrics.get('memory_usage_percent'),
                'disk_usage': metrics.get('disk_usage_percent'),
                'database_response_time': db_component.get('response_time_ms')
            },
            'capacity': {
                'instruments_utilization': resources.get('instruments', {}).get('percentage', 0),
                'tags_utilization': resources.get('tags', {}).get('percentage', 0),
                'users_utilization': resources.get('users', {}).get('percentage', 0)
            },
            'database': {
                'connection_pool_size': db_component.get('connection_pool_size'),
                'active_connections': db_component.get('checked_out_connections'),
                'available_connections': db_component.get('checked_in_connections')
            },
            'timestamp': datetime.utcnow().isoformat()
        }

        return jsonify(response)

    except Exception as e:
        current_app.logger.error(f"Error fetching system metrics API: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/debug/routes')
@login_required
@admin_required
def debug_routes():
    routes = []
    for rule in current_app.url_map.iter_rules():
        if 'bulk' in rule.rule:
            routes.append(f"{rule.rule} - Methods: {list(rule.methods)}")
    return f"<pre>{'<br>'.join(routes)}</pre>"

@admin_bp.route('/users/test_bulk', methods=['POST'])
@login_required
@admin_required
def test_bulk():
    return jsonify({'status': 'success', 'message': 'Test route working!'})


@admin_bp.route('/debug/check-routes')
@login_required
@admin_required
def debug_check_routes():
    """Debug endpoint to check if bulk routes are registered."""
    from flask import current_app

    routes_info = []
    for rule in current_app.url_map.iter_rules():
        if 'bulk' in rule.rule:
            routes_info.append({
                'rule': rule.rule,
                'methods': list(rule.methods),
                'endpoint': rule.endpoint
            })

    return jsonify({
        'status': 'success',
        'message': 'Route check completed',
        'bulk_routes': routes_info,
        'total_routes': len(list(current_app.url_map.iter_rules()))
    })


# SIMPLE TEST ROUTE - to verify basic POST requests work
@admin_bp.route('/users/test-post', methods=['POST'])
@login_required
@admin_required
def test_post_route():
    """Simple test route to verify POST requests work."""
    try:
        data = request.get_json()
        return jsonify({
            'status': 'success',
            'message': 'Test POST route working!',
            'received_data': data,
            'user': current_user.username
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Test route error: {str(e)}'
        }), 500


# ============================================================================
# ENTERPRISE-LEVEL ADMIN EXPORT FUNCTIONALITY
# ============================================================================

@admin_bp.route('/export_system_report', methods=['GET'])
@login_required
@admin_required
def export_system_report():
    """Export comprehensive system performance report."""
    import csv
    import io
    from datetime import datetime, timedelta
    from flask import Response
    
    try:
        # Get system-wide statistics
        total_users = User.query.count()
        active_users = User.query.filter(User.last_login_date >= datetime.now() - timedelta(days=30)).count()
        total_instruments = Instrument.query.count()
        total_tags = Tag.query.count()
        total_models = TradingModel.query.count()
        total_scenarios = P12Scenario.query.count()
        
        # Get recent activity
        recent_activities = Activity.query.order_by(Activity.timestamp.desc()).limit(100).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # System Report Header
        writer.writerow(['ENTERPRISE TRADING SYSTEM PERFORMANCE REPORT'])
        writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([f'Administrator: {current_user.username}'])
        writer.writerow([])
        
        # System Statistics
        writer.writerow(['SYSTEM STATISTICS'])
        writer.writerow(['Total Users', total_users])
        writer.writerow(['Active Users (30 days)', active_users])
        writer.writerow(['Total Instruments', total_instruments])
        writer.writerow(['Total Tags', total_tags])
        writer.writerow(['Total Trading Models', total_models])
        writer.writerow(['Total P12 Scenarios', total_scenarios])
        writer.writerow(['User Activity Rate', f'{(active_users/total_users*100):.1f}%' if total_users > 0 else '0%'])
        writer.writerow([])
        
        # Recent System Activity
        writer.writerow(['RECENT SYSTEM ACTIVITY'])
        writer.writerow(['Timestamp', 'User', 'Action', 'Details'])
        for activity in recent_activities:
            writer.writerow([
                activity.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                activity.user.username if activity.user else 'System',
                activity.activity_type,
                activity.description[:100] + '...' if len(activity.description) > 100 else activity.description
            ])
        
        output.seek(0)
        filename = f"system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(output, mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment;filename={filename}"})

    except Exception as e:
        flash(f'Error generating system report: {str(e)}', 'danger')
        return redirect(url_for('admin_bp.show_admin_dashboard'))


@admin_bp.route('/export_user_activity', methods=['GET'])
@login_required
@admin_required
def export_user_activity():
    """Export detailed user activity report."""
    import csv
    import io
    from datetime import datetime, timedelta
    from flask import Response
    
    try:
        # Get user activity data
        users = User.query.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # User Activity Report Header
        writer.writerow(['USER ACTIVITY ANALYSIS REPORT'])
        writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([f'Administrator: {current_user.username}'])
        writer.writerow([])
        
        # User Activity Summary
        writer.writerow(['USER ACTIVITY SUMMARY'])
        writer.writerow(['Username', 'Role', 'Created Date', 'Last Login', 'Login Count', 'Status'])
        
        for user in users:
            last_login = user.last_login_date.strftime('%Y-%m-%d %H:%M:%S') if user.last_login_date else 'Never'
            status = 'Active' if user.last_login_date and user.last_login_date >= datetime.now() - timedelta(days=30) else 'Inactive'
            
            writer.writerow([
                user.username,
                user.role.value,
                user.created_date.strftime('%Y-%m-%d'),
                last_login,
                user.login_count or 0,
                status
            ])
        
        output.seek(0)
        filename = f"user_activity_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(output, mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment;filename={filename}"})

    except Exception as e:
        flash(f'Error generating user activity report: {str(e)}', 'danger')
        return redirect(url_for('admin_bp.show_admin_dashboard'))


@admin_bp.route('/export_audit_log', methods=['GET'])
@login_required
@admin_required
def export_audit_log():
    """Export comprehensive system audit log."""
    import csv
    import io
    from datetime import datetime, timedelta
    from flask import Response
    
    try:
        # Get audit trail data (last 90 days)
        cutoff_date = datetime.now() - timedelta(days=90)
        activities = Activity.query.filter(
            Activity.timestamp >= cutoff_date
        ).order_by(Activity.timestamp.desc()).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Audit Log Header
        writer.writerow(['SYSTEM AUDIT LOG'])
        writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([f'Administrator: {current_user.username}'])
        writer.writerow([f'Period: Last 90 days'])
        writer.writerow([])
        
        # Audit Log Entries
        writer.writerow(['Timestamp', 'User ID', 'Username', 'Activity Type', 'Description', 'IP Address'])
        
        for activity in activities:
            writer.writerow([
                activity.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                activity.user_id or 'System',
                activity.user.username if activity.user else 'System',
                activity.activity_type,
                activity.description,
                getattr(activity, 'ip_address', 'N/A')  # In case IP tracking isn't implemented
            ])
        
        output.seek(0)
        filename = f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(output, mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment;filename={filename}"})

    except Exception as e:
        flash(f'Error generating audit log: {str(e)}', 'danger')
        return redirect(url_for('admin_bp.show_admin_dashboard'))


@admin_bp.route('/backup_system_data', methods=['GET'])
@login_required
@admin_required  
def backup_system_data():
    """Create comprehensive system backup."""
    import json
    import io
    from datetime import datetime
    from flask import Response
    
    try:
        # Create comprehensive data backup
        backup_data = {
            'backup_metadata': {
                'created_by': current_user.username,
                'created_at': datetime.now().isoformat(),
                'system_version': getattr(current_app, 'version', '1.0.0'),
                'backup_type': 'full_system'
            },
            'users': [],
            'instruments': [],
            'tags': [],
            'trading_models': [],
            'p12_scenarios': []
        }
        
        # Backup Users (excluding sensitive data)
        users = User.query.all()
        for user in users:
            backup_data['users'].append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role.value,
                'created_date': user.created_date.isoformat(),
                'last_login_date': user.last_login_date.isoformat() if user.last_login_date else None,
                'is_active': True  # Simplified status
            })
        
        # Backup Instruments
        instruments = Instrument.query.all()
        for instrument in instruments:
            backup_data['instruments'].append({
                'id': instrument.id,
                'symbol': instrument.symbol,
                'name': instrument.name,
                'point_value': float(instrument.point_value) if instrument.point_value else None,
                'created_date': instrument.created_date.isoformat() if hasattr(instrument, 'created_date') else None
            })
        
        # Backup Tags
        tags = Tag.query.all()
        for tag in tags:
            backup_data['tags'].append({
                'id': tag.id,
                'name': tag.name,
                'category': tag.category.value if tag.category else None,
                'is_default': tag.is_default,
                'user_id': tag.user_id
            })
        
        # Backup Trading Models
        models = TradingModel.query.all()
        for model in models:
            backup_data['trading_models'].append({
                'id': model.id,
                'name': model.name,
                'description': model.description,
                'is_default': model.is_default,
                'user_id': model.user_id
            })
        
        # Backup P12 Scenarios
        scenarios = P12Scenario.query.all()
        for scenario in scenarios:
            backup_data['p12_scenarios'].append({
                'id': scenario.id,
                'scenario_number': scenario.scenario_number,
                'scenario_name': scenario.scenario_name,
                'short_description': scenario.short_description,
                'is_active': scenario.is_active
            })
        
        json_str = json.dumps(backup_data, indent=2, default=str)
        filename = f"system_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return Response(json_str, mimetype="application/json",
                        headers={"Content-Disposition": f"attachment;filename={filename}"})

    except Exception as e:
        flash(f'Error creating system backup: {str(e)}', 'danger')
        return redirect(url_for('admin_bp.show_admin_dashboard'))


# =============================================================================
# BACKTESTING ROUTES FOR DEFAULT MODELS
# =============================================================================

@admin_bp.route('/default-models/backtest')
@login_required
@admin_required
def manage_default_model_backtests():
    """Admin page to manage all default model backtests"""
    # Get filter parameters
    filter_form = BacktestFilterForm()
    
    # Populate trading model choices with default models only
    default_models = TradingModel.query.filter_by(is_default=True).all()
    filter_form.trading_model_id.choices = [('', 'All Models')] + [(m.id, m.name) for m in default_models]
    
    # Build query for default model backtests only
    query = Backtest.query.join(TradingModel).filter(TradingModel.is_default == True)
    
    # Apply filters
    if request.args.get('search'):
        search_term = f"%{request.args.get('search')}%"
        query = query.filter(db.or_(
            Backtest.name.ilike(search_term),
            Backtest.description.ilike(search_term)
        ))
    
    if request.args.get('trading_model_id'):
        query = query.filter(Backtest.trading_model_id == request.args.get('trading_model_id'))
    
    if request.args.get('status'):
        query = query.filter(Backtest.status == request.args.get('status'))
    
    if request.args.get('start_date'):
        query = query.filter(Backtest.start_date >= datetime.strptime(request.args.get('start_date'), '%Y-%m-%d').date())
    
    if request.args.get('end_date'):
        query = query.filter(Backtest.end_date <= datetime.strptime(request.args.get('end_date'), '%Y-%m-%d').date())
    
    # Order and paginate
    backtests = query.order_by(Backtest.created_at.desc()).all()
    
    return render_template('admin/manage_default_model_backtests.html',
                           title='Default Model Backtesting',
                           backtests=backtests,
                           filter_form=filter_form)


@admin_bp.route('/default-models/<int:model_id>/backtests')
@login_required  
@admin_required
def view_model_backtests(model_id):
    """View all backtests for a specific default trading model"""
    model = TradingModel.query.get_or_404(model_id)
    if not model.is_default:
        flash('This is not a default model.', 'warning')
        return redirect(url_for('admin.manage_default_trading_models'))
    
    backtests = Backtest.query.filter_by(trading_model_id=model_id).order_by(Backtest.created_at.desc()).all()
    
    return render_template('admin/view_model_backtests.html',
                           title=f'Backtests for {model.name}',
                           model=model,
                           backtests=backtests)


@admin_bp.route('/default-models/<int:model_id>/backtests/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_default_model_backtest(model_id):
    """Create a new backtest for a default trading model"""
    model = TradingModel.query.get_or_404(model_id)
    if not model.is_default:
        flash('This is not a default model.', 'warning')
        return redirect(url_for('admin.manage_default_trading_models'))
    
    form = BacktestForm()
    
    # Set the trading model (pre-selected and hidden)
    form.trading_model_id.choices = [(model.id, model.name)]
    form.trading_model_id.data = model.id
    
    if form.validate_on_submit():
        # Determine status - use form data or default to DRAFT
        status_value = form.status.data if form.status.data else 'DRAFT'
        status_enum = BacktestStatus[status_value]  # Convert string to enum using name lookup
        
        backtest = Backtest(
            name=form.name.data,
            description=form.description.data,
            trading_model_id=model.id,
            user_id=current_user.id,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            market_conditions=form.market_conditions.data,
            session_context=form.session_context.data,
            specific_rules_used=form.specific_rules_used.data,
            entry_rules=form.entry_rules.data,
            exit_rules=form.exit_rules.data,
            trade_management_applied=form.trade_management_applied.data,
            risk_settings=form.risk_settings.data,
            tradingview_screenshot_links=form.tradingview_screenshot_links.data,
            chart_screenshots=form.chart_screenshots.data,
            notes=form.notes.data,
            status=status_enum
        )
        
        try:
            db.session.add(backtest)
            db.session.commit()
            flash(f'Backtest "{backtest.name}" created successfully!', 'success')
            return redirect(url_for('admin.view_backtest', backtest_id=backtest.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating backtest: {str(e)}', 'danger')
    
    return render_template('admin/create_default_model_backtest.html',
                           title=f'Create Backtest for {model.name}',
                           form=form,
                           model=model)


@admin_bp.route('/backtests/<int:backtest_id>')
@login_required
@admin_required
def view_backtest(backtest_id):
    """View a specific backtest with all its trades and analytics"""
    backtest = Backtest.query.get_or_404(backtest_id)
    
    # Verify it's a default model backtest
    if not backtest.trading_model.is_default:
        flash('Access denied: This is not a default model backtest.', 'warning')
        return redirect(url_for('admin.manage_default_model_backtests'))
    
    # Get all trades for this backtest
    trades = BacktestTrade.query.filter_by(backtest_id=backtest_id).order_by(BacktestTrade.trade_date, BacktestTrade.trade_time).all()
    
    # Calculate performance metrics if not up to date
    backtest.calculate_performance_metrics()
    db.session.commit()
    
    return render_template('admin/view_backtest.html',
                           title=f'Backtest: {backtest.name}',
                           backtest=backtest,
                           trades=trades)


@admin_bp.route('/backtests/<int:backtest_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_backtest(backtest_id):
    """Edit a backtest"""
    backtest = Backtest.query.get_or_404(backtest_id)
    
    # Verify it's a default model backtest
    if not backtest.trading_model.is_default:
        flash('Access denied: This is not a default model backtest.', 'warning')
        return redirect(url_for('admin.manage_default_model_backtests'))
    
    form = BacktestForm(obj=backtest)
    
    # Set trading model choices
    form.trading_model_id.choices = [(backtest.trading_model.id, backtest.trading_model.name)]
    
    if form.validate_on_submit():
        form.populate_obj(backtest)
        
        try:
            db.session.commit()
            flash(f'Backtest "{backtest.name}" updated successfully!', 'success')
            return redirect(url_for('admin.view_backtest', backtest_id=backtest.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating backtest: {str(e)}', 'danger')
    
    return render_template('admin/edit_backtest.html',
                           title=f'Edit Backtest: {backtest.name}',
                           form=form,
                           backtest=backtest)


@admin_bp.route('/backtests/<int:backtest_id>/trades/add', methods=['GET', 'POST'])
@login_required
@admin_required  
def add_backtest_trade(backtest_id):
    """Add a new trade to a backtest"""
    backtest = Backtest.query.get_or_404(backtest_id)
    
    # Verify it's a default model backtest
    if not backtest.trading_model.is_default:
        flash('Access denied: This is not a default model backtest.', 'warning')
        return redirect(url_for('admin.manage_default_model_backtests'))
    
    form = BacktestTradeForm()
    
    if form.validate_on_submit():
        trade = BacktestTrade(
            backtest_id=backtest_id,
            trade_date=form.trade_date.data,
            trade_time=form.trade_time.data,
            instrument=form.instrument.data,
            direction=form.direction.data,
            quantity=form.quantity.data,
            entry_price=form.entry_price.data,
            exit_price=form.exit_price.data,
            stop_loss_price=form.stop_loss_price.data,
            take_profit_price=form.take_profit_price.data,
            profit_loss=form.profit_loss.data,
            profit_loss_ticks=form.profit_loss_ticks.data,
            mae_ticks=form.mae_ticks.data,
            mfe_ticks=form.mfe_ticks.data,
            duration_minutes=form.duration_minutes.data,
            actual_exit_reason=form.actual_exit_reason.data,
            exit_time=form.exit_time.data,
            market_conditions=form.market_conditions.data,
            session_context=form.session_context.data,
            notes=form.notes.data,
            tags=form.tags.data,
            tradingview_screenshot_links=form.tradingview_screenshot_links.data,
            chart_screenshots=form.chart_screenshots.data
        )
        
        try:
            db.session.add(trade)
            db.session.commit()
            
            # Recalculate backtest performance metrics
            backtest.calculate_performance_metrics()
            db.session.commit()
            
            flash('Trade added successfully!', 'success')
            return redirect(url_for('admin.view_backtest', backtest_id=backtest_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding trade: {str(e)}', 'danger')
    
    return render_template('admin/add_backtest_trade.html',
                           title=f'Add Trade to {backtest.name}',
                           form=form,
                           backtest=backtest)


@admin_bp.route('/backtests/<int:backtest_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_backtest(backtest_id):
    """Delete a backtest and all its trades"""
    backtest = Backtest.query.get_or_404(backtest_id)
    
    # Verify it's a default model backtest
    if not backtest.trading_model.is_default:
        flash('Access denied: This is not a default model backtest.', 'warning')
        return redirect(url_for('admin.manage_default_model_backtests'))
    
    try:
        backtest_name = backtest.name
        db.session.delete(backtest)  # Cascade will delete all trades
        db.session.commit()
        
        flash(f'Backtest "{backtest_name}" and all its trades have been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting backtest: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_default_model_backtests'))


@admin_bp.route('/backtests/<int:backtest_id>/trades/<int:trade_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_backtest_trade(backtest_id, trade_id):
    """Delete a specific trade from a backtest"""
    backtest = Backtest.query.get_or_404(backtest_id)
    trade = BacktestTrade.query.get_or_404(trade_id)
    
    # Verify it's a default model backtest
    if not backtest.trading_model.is_default:
        flash('Access denied: This is not a default model backtest.', 'warning')
        return redirect(url_for('admin.manage_default_model_backtests'))
    
    # Verify trade belongs to this backtest
    if trade.backtest_id != backtest_id:
        flash('Invalid trade for this backtest.', 'danger')
        return redirect(url_for('admin.view_backtest', backtest_id=backtest_id))
    
    try:
        db.session.delete(trade)  # Cascade will delete entries/exits
        db.session.commit()
        
        # Recalculate backtest performance metrics
        backtest.calculate_performance_metrics()
        db.session.commit()
        
        flash('Trade deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting trade: {str(e)}', 'danger')
    
    return redirect(url_for('admin.view_backtest', backtest_id=backtest_id))
