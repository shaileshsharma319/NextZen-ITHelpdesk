from app import db
from datetime import datetime

class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(32), unique=True, nullable=True)  # e.g. MUM-HD-EM-20260711000123
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    ticket_type = db.Column(db.Enum('incident', 'request', 'problem', 'change'), default='incident', nullable=False)
    priority = db.Column(db.Enum('low', 'medium', 'high', 'critical'), default='medium', nullable=False)
    status = db.Column(db.Enum('open', 'in_progress', 'pending', 'resolved', 'closed'), default='open', nullable=False)
    category = db.Column(db.String(100))
    tags = db.Column(db.String(255), nullable=True)
    source = db.Column(db.Enum('manual', 'email', 'phone', 'walk_in', 'self_service'), default='manual', nullable=False)
    sub_category = db.Column(db.String(100), nullable=True)
    impact = db.Column(db.Enum('low', 'medium', 'high'), default='medium', nullable=False)
    urgency = db.Column(db.Enum('low', 'medium', 'high'), default='medium', nullable=False)
    support_group = db.Column(db.String(100), nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    software_id = db.Column(db.Integer, db.ForeignKey('software.id'), nullable=True)
    # Email-specific fields
    email_message_id = db.Column(db.String(255), nullable=True)
    email_from = db.Column(db.String(255), nullable=True)
    email_to = db.Column(db.String(255), nullable=True)
    email_cc = db.Column(db.String(500), nullable=True)
    email_subject = db.Column(db.String(255), nullable=True)
    parent_ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=True)
    is_auto_generated = db.Column(db.Boolean, default=False)
    sla_due = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent_ticket = db.relationship('Ticket', remote_side='Ticket.id', backref='child_tickets', foreign_keys=[parent_ticket_id])
    software      = db.relationship('Software', backref='tickets', lazy=True, foreign_keys=[software_id])

    comments   = db.relationship('Comment', backref='ticket', lazy=True, cascade='all, delete-orphan')
    replies    = db.relationship('TicketReply', backref='ticket', lazy=True, cascade='all, delete-orphan',
                                 primaryjoin='Ticket.id == foreign(TicketReply.ticket_id)')
    activities = db.relationship('TicketActivity', backref='ticket', lazy=True, cascade='all, delete-orphan',
                                 primaryjoin='Ticket.id == foreign(TicketActivity.ticket_id)',
                                 order_by='TicketActivity.created_at')

    @property
    def is_overdue(self):
        if self.sla_due and self.status not in ('resolved', 'closed'):
            return datetime.utcnow() > self.sla_due
        return False

    def __repr__(self):
        return f'<Ticket {self.id}: {self.title}>'
