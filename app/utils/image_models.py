# app/models/image_models.py
"""
Global image database models
"""

from app import db
from datetime import datetime
from flask import current_app
import os


class GlobalImage(db.Model):
    """
    Universal image model that can be used across the entire application.
    Replaces entity-specific image models where appropriate.
    """
    __tablename__ = 'global_image'

    id = db.Column(db.Integer, primary_key=True)

    # Entity relationship (polymorphic)
    entity_type = db.Column(db.String(50), nullable=False, index=True)  # 'p12_scenario', 'daily_journal', etc.
    entity_id = db.Column(db.Integer, nullable=False, index=True)  # ID of the related entity

    # User who uploaded the image
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    # File information
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)  # User's original filename
    relative_path = db.Column(db.String(500), nullable=False)  # Path relative to upload folder
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=True)

    # Image-specific metadata
    image_width = db.Column(db.Integer, nullable=True)
    image_height = db.Column(db.Integer, nullable=True)
    has_thumbnail = db.Column(db.Boolean, default=False, nullable=False)
    thumbnail_path = db.Column(db.String(500), nullable=True)

    # Metadata
    upload_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    caption = db.Column(db.String(500), nullable=True)
    image_type = db.Column(db.String(50), nullable=True)  # 'chart', 'screenshot', 'diagram', etc.
    is_optimized = db.Column(db.Boolean, default=False, nullable=False)

    # Usage tracking
    view_count = db.Column(db.Integer, default=0, nullable=False)
    last_accessed = db.Column(db.DateTime, nullable=True)

    # Relationships
    uploader = db.relationship('User', backref='uploaded_images', lazy=True)

    # Indexes for common queries
    __table_args__ = (
        db.Index('idx_global_image_entity', 'entity_type', 'entity_id'),
        db.Index('idx_global_image_user_date', 'user_id', 'upload_date'),
    )

    def __repr__(self):
        return f'<GlobalImage {self.filename} for {self.entity_type}:{self.entity_id}>'

    @property
    def full_disk_path(self):
        """Get full path to image file on disk."""
        upload_folder = current_app.config.get('UPLOAD_FOLDER',
                                               os.path.join(current_app.instance_path, 'uploads'))
        return os.path.join(upload_folder, self.relative_path)

    @property
    def full_thumbnail_path(self):
        """Get full path to thumbnail file on disk."""
        if not self.has_thumbnail or not self.thumbnail_path:
            return None
        upload_folder = current_app.config.get('UPLOAD_FOLDER',
                                               os.path.join(current_app.instance_path, 'uploads'))
        return os.path.join(upload_folder, self.thumbnail_path)

    def increment_view_count(self):
        """Track when image is viewed."""
        self.view_count += 1
        self.last_accessed = datetime.utcnow()
        db.session.commit()

    @classmethod
    def get_for_entity(cls, entity_type, entity_id):
        """Get all images for a specific entity."""
        return cls.query.filter_by(entity_type=entity_type, entity_id=entity_id).order_by(cls.upload_date.desc()).all()

    @classmethod
    def get_by_user(cls, user_id, entity_type=None):
        """Get all images uploaded by a specific user."""
        query = cls.query.filter_by(user_id=user_id)
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        return query.order_by(cls.upload_date.desc()).all()

    @classmethod
    def get_recent(cls, limit=20, entity_type=None):
        """Get recently uploaded images."""
        query = cls.query
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        return query.order_by(cls.upload_date.desc()).limit(limit).all()