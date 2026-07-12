from datetime import datetime
from app import db


class UserSignature(db.Model):
    __tablename__ = 'user_signatures'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    signature_enabled = db.Column(db.Boolean, default=True)
    auto_insert_signature = db.Column(db.Boolean, default=True)
    signature_html = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('signature_settings', uselist=False))

    @staticmethod
    def for_user(user):
        signature = UserSignature.query.filter_by(user_id=user.id).first()
        if signature:
            return signature
        signature = UserSignature(user_id=user.id)
        db.session.add(signature)
        db.session.flush()
        return signature
