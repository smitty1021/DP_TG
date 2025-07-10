# Create this file: app/utils/p12_image_helpers.py

from app.utils.image_manager import ImageManager
from app.models import GlobalImage
from app.models import P12Scenario
from app import db
from flask_login import current_user
from flask import current_app
import os
from datetime import datetime


def upload_p12_scenario_image(scenario_id, file, user_id, caption=None):
    """
    Upload image for P12 scenario using global image system.

    Args:
        scenario_id (int): P12 scenario ID
        file: Uploaded file object
        user_id (int): User ID uploading the image
        caption (str, optional): Image caption

    Returns:
        dict: Result with success status and image info
    """
    try:
        scenario = P12Scenario.query.get_or_404(scenario_id)

        # Initialize image manager for P12 scenarios
        image_manager = ImageManager('p12_scenario')

        # Save the image
        save_result = image_manager.save_image(file, entity_id=scenario_id)

        if not save_result['success']:
            return save_result

        # Create database record
        global_image = GlobalImage(
            entity_type='p12_scenario',
            entity_id=scenario_id,
            user_id=user_id,
            filename=save_result['filename'],
            original_filename=file.filename,
            relative_path=save_result['relative_path'],
            file_size=save_result['file_size'],
            mime_type=save_result['mime_type'],
            has_thumbnail=save_result['thumbnail_path'] is not None,
            thumbnail_path=save_result['thumbnail_path'],
            caption=caption or f'P12 Scenario {scenario.scenario_number} Example',
            is_optimized=True
        )

        # Get image dimensions if possible
        try:
            from PIL import Image
            with Image.open(save_result['file_path']) as img:
                global_image.image_width, global_image.image_height = img.size
        except:
            pass  # Not critical

        db.session.add(global_image)

        # Update legacy fields for backward compatibility
        scenario.image_filename = save_result['filename']
        scenario.image_path = save_result['filename']
        scenario.updated_date = datetime.utcnow()

        db.session.commit()

        return {
            'success': True,
            'image_id': global_image.id,
            'filename': save_result['filename'],
            'message': f'Image uploaded successfully for scenario {scenario.scenario_number}'
        }

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error uploading P12 scenario image: {str(e)}')
        return {'success': False, 'error': str(e)}


def get_p12_scenario_images(scenario_id):
    """
    Get all images for a P12 scenario.

    Args:
        scenario_id (int): P12 scenario ID

    Returns:
        list: List of GlobalImage objects
    """
    return GlobalImage.get_for_entity('p12_scenario', scenario_id)


def delete_p12_scenario_images(scenario_id, user_id):
    """
    Delete all images for a P12 scenario.

    Args:
        scenario_id (int): P12 scenario ID
        user_id (int): User ID (for permission checking)

    Returns:
        dict: Result with success status
    """
    try:
        scenario = P12Scenario.query.get_or_404(scenario_id)
        images = get_p12_scenario_images(scenario_id)

        if not images:
            return {'success': False, 'error': 'No images to delete'}

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

        return {
            'success': True,
            'message': f'Deleted {len(images)} images for scenario {scenario.scenario_number}'
        }

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error deleting P12 scenario images: {str(e)}')
        return {'success': False, 'error': str(e)}


def migrate_legacy_p12_images():
    """
    Migrate existing P12 scenario images to global system.
    Run this once to move your existing images.

    Returns:
        dict: Migration results
    """
    try:
        scenarios = P12Scenario.query.filter(P12Scenario.image_path.isnot(None)).all()
        migrated_count = 0
        errors = []

        for scenario in scenarios:
            try:
                # Check if already migrated
                existing = GlobalImage.query.filter_by(
                    entity_type='p12_scenario',
                    entity_id=scenario.id
                ).first()

                if existing:
                    continue  # Skip if already migrated

                # Get file size
                upload_folder = current_app.config.get('UPLOAD_FOLDER')
                file_path = os.path.join(upload_folder, 'p12_scenarios', scenario.image_path)
                file_size = 0

                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)

                # Create GlobalImage record
                global_image = GlobalImage(
                    entity_type='p12_scenario',
                    entity_id=scenario.id,
                    user_id=1,  # Admin user - adjust as needed
                    filename=scenario.image_path,
                    original_filename=scenario.image_path,
                    relative_path=f'p12_scenarios/{scenario.image_path}',
                    file_size=file_size,
                    caption=f'P12 Scenario {scenario.scenario_number} Example',
                    is_optimized=False  # Legacy images not optimized
                )

                # Try to get image dimensions
                try:
                    from PIL import Image
                    with Image.open(file_path) as img:
                        global_image.image_width, global_image.image_height = img.size
                except:
                    pass

                db.session.add(global_image)
                migrated_count += 1

            except Exception as e:
                errors.append(f'Scenario {scenario.scenario_number}: {str(e)}')
                continue

        db.session.commit()

        return {
            'success': True,
            'migrated_count': migrated_count,
            'total_scenarios': len(scenarios),
            'errors': errors
        }

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error migrating P12 images: {str(e)}')
        return {'success': False, 'error': str(e)}


# Flask CLI command to run migration
def register_p12_migration_command(app):
    """Register CLI command for P12 image migration."""

    @app.cli.command("migrate-p12-images")
    def migrate_p12_images_command():
        """Migrate existing P12 scenario images to global system."""
        import click

        click.echo("Starting P12 image migration...")
        result = migrate_legacy_p12_images()

        if result['success']:
            click.echo(f"Migration completed successfully!")
            click.echo(f"Migrated: {result['migrated_count']} images")
            click.echo(f"Total scenarios checked: {result['total_scenarios']}")

            if result['errors']:
                click.echo(f"Errors encountered: {len(result['errors'])}")
                for error in result['errors']:
                    click.echo(f"  - {error}")
        else:
            click.echo(f"Migration failed: {result['error']}")


# Usage examples for your routes:

# In your P12 scenario routes, you can now use:
"""
from app.utils.p12_image_helpers import upload_p12_scenario_image, get_p12_scenario_images

@p12_scenarios_bp.route('/upload-image/<int:scenario_id>', methods=['POST'])
@login_required
@admin_required
def upload_image(scenario_id):
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image provided'})

    file = request.files['image']
    caption = request.form.get('caption', '')

    result = upload_p12_scenario_image(scenario_id, file, current_user.id, caption)
    return jsonify(result)
"""