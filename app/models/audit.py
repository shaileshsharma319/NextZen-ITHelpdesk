from datetime import datetime

from app import db


class AuditPolicy(db.Model):
    __tablename__ = 'audit_policies'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(80), nullable=True)
    risk_level = db.Column(db.String(20), default='medium', nullable=False)
    status = db.Column(db.String(20), default='active', nullable=False)
    version = db.Column(db.String(30), default='1.0', nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    description = db.Column(db.Text, nullable=True)
    scope = db.Column(db.Text, nullable=True)
    controls = db.Column(db.Text, nullable=True)
    effective_date = db.Column(db.Date, nullable=True)
    review_date = db.Column(db.Date, nullable=True)
    requires_acknowledgement = db.Column(db.Boolean, default=False, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship('User', foreign_keys=[owner_id], backref='owned_audit_policies', lazy=True)
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_audit_policies', lazy=True)

    @property
    def is_review_due(self):
        from datetime import date
        return bool(self.review_date and self.review_date <= date.today())

    def acknowledgement_is_current(self, acknowledgement):
        if not acknowledgement:
            return False
        if acknowledgement.policy_version != self.version:
            return False
        if self.updated_at and acknowledgement.acknowledged_at < self.updated_at:
            return False
        return True


class AuditPolicyAcknowledgement(db.Model):
    __tablename__ = 'audit_policy_acknowledgements'
    __table_args__ = (
        db.UniqueConstraint('policy_id', 'user_id', name='uq_audit_policy_ack_policy_user'),
    )

    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('audit_policies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    policy_version = db.Column(db.String(30), nullable=True)
    acknowledged_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    policy = db.relationship('AuditPolicy', backref=db.backref('acknowledgements', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref='audit_policy_acknowledgements', lazy=True)


class AuditPolicyAttachment(db.Model):
    __tablename__ = 'audit_policy_attachments'

    id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('audit_policies.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(120), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    policy = db.relationship('AuditPolicy', backref=db.backref('attachments', lazy=True, cascade='all, delete-orphan'))
    uploader = db.relationship('User', backref='audit_policy_attachments', lazy=True)

    @property
    def is_image(self):
        return (self.content_type or '').startswith('image/')


class AuditPlan(db.Model):
    __tablename__ = 'audit_plans'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    audit_type = db.Column(db.String(40), default='internal', nullable=False)
    status = db.Column(db.String(30), default='planned', nullable=False)
    policy_id = db.Column(db.Integer, db.ForeignKey('audit_policies.id'), nullable=True)
    auditor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    scope = db.Column(db.Text, nullable=True)
    scheduled_date = db.Column(db.Date, nullable=True)
    completed_date = db.Column(db.Date, nullable=True)
    score = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    policy = db.relationship('AuditPolicy', backref='audits', lazy=True)
    auditor = db.relationship('User', foreign_keys=[auditor_id], backref='assigned_audits', lazy=True)
    department = db.relationship('Department', backref='audit_plans', lazy=True)
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_audits', lazy=True)


class AuditFinding(db.Model):
    __tablename__ = 'audit_findings'

    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey('audit_plans.id'), nullable=False)
    policy_id = db.Column(db.Integer, db.ForeignKey('audit_policies.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    severity = db.Column(db.String(20), default='medium', nullable=False)
    status = db.Column(db.String(30), default='open', nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    description = db.Column(db.Text, nullable=True)
    recommendation = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    audit = db.relationship('AuditPlan', backref=db.backref('findings', lazy=True, cascade='all, delete-orphan'))
    policy = db.relationship('AuditPolicy', backref='findings', lazy=True)
    owner = db.relationship('User', backref='audit_findings', lazy=True)

    @property
    def is_overdue(self):
        from datetime import date
        return self.status not in ('closed', 'accepted') and bool(self.due_date and self.due_date < date.today())


class AuditCorrectiveAction(db.Model):
    __tablename__ = 'audit_corrective_actions'

    id = db.Column(db.Integer, primary_key=True)
    finding_id = db.Column(db.Integer, db.ForeignKey('audit_findings.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(30), default='open', nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    finding = db.relationship('AuditFinding', backref=db.backref('actions', lazy=True, cascade='all, delete-orphan'))
    owner = db.relationship('User', backref='audit_corrective_actions', lazy=True)
