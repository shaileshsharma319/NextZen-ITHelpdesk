from app import db
from datetime import datetime

class Asset(db.Model):
    __tablename__ = 'assets'

    id = db.Column(db.Integer, primary_key=True)

    # Basic Info
    site_name            = db.Column(db.String(150))
    asset_tag            = db.Column(db.String(50), unique=True, nullable=False)
    name                 = db.Column(db.String(150), nullable=False)
    asset_type           = db.Column(db.Enum('computer','monitor','printer','phone','server','network','other'), nullable=False)
    status               = db.Column(db.Enum('available','in_use','under_repair','retired'), default='available', nullable=False)

    # Network
    hostname             = db.Column(db.String(100))
    ip_address           = db.Column(db.String(45))

    # People
    team_leader          = db.Column(db.String(100))
    previous_users       = db.Column(db.String(255))
    designation          = db.Column(db.String(100))

    # CPU
    cpu_model            = db.Column(db.String(150))
    cpu_serial           = db.Column(db.String(100))

    # Motherboard
    motherboard          = db.Column(db.String(150))

    # Storage
    ssd_model            = db.Column(db.String(150))
    internal_hdd         = db.Column(db.String(100))

    # OS
    operating_system     = db.Column(db.String(100))

    # Asset Serials
    full_serial_number   = db.Column(db.String(150))

    # RAM
    ram_details          = db.Column(db.String(100))
    ram_type             = db.Column(db.String(50))

    # Peripherals
    monitor_model        = db.Column(db.String(150))
    mouse_model          = db.Column(db.String(150))
    keyboard_model       = db.Column(db.String(150))

    # Remarks
    remarks              = db.Column(db.Text)

    # Legacy fields
    brand                = db.Column(db.String(100))
    model                = db.Column(db.String(100))
    serial_number        = db.Column(db.String(100))
    purchase_date        = db.Column(db.Date)
    warranty_expiry      = db.Column(db.Date)
    notes                = db.Column(db.Text)

    department_id        = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    assigned_user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    created_at           = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at           = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tickets              = db.relationship('Ticket', backref='asset', lazy=True)

    def __repr__(self):
        return f'<Asset {self.asset_tag}: {self.name}>'
