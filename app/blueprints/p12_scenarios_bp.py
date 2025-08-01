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
from app.utils.image_manager import ImageManager
from app.models import GlobalImage



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

    print(f"=== SAVE_SCENARIO_IMAGE DEBUG ===")
    print(f"File received: {file}")
    print(f"File filename: {file.filename}")
    print(f"File allowed check: {allowed_file(file.filename)}")
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

    # Get main P12 overview image
    main_image = GlobalImage.query.filter_by(
        entity_type='p12_overview',
        entity_id=1
    ).first()

    print("=== LIST SCENARIOS DEBUG ===")
    print("Scenarios found:", len(scenarios))
    print("Main image found:", main_image.id if main_image else None)
    print("============================")

    return render_template('admin/p12_scenarios/list_scenarios.html',
                           scenarios=scenarios,
                           main_image=main_image,
                           title="Manage P12 Scenarios")


@p12_scenarios_bp.route('/export-pdf', methods=['POST'])
@login_required
@admin_required
def export_scenarios_pdf():
    """Export P12 scenarios to comprehensive PDF with detailed information."""
    print("=== COMPREHENSIVE PDF EXPORT ROUTE CALLED ===")
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
            PageBreak, KeepTogether, Image
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from io import BytesIO
        
        # Get scenarios
        scenarios = P12Scenario.query.order_by(P12Scenario.scenario_number).all()
        print(f"Exporting {len(scenarios)} scenarios to detailed PDF")
        
        # Create PDF buffer
        buffer = BytesIO()
        
        # Create PDF document with margins
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=1*inch
        )
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center
            textColor=colors.darkblue
        )
        
        scenario_title_style = ParagraphStyle(
            'ScenarioTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=20,
            textColor=colors.darkred,
            borderWidth=2,
            borderColor=colors.darkred,
            borderPadding=10
        )
        
        section_header_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.darkblue,
            borderWidth=1,
            borderColor=colors.lightgrey,
            borderPadding=5
        )
        
        content_style = ParagraphStyle(
            'Content',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=8,
            leftIndent=10
        )
        
        # Add main title page
        main_title = Paragraph("P12 Strategic Frameworks", title_style)
        story.append(main_title)
        story.append(Spacer(1, 30))
        
        subtitle = Paragraph("Comprehensive Trading Methodology Guide", styles['Heading2'])
        story.append(subtitle)
        story.append(Spacer(1, 20))
        
        # Add overview
        overview_text = f"""
        This document contains detailed information about {len(scenarios)} P12 Strategic Framework scenarios 
        based on Random's (Matt Mickey) trading methodology. Each scenario covers the critical 
        12-hour period (06:00-18:00 EST) and provides comprehensive guidance for market analysis and trading decisions.
        """
        overview = Paragraph(overview_text, styles['Normal'])
        story.append(overview)
        story.append(Spacer(1, 20))
        
        # Add generation info
        gen_info = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Italic'])
        story.append(gen_info)
        
        # Table of Contents
        story.append(PageBreak())
        toc_title = Paragraph("Table of Contents", styles['Heading1'])
        story.append(toc_title)
        story.append(Spacer(1, 20))
        
        if scenarios:
            for scenario in scenarios:
                toc_entry = Paragraph(
                    f"Scenario {scenario.scenario_number}: {scenario.scenario_name}", 
                    styles['Normal']
                )
                story.append(toc_entry)
                story.append(Spacer(1, 5))
        
        # Add each scenario on its own page
        for i, scenario in enumerate(scenarios):
            story.append(PageBreak())
            
            # Scenario header
            scenario_header = Paragraph(
                f"Scenario {scenario.scenario_number}: {scenario.scenario_name}",
                scenario_title_style
            )
            story.append(scenario_header)
            story.append(Spacer(1, 20))
            
            # Add scenario image if available
            images = GlobalImage.get_for_entity('p12_scenario', scenario.id)
            if images:
                try:
                    # Get image file path using GlobalImage's full_disk_path property
                    image_path = images[0].full_disk_path
                    
                    if image_path and os.path.exists(image_path):
                        # Add image to PDF
                        img = Image(image_path, width=4*inch, height=3*inch, kind='proportional')
                        story.append(img)
                        story.append(Spacer(1, 10))
                        
                        # Add image caption
                        caption = Paragraph(f"Strategic Framework Analysis - {scenario.scenario_name}", styles['Italic'])
                        story.append(caption)
                        story.append(Spacer(1, 15))
                except Exception as e:
                    print(f"Error adding image for scenario {scenario.scenario_number}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Basic Information Section
            basic_info_items = []
            
            # Short Description
            if scenario.short_description:
                basic_info_items.append(['Short Description:', scenario.short_description])
            
            # Directional Bias
            if scenario.directional_bias:
                basic_info_items.append(['Directional Bias:', scenario.directional_bias.title()])
            
            # Status
            status = 'Active' if scenario.is_active else 'Inactive'
            basic_info_items.append(['Status:', status])
            
            # Risk Percentage
            if scenario.risk_percentage:
                basic_info_items.append(['Risk Percentage:', f"{scenario.risk_percentage}%"])
            
            if basic_info_items:
                basic_info_table = Table(basic_info_items, colWidths=[1.5*inch, 4*inch])
                basic_info_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                story.append(basic_info_table)
                story.append(Spacer(1, 15))
            
            # Detailed sections
            sections = [
                ("Detailed Description", scenario.detailed_description),
                ("HOD/LOD Implications", scenario.hod_lod_implication),
                ("Alert Criteria", scenario.alert_criteria),
                ("Confirmation Criteria", scenario.confirmation_criteria),
                ("Entry Strategy", scenario.entry_strategy),
                ("Typical Targets", scenario.typical_targets),
                ("Stop Loss Guidance", scenario.stop_loss_guidance),
                ("Risk Guidance", scenario.risk_guidance),
                ("Key Considerations", scenario.key_considerations),
            ]
            
            for section_title, section_content in sections:
                if section_content and section_content.strip():
                    # Section header
                    section_header = Paragraph(section_title, section_header_style)
                    story.append(section_header)
                    
                    # Section content
                    content = Paragraph(section_content, content_style)
                    story.append(content)
                    story.append(Spacer(1, 10))
            
            # Trading Models section
            if scenario.models_to_activate or scenario.models_to_avoid:
                models_header = Paragraph("Trading Model Recommendations", section_header_style)
                story.append(models_header)
                
                if scenario.models_to_activate:
                    activate_text = "Models to Activate: " + ", ".join(scenario.models_to_activate)
                    activate_para = Paragraph(activate_text, content_style)
                    story.append(activate_para)
                
                if scenario.models_to_avoid:
                    avoid_text = "Models to Avoid: " + ", ".join(scenario.models_to_avoid)
                    avoid_para = Paragraph(avoid_text, content_style)
                    story.append(avoid_para)
                
                story.append(Spacer(1, 10))
            
            # Preferred Timeframes
            if scenario.preferred_timeframes:
                timeframes_header = Paragraph("Preferred Timeframes", section_header_style)
                story.append(timeframes_header)
                
                timeframes_text = ", ".join(scenario.preferred_timeframes)
                timeframes_para = Paragraph(timeframes_text, content_style)
                story.append(timeframes_para)
                story.append(Spacer(1, 10))
            
            # Usage statistics and operational metrics
            usage_header = Paragraph("Operational Metrics & Usage Statistics", section_header_style)
            story.append(usage_header)
            
            usage_items = []
            usage_items.append(['Usage Count:', f"{scenario.times_selected or 0} selections"])
            usage_items.append(['Operational Status:', 'Active' if scenario.is_active else 'Inactive'])
            usage_items.append(['Risk Percentage:', f"{scenario.risk_percentage}%" if scenario.risk_percentage else 'Not specified'])
            usage_items.append(['Directional Bias:', scenario.directional_bias.title() if scenario.directional_bias else 'Neutral'])
            
            from reportlab.platypus import Table, TableStyle
            usage_table = Table(usage_items, colWidths=[1.5*inch, 3*inch])
            usage_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(usage_table)
            story.append(Spacer(1, 10))
            
            # Metadata footer for each scenario
            story.append(Spacer(1, 20))
            metadata_text = f"Created: {scenario.created_date.strftime('%Y-%m-%d')} | Last Updated: {scenario.updated_date.strftime('%Y-%m-%d')}"
            metadata_para = Paragraph(metadata_text, styles['Italic'])
            story.append(metadata_para)
        
        else:
            story.append(Paragraph("No P12 scenarios configured.", styles['Normal']))
        
        print("Building comprehensive PDF...")
        doc.build(story)
        buffer.seek(0)
        
        print("Sending detailed PDF file...")
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'P12_Strategic_Frameworks_Detailed_{datetime.now().strftime("%Y%m%d")}.pdf',
            mimetype='application/pdf'
        )
        
    except ImportError as e:
        error_msg = f"ReportLab not installed for PDF generation: {e}"
        print(f"ImportError: {error_msg}")
        current_app.logger.error(error_msg)
        return jsonify({'success': False, 'error': 'PDF generation not available'}), 500
    except Exception as e:
        error_msg = f"Error generating PDF: {e}"
        print(f"Exception: {error_msg}")
        import traceback
        traceback.print_exc()
        current_app.logger.error(error_msg)
        return jsonify({'success': False, 'error': 'PDF generation failed'}), 500


