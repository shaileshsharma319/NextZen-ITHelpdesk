from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    # Identity
    employee_id = db.Column(db.String(20), unique=True, nullable=True)
    first_name = db.Column(db.String(60), nullable=True)
    last_name = db.Column(db.String(60), nullable=True)
    name = db.Column(db.String(100), nullable=False)  # full name / backward compat
    username = db.Column(db.String(60), unique=True, nullable=True)

    # Contact
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    company_domain = db.Column(db.String(120), nullable=True)

    # Employment
    designation = db.Column(db.String(100), nullable=True)
    reporting_manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    date_of_joining = db.Column(db.Date, nullable=True)
    employment_type = db.Column(db.String(40), nullable=True)
    work_state = db.Column(db.String(120), nullable=True)
    work_location = db.Column(db.String(120), nullable=True)
    state_code = db.Column(db.String(8), nullable=True)
    location_code = db.Column(db.String(8), nullable=True)
    branch = db.Column(db.String(120), nullable=True)
    cost_center = db.Column(db.String(80), nullable=True)
    grade = db.Column(db.String(60), nullable=True)
    shift = db.Column(db.String(80), nullable=True)
    probation_end_date = db.Column(db.Date, nullable=True)
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    emergency_contact_phone = db.Column(db.String(30), nullable=True)

    # Account
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum('master_admin', 'admin_staff', 'hr_admin', 'hr_staff', 'user'), default='user', nullable=False)
    _is_active = db.Column('is_active', db.Boolean, default=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    allow_helpdesk_admin = db.Column(db.Boolean, default=False, nullable=False)
    allow_inventory = db.Column(db.Boolean, default=False, nullable=False)
    allow_licenses = db.Column(db.Boolean, default=False, nullable=False)
    allow_compliance = db.Column(db.Boolean, default=False, nullable=False)
    two_factor_required = db.Column(db.Boolean, default=False, nullable=False)
    two_factor_enabled = db.Column(db.Boolean, default=False, nullable=False)
    two_factor_secret = db.Column(db.String(64), nullable=True)
    two_factor_backup_codes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    reporting_manager = db.relationship('User', foreign_keys=[reporting_manager_id], remote_side='User.id', backref='subordinates')

    tickets_created = db.relationship('Ticket', foreign_keys='Ticket.user_id', backref='creator', lazy=True)
    tickets_assigned = db.relationship('Ticket', foreign_keys='Ticket.assigned_to', backref='assignee', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    assets = db.relationship('Asset', backref='assigned_user', lazy=True)

    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        self._is_active = value

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def role_label(self):
        labels = {
            'master_admin': 'System Owner',
            'admin_staff': 'Admin',
            'hr_admin': 'Admin',
            'hr_staff': 'Basic User',
            'user': 'Basic User',
        }
        return labels.get(self.role, self.role.title())

    @property
    def department_key(self):
        name = (self.department.name if self.department else '').strip().lower()
        if not name:
            return ''
        if 'human' in name or name == 'hr' or 'hr ' in f'{name} ' or 'hrms' in name:
            return 'hr'
        if 'information technology' in name or name == 'it' or 'it ' in f'{name} ' or 'technical' in name:
            return 'it'
        if 'account' in name:
            return 'account'
        if 'finance' in name or 'finence' in name:
            return 'finance'
        if 'sales' in name or 'business development' in name:
            return 'sales'
        if 'office admin' in name or name == 'office' or name == 'admin' or 'administration' in name:
            return 'office_admin'
        return name.replace(' ', '_')

    @property
    def access_level_label(self):
        if self.role == 'master_admin':
            return 'System'
        if self.role in ('admin_staff', 'hr_admin'):
            return 'Admin'
        return 'Basic'

    @property
    def is_department_admin(self):
        return self.role in ('master_admin', 'admin_staff', 'hr_admin')

    @property
    def can_manage_users(self):
        return self.can_manage_system or (
            self.department_key == 'hr' and self.is_department_admin
        ) or self.role == 'hr_admin'

    @property
    def can_manage_user_accounts(self):
        return self.can_manage_users or (
            self.department_key == 'it' and self.is_department_admin
        )

    @property
    def can_manage_hrms(self):
        return False

    @property
    def can_view_all_tickets(self):
        return self.can_manage_system or (
            self.department_key in ('it', 'it_support') and self.is_department_admin
        ) or (self.role == 'admin_staff' and self.department_key == '')

    @property
    def can_manage_helpdesk(self):
        return self.can_view_all_tickets or self.allow_helpdesk_admin

    @property
    def can_manage_inventory(self):
        return self.can_manage_system or self.allow_inventory or (
            self.department_key in ('it', 'it_support') and self.is_department_admin
        ) or (self.role == 'admin_staff' and self.department_key == '')

    @property
    def can_manage_compliance(self):
        return self.can_manage_system or self.allow_compliance or (
            self.department_key == 'it' and self.is_department_admin
        )

    @property
    def can_manage_licenses(self):
        return self.can_manage_system or self.allow_licenses or self.can_manage_inventory

    @property
    def can_manage_system(self):
        return self.role == 'master_admin'

    @property
    def is_agent(self):
        return self.can_manage_helpdesk

    def __repr__(self):
        return f'<User {self.email}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
