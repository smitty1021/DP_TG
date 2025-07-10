# app/utils/image_forms.py
"""
Global image-related forms
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import SelectField, BooleanField, StringField, TextAreaField
from wtforms.validators import Optional, Length


class ImageUploadForm(FlaskForm):
    """Generic image upload form."""

    image = FileField(
        'Image',
        validators=[
            FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images only!'),
            FileSize(max_size=10 * 1024 * 1024, message='File must be less than 10MB')
        ]
    )

    caption = StringField(
        'Caption',
        validators=[Optional(), Length(max=255)],
        description='Optional caption for the image'
    )

    replace_existing = BooleanField(
        'Replace Existing',
        default=False,
        description='Replace existing image if one exists'
    )


class BulkImageUploadForm(FlaskForm):
    """Form for bulk image uploads."""

    images = FileField(
        'Images',
        validators=[
            FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images only!')
        ],
        render_kw={'multiple': True}
    )

    naming_pattern = SelectField(
        'Naming Pattern',
        choices=[
            ('p12_scenario', 'P12 Scenarios (P12_1.png, P12_2.jpg, etc.)'),
            ('sequential', 'Sequential numbering'),
            ('original', 'Keep original names'),
            ('custom', 'Custom pattern')
        ],
        default='original'
    )

    overwrite_existing = BooleanField(
        'Overwrite Existing',
        default=False,
        description='Replace existing images'
    )


class ImageGalleryFilterForm(FlaskForm):
    """Form for filtering image galleries."""

    entity_type = SelectField(
        'Entity Type',
        choices=[
            ('', 'All Types'),
            ('p12_scenario', 'P12 Scenarios'),
            ('daily_journal', 'Daily Journals'),
            ('trade', 'Trade Images'),
            ('user_profile', 'Profile Pictures')
        ],
        default=''
    )

    has_thumbnail = SelectField(
        'Thumbnail Status',
        choices=[
            ('', 'All Images'),
            ('yes', 'Has Thumbnail'),
            ('no', 'No Thumbnail')
        ],
        default=''
    )

    sort_by = SelectField(
        'Sort By',
        choices=[
            ('upload_date', 'Upload Date'),
            ('filename', 'Filename'),
            ('file_size', 'File Size'),
            ('entity_id', 'Entity ID')
        ],
        default='upload_date'
    )