@p12_scenarios_bp.route('/export-csv', methods=['POST'])
@login_required
@admin_required
def export_scenarios_csv():
    """Export P12 scenarios to CSV with all scenario data."""
    import csv
    import io
    from flask import Response
    
    try:
        # Get all scenarios ordered by scenario number
        scenarios = P12Scenario.query.order_by(P12Scenario.scenario_number).all()
        
        # Create CSV buffer
        output = io.StringIO()
        
        # Define CSV columns (same as template)
        fieldnames = [
            'scenario_number',
            'scenario_name', 
            'short_description',
            'detailed_description',
            'hod_lod_implication',
            'directional_bias',
            'alert_criteria',
            'confirmation_criteria',
            'entry_strategy',
            'typical_targets',
            'stop_loss_guidance',
            'risk_percentage',
            'is_active',
            'models_to_activate',
            'models_to_avoid',
            'risk_guidance',
            'preferred_timeframes',
            'key_considerations',
            'times_selected',
            'created_date',
            'updated_date'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Export each scenario
        for scenario in scenarios:
            # Handle list fields by joining with semicolons
            models_to_activate = ';'.join(scenario.models_to_activate) if scenario.models_to_activate else ''
            models_to_avoid = ';'.join(scenario.models_to_avoid) if scenario.models_to_avoid else ''
            preferred_timeframes = ';'.join(scenario.preferred_timeframes) if scenario.preferred_timeframes else ''
            
            row_data = {
                'scenario_number': scenario.scenario_number,
                'scenario_name': scenario.scenario_name or '',
                'short_description': scenario.short_description or '',
                'detailed_description': scenario.detailed_description or '',
                'hod_lod_implication': scenario.hod_lod_implication or '',
                'directional_bias': scenario.directional_bias or '',
                'alert_criteria': scenario.alert_criteria or '',
                'confirmation_criteria': scenario.confirmation_criteria or '',
                'entry_strategy': scenario.entry_strategy or '',
                'typical_targets': scenario.typical_targets or '',
                'stop_loss_guidance': scenario.stop_loss_guidance or '',
                'risk_percentage': scenario.risk_percentage or '',
                'is_active': 'true' if scenario.is_active else 'false',
                'models_to_activate': models_to_activate,
                'models_to_avoid': models_to_avoid,
                'risk_guidance': scenario.risk_guidance or '',
                'preferred_timeframes': preferred_timeframes,
                'key_considerations': scenario.key_considerations or '',
                'times_selected': scenario.times_selected or 0,
                'created_date': scenario.created_date.strftime('%Y-%m-%d %H:%M:%S') if scenario.created_date else '',
                'updated_date': scenario.updated_date.strftime('%Y-%m-%d %H:%M:%S') if scenario.updated_date else ''
            }
            
            writer.writerow(row_data)
        
        # Create response
        output.seek(0)
        filename = f"P12_Strategic_Frameworks_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exporting P12 scenarios to CSV: {e}")
        return jsonify({'success': False, 'error': 'CSV export failed'}), 500


