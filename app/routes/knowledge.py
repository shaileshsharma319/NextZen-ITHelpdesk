import os
from datetime import date
from uuid import uuid4

from flask import Blueprint, abort, current_app, render_template, redirect, send_from_directory, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models.knowledge import KnowledgeAcknowledgement, KnowledgeArticle, KnowledgeAttachment

knowledge = Blueprint('knowledge', __name__)

ALLOWED_KB_ATTACHMENT_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'doc', 'docx',
    'xls', 'xlsx', 'csv', 'ppt', 'pptx', 'zip'
}

ARTICLE_TYPES = [
    ('how_to', 'How-To Guide'),
    ('faq', 'FAQ'),
    ('troubleshooting', 'Troubleshooting'),
    ('known_error', 'Known Error'),
    ('sop', 'SOP / Procedure'),
    ('policy', 'Policy'),
    ('checklist', 'Checklist'),
    ('announcement', 'Announcement'),
    ('release_note', 'Release Note'),
    ('security_advisory', 'Security Advisory'),
    ('onboarding', 'Onboarding'),
    ('offboarding', 'Offboarding'),
    ('asset_guide', 'Asset Guide'),
    ('software_guide', 'Software Guide'),
    ('network_guide', 'Network Guide'),
    ('email_guide', 'Email Guide'),
    ('template', 'Template'),
    ('reference', 'Reference'),
    ('other', 'Other'),
]

ARTICLE_TYPE_LABELS = dict(ARTICLE_TYPES)


def parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def can_view_article(article):
    if not article.is_published and not current_user.can_manage_helpdesk:
        return False
    if article.visibility == 'support' and not current_user.can_manage_helpdesk:
        return False
    return True


def allowed_attachment(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_KB_ATTACHMENT_EXTENSIONS


def article_upload_folder(article_id):
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'knowledge', str(article_id))
    os.makedirs(folder, exist_ok=True)
    return folder


def save_article_attachments(article):
    saved = 0
    for upload in request.files.getlist('attachments'):
        if not upload or not upload.filename:
            continue
        if not allowed_attachment(upload.filename):
            flash(f'Attachment skipped: {upload.filename} is not an allowed file type.', 'warning')
            continue
        original = secure_filename(upload.filename)
        ext = original.rsplit('.', 1)[1].lower() if '.' in original else ''
        stored = f'{uuid4().hex}.{ext}' if ext else uuid4().hex
        path = os.path.join(article_upload_folder(article.id), stored)
        upload.save(path)
        db.session.add(KnowledgeAttachment(
            article_id=article.id,
            original_filename=original,
            stored_filename=stored,
            content_type=upload.mimetype,
            file_size=os.path.getsize(path),
            uploaded_by=current_user.id,
        ))
        saved += 1
    return saved


def related_articles_for(article):
    query = KnowledgeArticle.query.filter(
        KnowledgeArticle.id != article.id,
        KnowledgeArticle.is_published.is_(True),
        KnowledgeArticle.visibility == 'all',
    )
    conditions = [KnowledgeArticle.article_type == article.article_type]
    if article.category:
        conditions.append(KnowledgeArticle.category == article.category)
    related = query.filter(db.or_(*conditions)).order_by(
        KnowledgeArticle.is_featured.desc(),
        KnowledgeArticle.updated_at.desc(),
    ).limit(5).all()
    return related


