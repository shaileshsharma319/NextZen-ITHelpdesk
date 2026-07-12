from app import db
from datetime import datetime

class TicketReply(db.Model):
    __tablename__ = 'ticket_replies'

    id             = db.Column(db.Integer, primary_key=True)
    ticket_id      = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    reply_type     = db.Column(db.Enum('public', 'internal', 'email'), default='public', nullable=False)
    message        = db.Column(db.Text, nullable=False)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    is_public      = db.Column(db.Boolean, default=True)
    attachment_path= db.Column(db.String(255), nullable=True)

    author = db.relationship('User', backref='replies', lazy=True)

    def __repr__(self):
        return f'<TicketReply {self.id}>'


class TicketActivity(db.Model):
    __tablename__ = 'ticket_activities'

    id          = db.Column(db.Integer, primary_key=True)
    ticket_id   = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    actor = db.relationship('User', backref='activities', lazy=True)

    def __repr__(self):
        return f'<TicketActivity {self.id}>'


class TicketAttachment(db.Model):
    __tablename__ = 'ticket_attachments'

    id                = db.Column(db.Integer, primary_key=True)
    ticket_id         = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    reply_id          = db.Column(db.Integer, db.ForeignKey('ticket_replies.id'), nullable=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename   = db.Column(db.String(255), nullable=False)
    content_type      = db.Column(db.String(120), nullable=True)
    file_size         = db.Column(db.Integer, nullable=True)
    uploaded_by       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)

    ticket = db.relationship('Ticket', backref=db.backref('attachments', lazy=True, cascade='all, delete-orphan'))
    reply = db.relationship('TicketReply', backref=db.backref('attachments', lazy=True, cascade='all, delete-orphan'))
    uploader = db.relationship('User', backref='ticket_attachments', lazy=True)

    @property
    def size_label(self):
        if not self.file_size:
            return 'Unknown size'
        if self.file_size < 1024:
            return f'{self.file_size} B'
        if self.file_size < 1024 * 1024:
            return f'{self.file_size / 1024:.1f} KB'
        return f'{self.file_size / (1024 * 1024):.1f} MB'

    def __repr__(self):
        return f'<TicketAttachment {self.original_filename}>'


class TicketReplyTemplate(db.Model):
    __tablename__ = 'ticket_reply_templates'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    category    = db.Column(db.String(80), nullable=True)
    body        = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)
    is_active   = db.Column(db.Boolean, default=True)
    created_by  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = db.relationship('User', backref='reply_templates', lazy=True)

    def __repr__(self):
        return f'<TicketReplyTemplate {self.name}>'