@p12_scenarios_bp.route('/<int:scenario_id>/export-pdf', methods=['POST'])
@login_required
@admin_required
def export_single_scenario_pdf(scenario_id):
    """Export single P12 scenario to PDF with detailed information and image."""
    print(f"=== SINGLE SCENARIO PDF EXPORT ROUTE CALLED for scenario {scenario_id} ===")
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
            PageBreak, KeepTogether, Image
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from io import BytesIO
        import os
        
        # Get the specific scenario
        scenario = P12Scenario.query.get_or_404(scenario_id)
        print(f"Exporting scenario {scenario.scenario_number}: {scenario.scenario_name} to PDF")
        
        # Create PDF buffer
        buffer = BytesIO()
        
        # Create PDF document with margins
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=1*inch
        )
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center
            textColor=colors.darkblue
        )
        
        scenario_title_style = ParagraphStyle(
            'ScenarioTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=20,
            textColor=colors.darkred,
            borderWidth=2,
            borderColor=colors.darkred,
            borderPadding=10
        )
        
        section_header_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.darkblue,
            borderWidth=1,
            borderColor=colors.lightgrey,
            borderPadding=5
        )
        
        content_style = ParagraphStyle(
            'Content',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=8,
            leftIndent=10
        )
        
        # Add main title page
        main_title = Paragraph(f"P12 Strategic Framework {scenario.scenario_number}", title_style)
        story.append(main_title)
        story.append(Spacer(1, 20))
        
        subtitle = Paragraph(scenario.scenario_name, styles['Heading2'])
        story.append(subtitle)
        story.append(Spacer(1, 30))
        
        # Add scenario image if available
        images = GlobalImage.get_for_entity('p12_scenario', scenario_id)
        if images:
            try:
                # Get image file path using GlobalImage's full_disk_path property
                image_path = images[0].full_disk_path
                
                if os.path.exists(image_path):
                    # Add image to PDF
                    img = Image(image_path, width=5*inch, height=4*inch, kind='proportional')
                    story.append(img)
                    story.append(Spacer(1, 20))
                    
                    # Add image caption
                    caption = Paragraph(f"Strategic Framework Analysis - {scenario.scenario_name}", styles['Italic'])
                    story.append(caption)
                    story.append(Spacer(1, 20))
            except Exception as e:
                print(f"Error adding image to PDF: {e}")
        
        # Scenario header
        scenario_header = Paragraph(
            f"Scenario {scenario.scenario_number}: {scenario.scenario_name}",
            scenario_title_style
        )
        story.append(scenario_header)
        story.append(Spacer(1, 20))
        
        # Basic Information Section
        basic_info_items = []
        
        # Short Description
        if scenario.short_description:
            basic_info_items.append(['Short Description:', scenario.short_description])
        
        # Directional Bias
        if scenario.directional_bias:
            basic_info_items.append(['Directional Bias:', scenario.directional_bias.title()])
        
        # Status
        status = 'Active' if scenario.is_active else 'Inactive'
        basic_info_items.append(['Status:', status])
        
        # Risk Percentage
        if scenario.risk_percentage:
            basic_info_items.append(['Risk Percentage:', f"{scenario.risk_percentage}%"])
        
        if basic_info_items:
            basic_info_table = Table(basic_info_items, colWidths=[1.5*inch, 4*inch])
            basic_info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(basic_info_table)
            story.append(Spacer(1, 15))
        
        # Detailed sections
        sections = [
            ("Detailed Description", scenario.detailed_description),
            ("HOD/LOD Implications", scenario.hod_lod_implication),
            ("Alert Criteria", scenario.alert_criteria),
            ("Confirmation Criteria", scenario.confirmation_criteria),
            ("Entry Strategy", scenario.entry_strategy),
            ("Typical Targets", scenario.typical_targets),
            ("Stop Loss Guidance", scenario.stop_loss_guidance),
            ("Risk Guidance", scenario.risk_guidance),
            ("Key Considerations", scenario.key_considerations),
        ]
        
        for section_title, section_content in sections:
            if section_content and section_content.strip():
                # Section header
                section_header = Paragraph(section_title, section_header_style)
                story.append(section_header)
                
                # Section content
                content = Paragraph(section_content, content_style)
                story.append(content)
                story.append(Spacer(1, 10))
        
        # Trading Models section
        if scenario.models_to_activate or scenario.models_to_avoid:
            models_header = Paragraph("Trading Model Recommendations", section_header_style)
            story.append(models_header)
            
            if scenario.models_to_activate:
                activate_text = "Models to Activate: " + ", ".join(scenario.models_to_activate)
                activate_para = Paragraph(activate_text, content_style)
                story.append(activate_para)
            
            if scenario.models_to_avoid:
                avoid_text = "Models to Avoid: " + ", ".join(scenario.models_to_avoid)
                avoid_para = Paragraph(avoid_text, content_style)
                story.append(avoid_para)
            
            story.append(Spacer(1, 10))
        
        # Preferred Timeframes
        if scenario.preferred_timeframes:
            timeframes_header = Paragraph("Preferred Timeframes", section_header_style)
            story.append(timeframes_header)
            
            timeframes_text = ", ".join(scenario.preferred_timeframes)
            timeframes_para = Paragraph(timeframes_text, content_style)
            story.append(timeframes_para)
            story.append(Spacer(1, 10))
        
        # Usage statistics and operational metrics
        usage_header = Paragraph("Operational Metrics & Usage Statistics", section_header_style)
        story.append(usage_header)
        
        usage_items = []
        usage_items.append(['Usage Count:', f"{scenario.times_selected or 0} selections"])
        usage_items.append(['Operational Status:', 'Active' if scenario.is_active else 'Inactive'])
        usage_items.append(['Risk Percentage:', f"{scenario.risk_percentage}%" if scenario.risk_percentage else 'Not specified'])
        usage_items.append(['Directional Bias:', scenario.directional_bias.title() if scenario.directional_bias else 'Neutral'])
        
        usage_table = Table(usage_items, colWidths=[1.5*inch, 3*inch])
        usage_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(usage_table)
        story.append(Spacer(1, 10))
        
        # Metadata footer
        story.append(Spacer(1, 20))
        metadata_text = f"Created: {scenario.created_date.strftime('%Y-%m-%d')} | Last Updated: {scenario.updated_date.strftime('%Y-%m-%d')}"
        metadata_para = Paragraph(metadata_text, styles['Italic'])
        story.append(metadata_para)
        
        # Generation info
        gen_info = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Italic'])
        story.append(gen_info)
        
        print("Building single scenario PDF...")
        doc.build(story)
        buffer.seek(0)
        
        print("Sending single scenario PDF file...")
        filename = f'P12_Strategic_Framework_{scenario.scenario_number}_{scenario.scenario_name.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.pdf'
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except ImportError as e:
        error_msg = f"ReportLab not installed for PDF generation: {e}"
        print(f"ImportError: {error_msg}")
        current_app.logger.error(error_msg)
        return jsonify({'success': False, 'error': 'PDF generation not available'}), 500
    except Exception as e:
        error_msg = f"Error generating single scenario PDF: {e}"
        print(f"Exception: {error_msg}")
        import traceback
        traceback.print_exc()
        current_app.logger.error(error_msg)
        return jsonify({'success': False, 'error': 'PDF generation failed'}), 500


