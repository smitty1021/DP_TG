# In app/blueprints/tags_bp.py - Change the blueprint name from 'tags_management' to 'tags'

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Tag
from app.forms import TagForm

# CHANGE THIS LINE: Change 'tags_management' to 'tags'
tags_bp = Blueprint('tags', __name__, url_prefix='/tags', template_folder='../templates/tags')


@tags_bp.route('/')
@login_required
def tags_list():
    """Display a list of all user-created tags."""
    user_tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name).all()
    return render_template('tags_list.html', title='Manage Tags', tags=user_tags)


@tags_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_tag():
    """Create a new tag."""
    form = TagForm()
    if form.validate_on_submit():
        existing_tag = Tag.query.filter_by(user_id=current_user.id, name=form.name.data).first()
        if existing_tag:
            flash('A tag with this name already exists.', 'warning')
        else:
            new_tag = Tag(name=form.name.data, user_id=current_user.id)
            db.session.add(new_tag)
            db.session.commit()
            flash(f'Tag "{new_tag.name}" created successfully!', 'success')
            return redirect(url_for('tags.tags_list'))
    return render_template('create_tag.html', title='Create New Tag', form=form)


@tags_bp.route('/<int:tag_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_tag(tag_id):
    """Edit an existing tag."""
    tag = Tag.query.get_or_404(tag_id)
    if tag.user_id != current_user.id:
        abort(403)
    form = TagForm(obj=tag)
    if form.validate_on_submit():
        tag.name = form.name.data
        db.session.commit()
        flash(f'Tag "{tag.name}" updated successfully!', 'success')
        return redirect(url_for('tags.tags_list'))
    return render_template('edit_tag.html', title='Edit Tag', form=form, tag=tag)


@tags_bp.route('/<int:tag_id>/delete', methods=['POST'])
@login_required
def delete_tag(tag_id):
    """Delete a tag."""
    tag = Tag.query.get_or_404(tag_id)
    if tag.user_id != current_user.id:
        abort(403)

    # Note: This will also remove the tag from any trades it's associated with.
    db.session.delete(tag)
    db.session.commit()
    flash(f'Tag "{tag.name}" has been deleted.', 'success')
    return redirect(url_for('tags.tags_list'))