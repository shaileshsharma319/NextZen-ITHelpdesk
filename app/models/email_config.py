from app import db
from datetime import datetime

class EmailConfig(db.Model):
    __tablename__ = 'email_config'

    id           = db.Column(db.Integer, primary_key=True)
    mail_server  = db.Column(db.String(120), nullable=False)
    mail_port    = db.Column(db.Integer, default=587)
    mail_use_tls = db.Column(db.Boolean, default=True)
    mail_use_ssl = db.Column(db.Boolean, default=False)
    mail_username = db.Column(db.String(120), nullable=False)
    mail_password = db.Column(db.String(255), nullable=False)
    mail_from    = db.Column(db.String(120), nullable=False)   # default sender
    mail_from_name = db.Column(db.String(100), default='IT HelpDesk')
    # Notification toggles
    notify_ticket_created  = db.Column(db.Boolean, default=True)
    notify_ticket_updated  = db.Column(db.Boolean, default=True)
    notify_ticket_assigned = db.Column(db.Boolean, default=True)
    notify_email_ticket    = db.Column(db.Boolean, default=True)  # notify on email-source ticket
    # CC all notifications to this address
    notify_cc = db.Column(db.String(255), nullable=True)

    # Outbound signature
    signature_enabled = db.Column(db.Boolean, default=True)
    auto_insert_signature = db.Column(db.Boolean, default=True)
    signature_html = db.Column(db.Text, nullable=True)

    # Inbound email / auto-ticket settings
    inbound_enabled = db.Column(db.Boolean, default=False)
    imap_server = db.Column(db.String(120), nullable=True)
    imap_port = db.Column(db.Integer, default=993)
    imap_use_ssl = db.Column(db.Boolean, default=True)
    imap_username = db.Column(db.String(120), nullable=True)
    imap_password = db.Column(db.String(255), nullable=True)
    imap_folder = db.Column(db.String(80), default='INBOX')
    imap_last_uid = db.Column(db.Integer, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get():
        return EmailConfig.query.first()