@p12_scenarios_bp.route('/<int:scenario_id>/export-csv', methods=['POST'])
@login_required
@admin_required
def export_single_scenario_csv(scenario_id):
    """Export single P12 scenario to CSV with all scenario data."""
    import csv
    import io
    from flask import Response
    
    try:
        # Get the specific scenario
        scenario = P12Scenario.query.get_or_404(scenario_id)
        
        # Create CSV buffer
        output = io.StringIO()
        
        # Define CSV columns (same as template)
        fieldnames = [
            'scenario_number',
            'scenario_name', 
            'short_description',
            'detailed_description',
            'hod_lod_implication',
            'directional_bias',
            'alert_criteria',
            'confirmation_criteria',
            'entry_strategy',
            'typical_targets',
            'stop_loss_guidance',
            'risk_percentage',
            'is_active',
            'models_to_activate',
            'models_to_avoid',
            'risk_guidance',
            'preferred_timeframes',
            'key_considerations',
            'times_selected',
            'created_date',
            'updated_date'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Handle list fields by joining with semicolons
        models_to_activate = ';'.join(scenario.models_to_activate) if scenario.models_to_activate else ''
        models_to_avoid = ';'.join(scenario.models_to_avoid) if scenario.models_to_avoid else ''
        preferred_timeframes = ';'.join(scenario.preferred_timeframes) if scenario.preferred_timeframes else ''
        
        row_data = {
            'scenario_number': scenario.scenario_number,
            'scenario_name': scenario.scenario_name or '',
            'short_description': scenario.short_description or '',
            'detailed_description': scenario.detailed_description or '',
            'hod_lod_implication': scenario.hod_lod_implication or '',
            'directional_bias': scenario.directional_bias or '',
            'alert_criteria': scenario.alert_criteria or '',
            'confirmation_criteria': scenario.confirmation_criteria or '',
            'entry_strategy': scenario.entry_strategy or '',
            'typical_targets': scenario.typical_targets or '',
            'stop_loss_guidance': scenario.stop_loss_guidance or '',
            'risk_percentage': scenario.risk_percentage or '',
            'is_active': 'true' if scenario.is_active else 'false',
            'models_to_activate': models_to_activate,
            'models_to_avoid': models_to_avoid,
            'risk_guidance': scenario.risk_guidance or '',
            'preferred_timeframes': preferred_timeframes,
            'key_considerations': scenario.key_considerations or '',
            'times_selected': scenario.times_selected or 0,
            'created_date': scenario.created_date.strftime('%Y-%m-%d %H:%M:%S') if scenario.created_date else '',
            'updated_date': scenario.updated_date.strftime('%Y-%m-%d %H:%M:%S') if scenario.updated_date else ''
        }
        
        writer.writerow(row_data)
        
        # Create response
        output.seek(0)
        filename = f"P12_Strategic_Framework_{scenario.scenario_number}_{scenario.scenario_name.replace(' ', '_')}_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exporting single P12 scenario to CSV: {e}")
        return jsonify({'success': False, 'error': 'CSV export failed'}), 500


