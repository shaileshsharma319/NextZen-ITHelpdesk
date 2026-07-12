from datetime import datetime

from app import db


class AssignmentRule(db.Model):
    __tablename__ = 'assignment_rules'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    priority_order = db.Column(db.Integer, default=100, nullable=False)

    match_source = db.Column(db.String(40), nullable=True)
    match_ticket_type = db.Column(db.String(40), nullable=True)
    match_priority = db.Column(db.String(40), nullable=True)
    match_category = db.Column(db.String(100), nullable=True)
    match_support_group = db.Column(db.String(100), nullable=True)
    keywords = db.Column(db.String(500), nullable=True)

    assign_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    set_support_group = db.Column(db.String(100), nullable=True)
    set_priority = db.Column(db.String(40), nullable=True)
    set_status = db.Column(db.String(40), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignee = db.relationship('User', foreign_keys=[assign_to])

    def __repr__(self):
        return f'<AssignmentRule {self.id}: {self.name}>'
