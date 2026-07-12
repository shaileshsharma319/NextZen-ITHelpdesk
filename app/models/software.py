from app import db
from datetime import datetime

class Software(db.Model):
    __tablename__ = 'software'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    version = db.Column(db.String(50))
    vendor = db.Column(db.String(100))
    category = db.Column(db.Enum('os', 'office', 'security', 'development', 'design', 'communication', 'utility', 'other'), default='other', nullable=False)
    license_type = db.Column(db.Enum('free', 'open_source', 'commercial', 'subscription', 'trial'), default='commercial', nullable=False)
    license_edition = db.Column(db.Enum('msdn', 'oem_pro', 'oem_sl', 'retail', 'volume', 'other'), nullable=True)
    license_key = db.Column(db.String(255))
    license_seats = db.Column(db.Integer, default=1)
    license_expiry = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    installations = db.relationship('SoftwareInstallation', backref='software', lazy=True, cascade='all, delete-orphan')

    @property
    def installed_count(self):
        return len(self.installations)

    @property
    def seats(self):
        return self.license_seats or 1

    @property
    def is_license_expired(self):
        if self.license_expiry:
            return datetime.utcnow().date() > self.license_expiry
        return False

    def __repr__(self):
        return f'<Software {self.name} {self.version}>'


class SoftwareInstallation(db.Model):
    __tablename__ = 'software_installations'

    id = db.Column(db.Integer, primary_key=True)
    software_id = db.Column(db.Integer, db.ForeignKey('software.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    installed_date = db.Column(db.Date, nullable=True)
    installed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    asset = db.relationship('Asset', backref='software_installations', lazy=True)
    installed_by = db.relationship('User', backref='installations', lazy=True)

    def __repr__(self):
        return f'<SoftwareInstallation {self.software_id} on Asset {self.asset_id}>'
