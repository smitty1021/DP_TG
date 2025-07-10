# Create this file: app/utils/image_manager.py

import os
import uuid
import mimetypes
from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename



class ImageManager:
    """
    Simplified image management class for your current setup.
    """

    # Supported image formats
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Entity-specific configurations
    ENTITY_CONFIGS = {
        'p12_scenario': {
            'subfolder': 'p12_scenarios',
            'max_size': 5 * 1024 * 1024,  # 5MB
        },
        'daily_journal': {
            'subfolder': 'daily_journals',
            'max_size': 10 * 1024 * 1024,  # 10MB
        },
        'trade': {
            'subfolder': 'trades',
            'max_size': 10 * 1024 * 1024,  # 10MB
        },
        'general': {
            'subfolder': 'general',
            'max_size': 10 * 1024 * 1024,  # 10MB
        }
    }

    def __init__(self, entity_type='general'):
        """Initialize ImageManager for specific entity type."""
        self.entity_type = entity_type
        self.config = self.ENTITY_CONFIGS.get(entity_type, self.ENTITY_CONFIGS['general'])
        self.upload_folder = current_app.config.get('UPLOAD_FOLDER',
                                                    os.path.join(current_app.instance_path, 'uploads'))
        self.entity_folder = os.path.join(self.upload_folder, self.config['subfolder'])

        # Ensure folder exists
        os.makedirs(self.entity_folder, exist_ok=True)

    @classmethod
    def is_allowed_file(cls, filename):
        """Check if file extension is allowed."""
        return ('.' in filename and
                filename.rsplit('.', 1)[1].lower() in cls.ALLOWED_EXTENSIONS)

    def validate_image(self, file):
        """Validate uploaded image file."""
        result = {'valid': False, 'errors': []}

        if not file or file.filename == '':
            result['errors'].append('No file selected')
            return result

        if not self.is_allowed_file(file.filename):
            result['errors'].append('Invalid file type. Allowed: ' + ', '.join(self.ALLOWED_EXTENSIONS))
            return result

        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > self.config['max_size']:
            max_mb = self.config['max_size'] / (1024 * 1024)
            result['errors'].append(f'File too large. Maximum size: {max_mb:.1f}MB')
            return result

        result['valid'] = True
        return result

    def save_image(self, file, entity_id=None):
        """Save uploaded image."""
        validation = self.validate_image(file)
        if not validation['valid']:
            return {'success': False, 'errors': validation['errors']}

        try:
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            name_part, ext = os.path.splitext(original_filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            entity_prefix = f"{self.entity_type}_{entity_id}_" if entity_id else f"{self.entity_type}_"
            filename = f"{entity_prefix}{timestamp}_{uuid.uuid4().hex[:8]}{ext}"

            # Save file
            file_path = os.path.join(self.entity_folder, filename)
            file.save(file_path)

            # Get file info
            file_size = os.path.getsize(file_path)
            mime_type = mimetypes.guess_type(file_path)[0]

            return {
                'success': True,
                'filename': filename,
                'file_path': file_path,
                'relative_path': os.path.join(self.config['subfolder'], filename),
                'file_size': file_size,
                'mime_type': mime_type,
                'thumbnail_path': None
            }

        except Exception as e:
            current_app.logger.error(f'Error saving image: {str(e)}')
            return {'success': False, 'errors': [f'Failed to save image: {str(e)}']}

    def delete_image(self, filename):
        """Delete image file."""
        try:
            file_path = os.path.join(self.entity_folder, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception as e:
            current_app.logger.error(f'Error deleting image {filename}: {str(e)}')
            return False

