from app import db
from datetime import datetime

class KnowledgeArticle(db.Model):
    __tablename__ = 'knowledge_articles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    article_type = db.Column(db.String(60), default='how_to', nullable=False)
    summary = db.Column(db.String(300), nullable=True)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100))
    tags = db.Column(db.String(255), nullable=True)
    visibility = db.Column(db.String(30), default='all', nullable=False)
    review_date = db.Column(db.Date, nullable=True)
    policy_version = db.Column(db.String(40), nullable=True)
    effective_date = db.Column(db.Date, nullable=True)
    requires_acknowledgement = db.Column(db.Boolean, default=False, nullable=False)
    is_published = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0, nullable=False)
    helpful_count = db.Column(db.Integer, default=0, nullable=False)
    not_helpful_count = db.Column(db.Integer, default=0, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship('User', backref='articles', lazy=True)

    def __repr__(self):
        return f'<KnowledgeArticle {self.title}>'


class KnowledgeAttachment(db.Model):
    __tablename__ = 'knowledge_attachments'

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('knowledge_articles.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(120), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    article = db.relationship('KnowledgeArticle', backref=db.backref('attachments', lazy=True, cascade='all, delete-orphan'))
    uploader = db.relationship('User', backref='knowledge_attachments', lazy=True)


class KnowledgeAcknowledgement(db.Model):
    __tablename__ = 'knowledge_acknowledgements'
    __table_args__ = (
        db.UniqueConstraint('article_id', 'user_id', name='uq_knowledge_ack_article_user'),
    )

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('knowledge_articles.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    policy_version = db.Column(db.String(40), nullable=True)
    acknowledged_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    article = db.relationship('KnowledgeArticle', backref=db.backref('acknowledgements', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref='knowledge_acknowledgements', lazy=True)
