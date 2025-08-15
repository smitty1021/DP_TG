# app/blueprints/image_bp.py
"""
Global Image Management Blueprint
Handles all image operations across the application
"""

import os
import zipfile
import tempfile
from datetime import datetime
from flask import (
    Blueprint, request, jsonify, send_file, current_app,
    abort, url_for, render_template, flash, redirect
)
from flask_login import login_required, current_user

from app import db
from app.models import GlobalImage, TradeImage
from app.utils.image_manager import ImageManager


# Admin required decorator
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


image_bp = Blueprint('images', __name__, url_prefix='/images')


@image_bp.route('/upload/<string:entity_type>/<int:entity_id>', methods=['POST'])
@login_required
def upload_image(entity_type, entity_id):
    """
    Universal image upload endpoint.

    Args:
        entity_type: Type of entity (p12_scenario, daily_journal, trade, etc.)
        entity_id: ID of the entity
    """
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image file provided'})

    file = request.files['image']
    caption = request.form.get('caption', '')
    replace_existing = request.form.get('replace_existing', 'false').lower() == 'true'

    # Initialize image manager for entity type
    image_manager = ImageManager(entity_type)

    # Save image
    save_result = image_manager.save_image(file, entity_id=entity_id)

    if not save_result['success']:
        return jsonify(save_result)

    try:
        # Delete existing image if replace is requested
        if replace_existing:
            existing_images = GlobalImage.get_for_entity(entity_type, entity_id)
            for existing_image in existing_images:
                image_manager.delete_image(existing_image.filename)
                db.session.delete(existing_image)

        # Create database record
        global_image = GlobalImage(
            entity_type=entity_type,
            entity_id=entity_id,
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

        # Get image dimensions if available
        try:
            from PIL import Image
            with Image.open(save_result['file_path']) as img:
                global_image.image_width, global_image.image_height = img.size
        except:
            pass  # Not critical if we can't get dimensions

        db.session.add(global_image)
        db.session.commit()

        return jsonify({
            'success': True,
            'image_id': global_image.id,
            'image_url': url_for('images.serve_image', image_id=global_image.id),
            'thumbnail_url': url_for('images.serve_image', image_id=global_image.id,
                                     thumbnail='true') if global_image.has_thumbnail else None,
            'message': f'Image uploaded successfully'
        })

    except Exception as e:
        db.session.rollback()
        # Clean up uploaded file on database error
        image_manager.delete_image(save_result['filename'])
        current_app.logger.error(f'Database error uploading image: {str(e)}')
        return jsonify({'success': False, 'error': 'Database error occurred'})


@image_bp.route('/bulk-upload/<string:entity_type>', methods=['POST'])
@login_required
@admin_required
def bulk_upload_images(entity_type):
    """Bulk upload images for an entity type."""
    if 'images' not in request.files:
        return jsonify({'success': False, 'error': 'No images provided'})

    files = request.files.getlist('images')
    naming_pattern = request.form.get('naming_pattern', 'original')
    overwrite_existing = request.form.get('overwrite_existing', 'false').lower() == 'true'

    image_manager = ImageManager(entity_type)

    # Process each file
    uploaded_count = 0
    errors = []

    for file in files:
        if not file or file.filename == '':
            continue

        if not image_manager.is_allowed_file(file.filename):
            errors.append(f'{file.filename}: Invalid file type')
            continue

        # Try to match filename to entity
        entity_id = None
        if naming_pattern == 'p12_scenario':
            # Extract scenario number from filename patterns like "P12_1.png", "p12_2.jpg"
            import re
            match = re.search(r'(?:p12_|scenario_)?(\d+)\.', file.filename.lower())
            if match:
                entity_id = int(match.group(1))

        try:
            # Save image
            save_result = image_manager.save_image(file, entity_id=entity_id)

            if not save_result['success']:
                errors.append(
                    f'{file.filename}: {save_result["errors"][0] if save_result.get("errors") else "Failed to save"}')
                continue

            # Delete existing image if overwrite is requested
            if overwrite_existing and entity_id:
                existing_images = GlobalImage.get_for_entity(entity_type, entity_id)
                for existing_image in existing_images:
                    image_manager.delete_image(existing_image.filename)
                    db.session.delete(existing_image)

            # Create database record
            global_image = GlobalImage(
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=current_user.id,
                filename=save_result['filename'],
                original_filename=file.filename,
                relative_path=save_result['relative_path'],
                file_size=save_result['file_size'],
                mime_type=save_result['mime_type'],
                has_thumbnail=save_result['thumbnail_path'] is not None,
                caption=f'{entity_type.title()} {entity_id} Example' if entity_id else 'Uploaded Image',
                is_optimized=True
            )

            db.session.add(global_image)
            uploaded_count += 1

        except Exception as e:
            errors.append(f'{file.filename}: {str(e)}')
            continue

    try:
        db.session.commit()

        return jsonify({
            'success': True,
            'uploaded_count': uploaded_count,
            'total_files': len(files),
            'message': f'Successfully uploaded {uploaded_count} images',
            'errors': errors if errors else None
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Database commit error in bulk upload: {str(e)}')
        return jsonify({'success': False, 'error': 'Database error occurred'})


@image_bp.route('/serve/<int:image_id>')
@image_bp.route('/serve/<int:image_id>/<string:thumbnail>')
@login_required
def serve_image(image_id, thumbnail=None):
    """Serve image files."""
    image = GlobalImage.query.get_or_404(image_id)

    # Get file path (for now, we don't have thumbnails, so just serve the main image)
    file_path = image.full_disk_path

    if not file_path or not os.path.exists(file_path):
        abort(404)

    # Track view
    try:
        image.view_count += 1
        image.last_accessed = datetime.utcnow()
        db.session.commit()
    except:
        pass  # Don't fail serving if view tracking fails

    return send_file(file_path)


@image_bp.route('/serve-trade-image/<int:image_id>')
@login_required
def serve_trade_image(image_id):
    """Serve trade image files."""
    trade_image = TradeImage.query.get_or_404(image_id)
    
    # Security check: ensure user owns the trade or is admin
    if trade_image.user_id != current_user.id and current_user.role.name != 'ADMIN':
        abort(403)
    
    # Get file path
    file_path = trade_image.full_disk_path
    
    if not file_path or not os.path.exists(file_path):
        abort(404)
    
    return send_file(file_path)


@image_bp.route('/delete/<int:image_id>', methods=['POST', 'DELETE'])
@login_required
def delete_image(image_id):
    """Delete an image."""
    image = GlobalImage.query.get_or_404(image_id)

    # Check permissions (user owns image or is admin)
    if image.user_id != current_user.id and not current_user.is_admin():
        abort(403)

    try:
        # Delete files
        image_manager = ImageManager(image.entity_type)
        image_manager.delete_image(image.filename)

        # Delete database record
        db.session.delete(image)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Image deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting image {image_id}: {str(e)}')
        return jsonify({'success': False, 'error': 'Failed to delete image'})


@image_bp.route('/gallery')
@image_bp.route('/gallery/<string:entity_type>')
@login_required
def image_gallery(entity_type=None):
    """Display image gallery with filtering."""
    # Build query
    query = GlobalImage.query

    if entity_type:
        query = query.filter_by(entity_type=entity_type)

    # Apply filters from request args
    if request.args.get('entity_type'):
        query = query.filter_by(entity_type=request.args.get('entity_type'))

    # Sorting
    sort_by = request.args.get('sort_by', 'upload_date')

    if sort_by == 'upload_date':
        query = query.order_by(GlobalImage.upload_date.desc())
    elif sort_by == 'filename':
        query = query.order_by(GlobalImage.filename)
    elif sort_by == 'file_size':
        query = query.order_by(GlobalImage.file_size.desc())
    elif sort_by == 'entity_id':
        query = query.order_by(GlobalImage.entity_type, GlobalImage.entity_id)

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('ITEMS_PER_PAGE', 20)
    images = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    # Get statistics
    stats = {
        'total_images': GlobalImage.query.count(),
        'by_entity_type': {}
    }

    # Count by entity type
    from sqlalchemy import func
    entity_counts = db.session.query(
        GlobalImage.entity_type,
        func.count(GlobalImage.id)
    ).group_by(GlobalImage.entity_type).all()

    for entity, count in entity_counts:
        stats['by_entity_type'][entity] = count

    # Create a simple form object for the template
    class SimpleForm:
        def __init__(self):
            self.entity_type = SimpleField(request.args.get('entity_type', ''))
            self.sort_by = SimpleField(request.args.get('sort_by', 'upload_date'))

    class SimpleField:
        def __init__(self, data):
            self.data = data

    form = SimpleForm()

    return render_template('images/gallery.html',
                           images=images,
                           form=form,
                           stats=stats,
                           title=f'Image Gallery - {entity_type.title() if entity_type else "All Images"}')


@image_bp.route('/api/<string:entity_type>/<int:entity_id>')
@login_required
def api_get_entity_images(entity_type, entity_id):
    """API endpoint to get all images for a specific entity."""
    images = GlobalImage.get_for_entity(entity_type, entity_id)

    image_data = []
    for image in images:
        image_data.append({
            'id': image.id,
            'filename': image.original_filename,
            'caption': image.caption,
            'upload_date': image.upload_date.isoformat(),
            'file_size': image.file_size,
            'image_url': url_for('images.serve_image', image_id=image.id),
            'thumbnail_url': url_for('images.serve_image', image_id=image.id,
                                     thumbnail='true') if image.has_thumbnail else None,
            'width': image.image_width,
            'height': image.image_height,
            'view_count': image.view_count
        })

    return jsonify(image_data)


# Helper functions for backward compatibility with existing code
def get_p12_scenario_image_url(scenario_id):
    """Helper function for P12 scenario image URLs."""
    image = GlobalImage.query.filter_by(
        entity_type='p12_scenario',
        entity_id=scenario_id
    ).first()

    if image:
        return url_for('images.serve_image', image_id=image.id)
    return None


def get_daily_journal_images(journal_id):
    """Helper function to get daily journal images."""
    return GlobalImage.get_for_entity('daily_journal', journal_id)


def get_trade_images(trade_id):
    """Helper function to get trade images."""
    return GlobalImage.get_for_entity('trade', trade_id)


# Add these routes to your existing image_bp.py file

@image_bp.route('/export/<string:entity_type>')
@login_required
@admin_required
def export_images(entity_type):
    """Export all images for an entity type as ZIP."""
    images = GlobalImage.query.filter_by(entity_type=entity_type).all()

    if not images:
        flash(f'No images found for {entity_type}', 'warning')
        return redirect(url_for('images.image_gallery', entity_type=entity_type))

    # Create temporary ZIP file
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')

    try:
        with zipfile.ZipFile(temp_zip.name, 'w') as zip_file:
            for image in images:
                file_path = image.full_disk_path
                if file_path and os.path.exists(file_path):
                    # Create clean filename for ZIP
                    extension = os.path.splitext(image.filename)[1]
                    clean_name = f"{entity_type}_{image.entity_id}_{image.original_filename}"
                    zip_file.write(file_path, clean_name)

        return send_file(
            temp_zip.name,
            as_attachment=True,
            download_name=f'{entity_type}_images_{datetime.now().strftime("%Y%m%d")}.zip',
            mimetype='application/zip'
        )

    except Exception as e:
        current_app.logger.error(f'Error creating image export: {str(e)}')
        flash('Error creating image export', 'danger')
        return redirect(url_for('images.image_gallery', entity_type=entity_type))
    finally:
        # Clean up temp file after delay
        import threading
        def cleanup():
            import time
            time.sleep(10)
            try:
                os.unlink(temp_zip.name)
            except:
                pass

        thread = threading.Thread(target=cleanup)
        thread.start()


@image_bp.route('/cleanup')
@login_required
@admin_required
def cleanup_orphaned_images():
    """Clean up orphaned image files and database records."""
    cleanup_results = {
        'orphaned_files_deleted': 0,
        'orphaned_records_deleted': 0,
        'errors': []
    }

    try:
        # Find orphaned database records (files don't exist)
        all_images = GlobalImage.query.all()
        for image in all_images:
            if not os.path.exists(image.full_disk_path):
                db.session.delete(image)
                cleanup_results['orphaned_records_deleted'] += 1

        # Find orphaned files (no database record)
        upload_folder = current_app.config.get('UPLOAD_FOLDER')

        for entity_config in ImageManager.ENTITY_CONFIGS.values():
            entity_folder = os.path.join(upload_folder, entity_config['subfolder'])
            if not os.path.exists(entity_folder):
                continue

            for filename in os.listdir(entity_folder):
                file_path = os.path.join(entity_folder, filename)
                if not os.path.isfile(file_path):
                    continue

                # Check if file has corresponding database record
                relative_path = os.path.join(entity_config['subfolder'], filename)
                image_record = GlobalImage.query.filter_by(relative_path=relative_path).first()

                if not image_record:
                    try:
                        os.remove(file_path)
                        cleanup_results['orphaned_files_deleted'] += 1
                    except Exception as e:
                        cleanup_results['errors'].append(f'Could not delete {filename}: {str(e)}')

        db.session.commit()

        flash(
            f'Cleanup completed: {cleanup_results["orphaned_records_deleted"]} records and {cleanup_results["orphaned_files_deleted"]} files removed',
            'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error during image cleanup: {str(e)}')
        flash('Cleanup failed', 'danger')

    return redirect(url_for('images.image_gallery'))