@p12_scenarios_bp.route('/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_scenarios():
    """Import P12 scenarios from JSON or CSV file."""
    try:
        if 'file' not in request.files:
            flash('No file selected for import.', 'danger')
            return redirect(url_for('p12_scenarios.list_scenarios'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected for import.', 'danger')
            return redirect(url_for('p12_scenarios.list_scenarios'))
        
        overwrite_existing = request.form.get('overwrite_existing') == 'true'
        
        # Read file content
        if file.filename.endswith('.json'):
            import json
            data = json.loads(file.read().decode('utf-8'))
        elif file.filename.endswith('.csv'):
            import csv
            import io
            content = file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            data = list(reader)
        else:
            flash('Unsupported file format. Please upload JSON or CSV.', 'danger')
            return redirect(url_for('p12_scenarios.list_scenarios'))
        
        imported_count = 0
        errors = []
        
        for item in data:
            try:
                # Extract scenario data
                scenario_number = int(item.get('scenario_number', 0))
                scenario_name = item.get('scenario_name', '').strip()
                
                if not scenario_name:
                    errors.append(f"Skipping scenario {scenario_number}: Missing name")
                    continue
                
                # Check if scenario exists
                existing = P12Scenario.query.filter_by(scenario_number=scenario_number).first()
                
                if existing and not overwrite_existing:
                    errors.append(f"Skipping scenario {scenario_number}: Already exists")
                    continue
                
                if existing and overwrite_existing:
                    # Update existing scenario
                    scenario = existing
                else:
                    # Create new scenario
                    scenario = P12Scenario(scenario_number=scenario_number)
                    db.session.add(scenario)
                
                # Update scenario fields - comprehensive mapping
                scenario.scenario_name = scenario_name
                scenario.short_description = item.get('short_description', '')
                scenario.detailed_description = item.get('detailed_description', '') or item.get('description', '')
                scenario.hod_lod_implication = item.get('hod_lod_implication', '')
                scenario.directional_bias = item.get('directional_bias', '')
                scenario.alert_criteria = item.get('alert_criteria', '')
                scenario.confirmation_criteria = item.get('confirmation_criteria', '')
                scenario.entry_strategy = item.get('entry_strategy', '')
                scenario.typical_targets = item.get('typical_targets', '')
                scenario.stop_loss_guidance = item.get('stop_loss_guidance', '')
                scenario.risk_percentage = float(item.get('risk_percentage', 0)) if item.get('risk_percentage') else None
                scenario.is_active = item.get('is_active', 'true').lower() in ['true', '1', 'yes']
                scenario.risk_guidance = item.get('risk_guidance', '')
                scenario.key_considerations = item.get('key_considerations', '')
                
                # Handle list fields that may be semicolon-separated strings
                models_to_activate = item.get('models_to_activate', '')
                if models_to_activate:
                    scenario.models_to_activate = [m.strip() for m in models_to_activate.split(';') if m.strip()]
                else:
                    scenario.models_to_activate = []
                    
                models_to_avoid = item.get('models_to_avoid', '')
                if models_to_avoid:
                    scenario.models_to_avoid = [m.strip() for m in models_to_avoid.split(';') if m.strip()]
                else:
                    scenario.models_to_avoid = []
                    
                preferred_timeframes = item.get('preferred_timeframes', '')
                if preferred_timeframes:
                    scenario.preferred_timeframes = [t.strip() for t in preferred_timeframes.split(';') if t.strip()]
                else:
                    scenario.preferred_timeframes = []
                
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Error processing scenario: {str(e)}")
                continue
        
        if imported_count > 0:
            db.session.commit()
            flash(f'Successfully imported {imported_count} scenarios.', 'success')
        else:
            flash('No scenarios were imported.', 'warning')
        
        if errors:
            flash(f'Import completed with {len(errors)} errors/warnings.', 'warning')
            current_app.logger.warning(f"P12 import errors: {errors}")
        
        return redirect(url_for('p12_scenarios.list_scenarios'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error importing P12 scenarios: {e}")
        flash('Import failed due to an unexpected error.', 'danger')
        return redirect(url_for('p12_scenarios.list_scenarios'))


@p12_scenarios_bp.route('/download-template', methods=['GET'])
@login_required
@admin_required
def download_csv_template():
    """Download CSV template for P12 scenario imports with example data."""
    import csv
    import io
    from flask import Response
    
    # Create CSV template with example data
    output = io.StringIO()
    
    # Define CSV columns based on import function and P12Scenario model
    fieldnames = [
        'scenario_number',
        'scenario_name', 
        'short_description',
        'detailed_description',
        'hod_lod_implication',
        'directional_bias',
        'alert_criteria',
        'confirmation_criteria',
        'entry_strategy',
        'typical_targets',
        'stop_loss_guidance',
        'risk_percentage',
        'is_active',
        'models_to_activate',
        'models_to_avoid',
        'risk_guidance',
        'preferred_timeframes',
        'key_considerations'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    # Add example P12 scenario
    example_scenario = {
        'scenario_number': '3A',
        'scenario_name': 'Example: Look Above P12 High and Go (Bullish Continuation)',
        'short_description': 'Bullish continuation scenario when price breaks above P12 high level',
        'detailed_description': 'This scenario occurs when price action demonstrates strength by breaking above the P12 high established during the overnight session. The break should be accompanied by volume and momentum, indicating institutional interest in pushing prices higher.',
        'hod_lod_implication': 'Bullish bias with potential for new daily highs. Consider reduced position sizing near prior resistance levels.',
        'directional_bias': 'bullish',
        'alert_criteria': 'Price approaching P12 high with strong momentum; Volume increasing on approach; No major resistance overhead',
        'confirmation_criteria': 'Clean break above P12 high by at least 2-4 handles; Hold above level for minimum 5 minutes; Volume confirmation on breakout',
        'entry_strategy': 'Enter long on pullback to P12 high level (now support) or on initial breakout with stop below P12 high',
        'typical_targets': 'Next major resistance level; Prior day high; Fibonacci extensions from P12 range',
        'stop_loss_guidance': 'Place stop loss 2-4 handles below P12 high level. Risk 0.5-1% of account per trade.',
        'risk_percentage': '0.75',
        'is_active': 'true',
        'models_to_activate': '0930 Opening Range;Captain Backtest;P12 Scenario-Based',
        'models_to_avoid': 'HOD/LOD Reversal;Midnight Open Retracement',
        'risk_guidance': 'Reduce position size during high volatility periods. Avoid trading during major news releases.',
        'preferred_timeframes': '5m;15m;1h',
        'key_considerations': 'Monitor Asia session behavior; Check for overnight news impact; Verify volume profile alignment'
    }
    
    writer.writerow(example_scenario)
    
    # Create response
    output.seek(0)
    filename = f"P12_Scenarios_Import_Template_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@p12_scenarios_bp.route('/upload-main-image', methods=['POST'])
@login_required
@admin_required
def upload_main_image():
    """Upload main P12 overview image."""
    print("=== UPLOAD MAIN IMAGE ROUTE CALLED ===")
    print("Request files:", list(request.files.keys()))
    print("Request form:", dict(request.form))

    if 'image' not in request.files:
        print("No image file in request")
        return jsonify({'success': False, 'error': 'No image file provided'})

    file = request.files['image']
    print("File received:", file.filename)
    print("File size:", len(file.read()))
    file.seek(0)  # Reset file pointer after reading

    caption = request.form.get('caption', 'P12 Scenarios Overview')
    print("Caption:", caption)

    try:
        # Use global image manager
        image_manager = ImageManager('p12_scenario')
        save_result = image_manager.save_image(file, entity_id=1)
        print("Save result:", save_result)

        if not save_result['success']:
            print("Image manager failed:", save_result)
            return jsonify(save_result)

        # Delete existing main image if it exists
        existing_image = GlobalImage.query.filter_by(
            entity_type='p12_overview',
            entity_id=1
        ).first()

        if existing_image:
            print("Deleting existing image:", existing_image.id)
            image_manager.delete_image(existing_image.filename)
            db.session.delete(existing_image)

        # Create database record
        global_image = GlobalImage(
            entity_type='p12_overview',
            entity_id=1,
            user_id=current_user.id,
            filename=save_result['filename'],
            original_filename=file.filename,
            relative_path=save_result['relative_path'],
            file_size=save_result['file_size'],
            mime_type=save_result['mime_type'],
            caption=caption,
            is_optimized=True
        )

        db.session.add(global_image)
        db.session.commit()
        print("Image saved with ID:", global_image.id)

        response_data = {
            'success': True,
            'image_id': global_image.id,
            'image_url': url_for('images.serve_image', image_id=global_image.id),
            'message': 'Overview image uploaded successfully'
        }
        print("Returning response:", response_data)
        return jsonify(response_data)

    except Exception as e:
        db.session.rollback()
        print("Exception occurred:", str(e))
        import traceback
        traceback.print_exc()
        current_app.logger.error(f'Error uploading main P12 image: {str(e)}')
        return jsonify({'success': False, 'error': 'Failed to upload image'})


@p12_scenarios_bp.route('/delete-main-image', methods=['POST'])
@login_required
@admin_required
def delete_main_image():
    """Delete main P12 overview image."""
    try:
        # Get the main image
        main_image = GlobalImage.query.filter_by(
            entity_type='p12_overview',
            entity_id=1
        ).first()

        if not main_image:
            return jsonify({'success': False, 'error': 'No overview image to delete'})

        image_manager = ImageManager('p12_scenario')
        image_manager.delete_image(main_image.filename)
        db.session.delete(main_image)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Overview image deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting main P12 image: {str(e)}')
        return jsonify({'success': False, 'error': 'Failed to delete image'})


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
        # Debug logging - ADD THIS HERE
        print(f"Form validation passed: {form.validate_on_submit()}")
        print(f"Scenario image data: {form.scenario_image.data}")
        print(f"Request files: {request.files}")
        if form.scenario_image.data:
            print(f"Image filename: {form.scenario_image.data.filename}")
            print(f"Image content type: {form.scenario_image.data.content_type}")

        # Check if scenario number conflicts (only if changed)
        if form.scenario_number.data != scenario.scenario_number:
            existing = P12Scenario.query.filter_by(scenario_number=form.scenario_number.data).first()
            if existing:
                flash(f'Scenario {form.scenario_number.data} already exists!', 'danger')
                return render_template('admin/p12_scenarios/edit_scenario.html',
                                       form=form, scenario=scenario, title="Edit P12 Scenario")

        # Handle image upload
        if form.scenario_image.data:
            print("=== CALLING global image upload ===")
            try:
                # Use global image manager
                image_manager = ImageManager('p12_scenario')
                save_result = image_manager.save_image(form.scenario_image.data, entity_id=scenario_id)

                if save_result['success']:
                    # Delete existing images first
                    existing_images = GlobalImage.get_for_entity('p12_scenario', scenario_id)
                    for existing_image in existing_images:
                        image_manager.delete_image(existing_image.filename)
                        db.session.delete(existing_image)

                    # Create new global image record
                    global_image = GlobalImage(
                        entity_type='p12_scenario',
                        entity_id=scenario_id,
                        user_id=current_user.id,
                        filename=save_result['filename'],
                        original_filename=form.scenario_image.data.filename,
                        relative_path=save_result['relative_path'],
                        file_size=save_result['file_size'],
                        mime_type=save_result['mime_type'],
                        has_thumbnail=save_result['thumbnail_path'] is not None,
                        thumbnail_path=save_result['thumbnail_path'],
                        caption=f'P12 Scenario {scenario.scenario_number} Example',
                        is_optimized=True
                    )

                    db.session.add(global_image)

                    # Update legacy fields for backward compatibility
                    scenario.image_filename = save_result['filename']
                    scenario.image_path = save_result['filename']

                    print(f"Global image created with ID: {global_image.id}")
                else:
                    print(f"Global image save failed: {save_result}")

            except Exception as e:
                print(f"Error with global image upload: {str(e)}")
                import traceback
                traceback.print_exc()

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
        # Get image URL from global system or fallback to legacy
        image_url = None
        thumbnail_url = None

        images = GlobalImage.get_for_entity('p12_scenario', scenario.id)
        if images:
            image_url = url_for('images.serve_image', image_id=images[0].id)
            if images[0].has_thumbnail:
                thumbnail_url = url_for('images.serve_image', image_id=images[0].id, thumbnail='true')
        elif scenario.image_path:
            # Fallback to legacy system
            image_url = url_for('p12_scenarios.serve_scenario_image', scenario_id=scenario.id)

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

            # Model recommendations
            'models_to_activate': scenario.models_to_activate or [],
            'models_to_avoid': scenario.models_to_avoid or [],
            'risk_guidance': scenario.risk_guidance,
            'preferred_timeframes': scenario.preferred_timeframes or [],
            'key_considerations': scenario.key_considerations,

            # Image URLs (global system)
            'image_url': image_url,
            'thumbnail_url': thumbnail_url
        })

    return jsonify(scenario_data)


@p12_scenarios_bp.route('/image/<int:scenario_id>')
@login_required
def serve_scenario_image(scenario_id):
    """Serve P12 scenario image (backward compatibility)."""
    # Try to get from global image system first
    images = GlobalImage.get_for_entity('p12_scenario', scenario_id)

    if images:
        # Redirect to global image service
        return redirect(url_for('images.serve_image', image_id=images[0].id))

    # Fallback to legacy system
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


@p12_scenarios_bp.route('/upload-image/<int:scenario_id>', methods=['POST'])
@login_required
@admin_required
def upload_scenario_image(scenario_id):
    """Upload image for P12 scenario using global image system."""
    scenario = P12Scenario.query.get_or_404(scenario_id)

    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image file provided'})

    file = request.files['image']
    caption = request.form.get('caption', f'P12 Scenario {scenario.scenario_number} Example')
    replace_existing = request.form.get('replace_existing', 'false').lower() == 'true'

    try:
        # Use global image manager
        image_manager = ImageManager('p12_scenario')
        save_result = image_manager.save_image(file, entity_id=scenario_id)

        if not save_result['success']:
            return jsonify(save_result)

        # Delete existing image if replace is requested
        if replace_existing:
            existing_images = GlobalImage.get_for_entity('p12_scenario', scenario_id)
            for existing_image in existing_images:
                image_manager.delete_image(existing_image.filename)
                db.session.delete(existing_image)

        # Create database record
        global_image = GlobalImage(
            entity_type='p12_scenario',
            entity_id=scenario_id,
            user_id=current_user.id,
            filename=save_result['filename'],
            original_filename=file.filename,
            relative_path=save_result['relative_path'],
            file_size=save_result['file_size'],
            mime_type=save_result['mime_type'],
            has_thumbnail=save_result['thumbnail_path'] is not None,
            thumbnail_path=save_result['thumbnail_path'],
            caption=caption,
            is_optimized=True
        )

        db.session.add(global_image)
        db.session.commit()

        # Update legacy fields for backward compatibility
        scenario.image_filename = save_result['filename']
        scenario.image_path = save_result['filename']
        scenario.updated_date = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'image_id': global_image.id,
            'image_url': url_for('images.serve_image', image_id=global_image.id),
            'message': f'Image uploaded successfully for scenario {scenario.scenario_number}'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error uploading P12 scenario image: {str(e)}')
        return jsonify({'success': False, 'error': 'Failed to upload image'})




# Add this route for deleting images
@p12_scenarios_bp.route('/delete-image/<int:scenario_id>', methods=['POST'])
@login_required
@admin_required
def delete_scenario_image(scenario_id):
    """Delete image for P12 scenario."""
    scenario = P12Scenario.query.get_or_404(scenario_id)

    # Get the scenario's images
    images = GlobalImage.get_for_entity('p12_scenario', scenario_id)

    if not images:
        return jsonify({'success': False, 'error': 'No images to delete'})

    try:
        image_manager = ImageManager('p12_scenario')

        for image in images:
            # Delete files
            image_manager.delete_image(image.filename)
            # Delete database record
            db.session.delete(image)

        # Clear legacy fields
        scenario.image_filename = None
        scenario.image_path = None
        scenario.updated_date = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Images deleted successfully for scenario {scenario.scenario_number}'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting P12 scenario images: {str(e)}')
        return jsonify({'success': False, 'error': 'Failed to delete images'})
