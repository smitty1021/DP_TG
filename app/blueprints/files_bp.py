import os
import uuid
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, send_from_directory, abort)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image # For thumbnail generation, make sure Pillow is in requirements.txt
import io

from app.extensions import db
from app.models import File, Activity # Assuming File model is defined in app.models
from app.forms import FileUploadForm # Assuming FileUploadForm is in app.forms
# You'll need the record_activity helper, ideally from utils.py
# For now, we can define a placeholder or copy it here temporarily if not in utils

files_bp = Blueprint('files', __name__,
                     template_folder='../templates/files', # We'll create this folder
                     url_prefix='/files')

# Placeholder for record_activity if not yet moved to utils.py
# Ideally, import this from app.utils
def record_activity(action, details=None, user_id_for_activity=None):
    # This is a simplified version. Use the one from auth_bp.py or move to utils.py
    activity_user_id = user_id_for_activity if user_id_for_activity is not None else (
        current_user.id if current_user.is_authenticated else None)
    if activity_user_id:
        try:
            new_activity = Activity(user_id=activity_user_id, action=action, details=details,
                                    ip_address=request.remote_addr,
                                    user_agent=request.user_agent.string if request.user_agent else None)
            db.session.add(new_activity)
            db.session.commit()
            current_app.logger.info(f"User {current_user.username} activity: {action} - {details or ''}")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error recording activity for {action}: {e}", exc_info=True)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@files_bp.route('/my_files') # This will be available at /files/my_files
@login_required
def user_my_files(): # This is the endpoint name 'files.user_my_files'
    user_files = []
    if hasattr(current_user, 'files'): # Check if the relationship exists
        user_files = current_user.files.order_by(File.upload_date.desc()).all()
    return render_template('my_files.html', title='My Files', files=user_files)

@files_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def user_upload_file():
    form = FileUploadForm()
    if form.validate_on_submit():
        file_to_upload = form.file.data
        if file_to_upload and allowed_file(file_to_upload.filename):
            original_filename = secure_filename(file_to_upload.filename)
            file_ext = ''
            if '.' in original_filename:
                file_ext = original_filename.rsplit('.', 1)[1].lower()

            unique_filename = f"{uuid.uuid4().hex}.{file_ext if file_ext else 'bin'}"
            # UPLOAD_FOLDER is now instance_path + 'uploads'
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)

            try:
                file_to_upload.save(file_path)
                new_file_obj = File(
                    filename=original_filename,
                    filepath=unique_filename, # Store only the unique part
                    filesize=os.path.getsize(file_path),
                    file_type=file_ext,
                    user_id=current_user.id,
                    mime_type=file_to_upload.mimetype,
                    description=form.description.data,
                    is_public=form.is_public.data
                )
                db.session.add(new_file_obj)
                db.session.commit()
                record_activity('file_upload', f"Uploaded: {original_filename}")
                flash('File successfully uploaded.', 'success')
                return redirect(url_for('files.user_my_files'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"File upload failed: {e}", exc_info=True)
                flash(f'Failed to upload file: {str(e)}', 'danger')
        else:
            if not file_to_upload:
                flash('No file selected for upload.', 'warning')
            else: # File type not allowed
                 flash(f"File type '{file_to_upload.filename.rsplit('.', 1)[1].lower()}' not allowed. Allowed: {', '.join(current_app.config['ALLOWED_EXTENSIONS'])}", 'danger')

    return render_template('upload_file.html', title='Upload File', form=form)


@files_bp.route('/view/<int:file_id>')
@login_required
def view_file(file_id):
    file_record = File.query.get_or_404(file_id)
    if not (file_record.user_id == current_user.id or getattr(current_user, 'is_admin', lambda: False)() or file_record.is_public):
        abort(403)
    try:
        record_activity('file_view', f"Viewed: {file_record.filename}")
        return send_from_directory(
            current_app.config['UPLOAD_FOLDER'],
            file_record.filepath,
            mimetype=file_record.mime_type,
            as_attachment=False # View in browser if possible
        )
    except FileNotFoundError:
        current_app.logger.error(f"File not found on disk: {file_record.filepath}")
        abort(404)
    except Exception as e:
        current_app.logger.error(f"Error viewing file {file_id}: {e}", exc_info=True)
        abort(500)

@files_bp.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    file_record = File.query.get_or_404(file_id)
    if not (file_record.user_id == current_user.id or getattr(current_user, 'is_admin', lambda: False)() or file_record.is_public):
        abort(403)
    try:
        file_record.record_access(commit=True) # Increment download count and update last_accessed
        record_activity('file_download', f"Downloaded: {file_record.filename}")
        return send_from_directory(
            current_app.config['UPLOAD_FOLDER'],
            file_record.filepath,
            as_attachment=True,
            download_name=file_record.filename # Use original filename for download
        )
    except FileNotFoundError:
        current_app.logger.error(f"File not found on disk for download: {file_record.filepath}")
        abort(404)
    except Exception as e:
        current_app.logger.error(f"Error downloading file {file_id}: {e}", exc_info=True)
        abort(500)

@files_bp.route('/delete/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    file_record = File.query.get_or_404(file_id)
    if not (file_record.user_id == current_user.id or getattr(current_user, 'is_admin', lambda: False)()):
        flash("You do not have permission to delete this file.", 'danger')
        return redirect(url_for('files.user_my_files'))

    file_disk_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_record.filepath)
    filename_for_log = file_record.filename

    try:
        if os.path.exists(file_disk_path):
            os.remove(file_disk_path)
        else:
            current_app.logger.warning(f"File not found on disk for deletion: {file_disk_path}, but deleting DB record.")

        db.session.delete(file_record)
        db.session.commit()
        record_activity('file_delete', f"Deleted: {filename_for_log}")
        flash(f"File '{filename_for_log}' has been deleted successfully.", 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting file {file_id}: {e}", exc_info=True)
        flash(f"An error occurred while deleting the file: {str(e)}", 'danger')
    return redirect(url_for('files.user_my_files'))

# Add other file-related routes from v3/app.py if needed (e.g., thumbnail)