@knowledge.route('/')
@login_required
def list():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    article_type = request.args.get('type', '').strip()
    status = request.args.get('status', 'published').strip()
    visibility = request.args.get('visibility', '').strip()
    review = request.args.get('review', '').strip()
    tag = request.args.get('tag', '').strip()
    query = KnowledgeArticle.query
    if current_user.can_manage_helpdesk:
        if status == 'draft':
            query = query.filter_by(is_published=False)
        elif status == 'all':
            pass
        else:
            status = 'published'
            query = query.filter_by(is_published=True)
    else:
        status = 'published'
        query = query.filter_by(is_published=True)
    if not current_user.can_manage_helpdesk:
        query = query.filter_by(visibility='all')
    if search:
        like_search = f'%{search}%'
        query = query.filter(db.or_(
            KnowledgeArticle.title.ilike(like_search),
            KnowledgeArticle.summary.ilike(like_search),
            KnowledgeArticle.content.ilike(like_search),
            KnowledgeArticle.tags.ilike(like_search),
        ))
    if category:
        query = query.filter_by(category=category)
    if article_type:
        query = query.filter_by(article_type=article_type)
    if current_user.can_manage_helpdesk and visibility:
        query = query.filter_by(visibility=visibility)
    if current_user.can_manage_helpdesk and review == 'due':
        query = query.filter(KnowledgeArticle.review_date.isnot(None), KnowledgeArticle.review_date <= date.today())
    elif current_user.can_manage_helpdesk and review == 'missing':
        query = query.filter(KnowledgeArticle.review_date.is_(None))
    if tag:
        query = query.filter(KnowledgeArticle.tags.ilike(f'%{tag}%'))
    articles = query.order_by(KnowledgeArticle.is_featured.desc(), KnowledgeArticle.updated_at.desc()).all()
    featured_articles = KnowledgeArticle.query.filter_by(is_published=True, is_featured=True).order_by(KnowledgeArticle.updated_at.desc()).limit(4).all()
    categories = db.session.query(KnowledgeArticle.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    tag_rows = db.session.query(KnowledgeArticle.tags).filter(KnowledgeArticle.tags.isnot(None), KnowledgeArticle.tags != '').all()
    tags = []
    for row in tag_rows:
        for item in (row[0] or '').split(','):
            clean = item.strip()
            if clean and clean not in tags:
                tags.append(clean)
    return render_template(
        'knowledge/list.html',
        articles=articles,
        featured_articles=featured_articles,
        search=search,
        category=category,
        article_type=article_type,
        article_types=ARTICLE_TYPES,
        article_type_labels=ARTICLE_TYPE_LABELS,
        categories=categories,
        status=status,
        visibility=visibility,
        review=review,
        tag=tag,
        tags=sorted(tags),
    )


@knowledge.route('/policies')
@login_required
def policies():
    return redirect(url_for('knowledge.list', type='policy'))


@knowledge.route('/<int:article_id>')
@login_required
def detail(article_id):
    article = KnowledgeArticle.query.get_or_404(article_id)
    if not can_view_article(article):
        flash('Article is not published.', 'warning')
        return redirect(url_for('knowledge.list'))
    article.view_count = (article.view_count or 0) + 1
    db.session.commit()
    acknowledgement = None
    if article.requires_acknowledgement:
        acknowledgement = KnowledgeAcknowledgement.query.filter_by(
            article_id=article.id,
            user_id=current_user.id,
        ).first()
    return render_template(
        'knowledge/detail.html',
        article=article,
        related_articles=related_articles_for(article),
        acknowledgement=acknowledgement,
        acknowledgement_count=KnowledgeAcknowledgement.query.filter_by(article_id=article.id).count(),
    )


@knowledge.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if not current_user.can_manage_helpdesk:
        flash('Access denied.', 'danger')
        return redirect(url_for('knowledge.list'))
    if request.method == 'POST':
        article = KnowledgeArticle(
            title=request.form.get('title', '').strip(),
            article_type=request.form.get('article_type') or 'how_to',
            summary=request.form.get('summary', '').strip() or None,
            content=request.form.get('content', '').strip(),
            category=request.form.get('category', '').strip() or None,
            tags=request.form.get('tags', '').strip() or None,
            visibility=request.form.get('visibility') or 'all',
            review_date=parse_date(request.form.get('review_date')),
            policy_version=request.form.get('policy_version', '').strip() or None,
            effective_date=parse_date(request.form.get('effective_date')),
            requires_acknowledgement=bool(request.form.get('requires_acknowledgement')),
            is_published=bool(request.form.get('is_published')),
            is_featured=bool(request.form.get('is_featured')),
            author_id=current_user.id
        )
        db.session.add(article)
        db.session.flush()
        saved = save_article_attachments(article)
        db.session.commit()
        flash(f'Article created{" with " + str(saved) + " attachment(s)" if saved else ""}.', 'success')
        return redirect(url_for('knowledge.detail', article_id=article.id))
    return render_template('knowledge/create.html', article_types=ARTICLE_TYPES)


@knowledge.route('/<int:article_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(article_id):
    if not current_user.can_manage_helpdesk:
        flash('Access denied.', 'danger')
        return redirect(url_for('knowledge.list'))
    article = KnowledgeArticle.query.get_or_404(article_id)
    if request.method == 'POST':
        article.title = request.form.get('title', '').strip()
        article.article_type = request.form.get('article_type') or 'how_to'
        article.summary = request.form.get('summary', '').strip() or None
        article.content = request.form.get('content', '').strip()
        article.category = request.form.get('category', '').strip() or None
        article.tags = request.form.get('tags', '').strip() or None
        article.visibility = request.form.get('visibility') or 'all'
        article.review_date = parse_date(request.form.get('review_date'))
        article.policy_version = request.form.get('policy_version', '').strip() or None
        article.effective_date = parse_date(request.form.get('effective_date'))
        article.requires_acknowledgement = bool(request.form.get('requires_acknowledgement'))
        article.is_published = bool(request.form.get('is_published'))
        article.is_featured = bool(request.form.get('is_featured'))
        saved = save_article_attachments(article)
        db.session.commit()
        flash(f'Article updated{" with " + str(saved) + " new attachment(s)" if saved else ""}.', 'success')
        return redirect(url_for('knowledge.detail', article_id=article.id))
    return render_template('knowledge/edit.html', article=article, article_types=ARTICLE_TYPES)


@knowledge.route('/<int:article_id>/delete', methods=['POST'])
@login_required
def delete(article_id):
    if not current_user.can_manage_system:
        flash('Access denied.', 'danger')
        return redirect(url_for('knowledge.list'))
    article = KnowledgeArticle.query.get_or_404(article_id)
    db.session.delete(article)
    db.session.commit()
    flash('Article deleted.', 'success')
    return redirect(url_for('knowledge.list'))


@knowledge.route('/<int:article_id>/feedback', methods=['POST'])
@login_required
def feedback(article_id):
    article = KnowledgeArticle.query.get_or_404(article_id)
    if not article.is_published and not current_user.can_manage_helpdesk:
        flash('Article is not published.', 'warning')
        return redirect(url_for('knowledge.list'))
    vote = request.form.get('vote')
    if vote == 'helpful':
        article.helpful_count = (article.helpful_count or 0) + 1
        flash('Thanks for the feedback.', 'success')
    elif vote == 'not_helpful':
        article.not_helpful_count = (article.not_helpful_count or 0) + 1
        flash('Thanks. We will improve this article.', 'info')
    db.session.commit()
    return redirect(url_for('knowledge.detail', article_id=article.id))


@knowledge.route('/<int:article_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge(article_id):
    article = KnowledgeArticle.query.get_or_404(article_id)
    if not can_view_article(article):
        abort(403)
    if not article.requires_acknowledgement:
        flash('This article does not require acknowledgement.', 'info')
        return redirect(url_for('knowledge.detail', article_id=article.id))
    acknowledgement = KnowledgeAcknowledgement.query.filter_by(
        article_id=article.id,
        user_id=current_user.id,
    ).first()
    if acknowledgement:
        acknowledgement.policy_version = article.policy_version
    else:
        acknowledgement = KnowledgeAcknowledgement(
            article_id=article.id,
            user_id=current_user.id,
            policy_version=article.policy_version,
        )
        db.session.add(acknowledgement)
    db.session.commit()
    flash('Policy acknowledgement recorded.', 'success')
    return redirect(url_for('knowledge.detail', article_id=article.id))


@knowledge.route('/attachments/<int:attachment_id>/download')
@login_required
def download_attachment(attachment_id):
    attachment = KnowledgeAttachment.query.get_or_404(attachment_id)
    if not can_view_article(attachment.article):
        abort(403)
    folder = article_upload_folder(attachment.article_id)
    return send_from_directory(
        folder,
        attachment.stored_filename,
        as_attachment=True,
        download_name=attachment.original_filename,
    )


@knowledge.route('/attachments/<int:attachment_id>/delete', methods=['POST'])
@login_required
def delete_attachment(attachment_id):
    attachment = KnowledgeAttachment.query.get_or_404(attachment_id)
    article_id = attachment.article_id
    if not current_user.can_manage_helpdesk:
        flash('Access denied.', 'danger')
        return redirect(url_for('knowledge.detail', article_id=article_id))
    path = os.path.join(article_upload_folder(article_id), attachment.stored_filename)
    if os.path.exists(path):
        os.remove(path)
    db.session.delete(attachment)
    db.session.commit()
    flash('Attachment deleted.', 'success')
    return redirect(url_for('knowledge.edit', article_id=article_id))
