from datetime import datetime, date

from app import db


class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    leave_type = db.Column(db.String(40), default='casual', nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days = db.Column(db.Numeric(5, 1), nullable=False, default=1)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    decision_note = db.Column(db.Text, nullable=True)
    decided_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('User', foreign_keys=[user_id], backref='leave_requests')
    approver = db.relationship('User', foreign_keys=[approver_id])

    @property
    def date_range_label(self):
        if self.start_date == self.end_date:
            return self.start_date.strftime('%d %b %Y')
        return f'{self.start_date.strftime("%d %b %Y")} - {self.end_date.strftime("%d %b %Y")}'


class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    attendance_date = db.Column(db.Date, default=date.today, nullable=False)
    check_in = db.Column(db.Time, nullable=True)
    check_out = db.Column(db.Time, nullable=True)
    status = db.Column(db.String(20), default='present', nullable=False)
    work_mode = db.Column(db.String(30), default='office', nullable=True)
    remarks = db.Column(db.String(255), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('User', foreign_keys=[user_id], backref='attendance_records')
    creator = db.relationship('User', foreign_keys=[created_by_id])


class Holiday(db.Model):
    __tablename__ = 'holidays'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    holiday_date = db.Column(db.Date, nullable=False)
    holiday_type = db.Column(db.String(40), default='public', nullable=False)
    location = db.Column(db.String(120), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by_id])


class ReimbursementClaim(db.Model):
    __tablename__ = 'reimbursement_claims'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expense_date = db.Column(db.Date, default=date.today, nullable=False)
    category = db.Column(db.String(60), default='travel', nullable=False)
    merchant = db.Column(db.String(120), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(10), default='INR', nullable=False)
    payment_method = db.Column(db.String(40), nullable=True)
    description = db.Column(db.Text, nullable=True)
    receipt_filename = db.Column(db.String(255), nullable=True)
    receipt_original_name = db.Column(db.String(255), nullable=True)
    receipt_mimetype = db.Column(db.String(120), nullable=True)
    receipt_size = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    decision_note = db.Column(db.Text, nullable=True)
    decided_at = db.Column(db.DateTime, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('User', foreign_keys=[user_id], backref='reimbursement_claims')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id])


class PayrollProfile(db.Model):
    __tablename__ = 'payroll_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    annual_ctc = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    flexible_benefit_plan = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    variable_pay = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    basic_percent = db.Column(db.Numeric(5, 2), default=40, nullable=False)
    hra_percent = db.Column(db.Numeric(5, 2), default=20, nullable=False)
    tax_regime = db.Column(db.String(20), default='new', nullable=False)
    pf_enabled = db.Column(db.Boolean, default=True, nullable=False)
    esi_enabled = db.Column(db.Boolean, default=False, nullable=False)
    pt_enabled = db.Column(db.Boolean, default=True, nullable=False)
    pf_number = db.Column(db.String(30), nullable=True)
    uan_number = db.Column(db.String(30), nullable=True)
    esi_number = db.Column(db.String(30), nullable=True)
    eps_number = db.Column(db.String(30), nullable=True)
    pan_number = db.Column(db.String(20), nullable=True)
    bank_name = db.Column(db.String(120), nullable=True)
    bank_account = db.Column(db.String(40), nullable=True)
    ifsc_code = db.Column(db.String(20), nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('User', foreign_keys=[user_id], backref=db.backref('payroll_profile', uselist=False))
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])

    @property
    def monthly_ctc(self):
        return (self.annual_ctc or 0) / 12

    @property
    def estimated_taxable_income(self):
        declarations = sum((item.approved_amount or 0) for item in self.employee.investment_declarations if item.status == 'approved')
        standard_deduction = 50000
        if self.tax_regime == 'old':
            return max((self.annual_ctc or 0) - declarations - standard_deduction, 0)
        return max((self.annual_ctc or 0) - standard_deduction, 0)


class StatutoryComponent(db.Model):
    __tablename__ = 'statutory_components'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    component_type = db.Column(db.String(30), default='deduction', nullable=False)
    code = db.Column(db.String(30), nullable=False, unique=True)
    formula = db.Column(db.String(255), nullable=False)
    applies_to = db.Column(db.String(80), default='all', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by_id])


class InvestmentDeclaration(db.Model):
    __tablename__ = 'investment_declarations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    financial_year = db.Column(db.String(9), nullable=False)
    section = db.Column(db.String(40), default='80C', nullable=False)
    description = db.Column(db.String(180), nullable=True)
    declared_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    approved_amount = db.Column(db.Numeric(12, 2), nullable=True)
    proof_filename = db.Column(db.String(255), nullable=True)
    proof_original_name = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='submitted', nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    decision_note = db.Column(db.Text, nullable=True)
    decided_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('User', foreign_keys=[user_id], backref='investment_declarations')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id])


class LoanAdvance(db.Model):
    __tablename__ = 'loan_advances'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    request_type = db.Column(db.String(30), default='advance', nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    repayment_months = db.Column(db.Integer, default=1, nullable=False)
    purpose = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    decision_note = db.Column(db.Text, nullable=True)
    decided_at = db.Column(db.DateTime, nullable=True)
    disbursed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('User', foreign_keys=[user_id], backref='loan_advances')
    approver = db.relationship('User', foreign_keys=[approver_id])

    @property
    def emi_amount(self):
        if not self.repayment_months:
            return self.amount
        return (self.amount or 0) / self.repayment_months


class BiometricLog(db.Model):
    __tablename__ = 'biometric_logs'

    id = db.Column(db.Integer, primary_key=True)
    employee_code = db.Column(db.String(40), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    device_name = db.Column(db.String(120), nullable=True)
    punch_time = db.Column(db.DateTime, nullable=False)
    punch_type = db.Column(db.String(20), default='in', nullable=False)
    sync_source = db.Column(db.String(80), default='manual', nullable=False)
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False, nullable=False)

    employee = db.relationship('User', foreign_keys=[user_id], backref='biometric_logs')


class EmployeeProfile(db.Model):
    __tablename__ = 'employee_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(30), nullable=True)
    marital_status = db.Column(db.String(30), nullable=True)
    personal_email = db.Column(db.String(120), nullable=True)
    blood_group = db.Column(db.String(10), nullable=True)
    address_line1 = db.Column(db.String(180), nullable=True)
    address_line2 = db.Column(db.String(180), nullable=True)
    city = db.Column(db.String(80), nullable=True)
    state = db.Column(db.String(80), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(80), default='India', nullable=True)
    mobile_app_enabled = db.Column(db.Boolean, default=False, nullable=False)
    mobile_device_id = db.Column(db.String(120), nullable=True)
    mobile_last_login = db.Column(db.DateTime, nullable=True)
    other_info = db.Column(db.Text, nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('User', foreign_keys=[user_id], backref=db.backref('employee_profile', uselist=False))
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])


class EmployeeDocument(db.Model):
    __tablename__ = 'employee_documents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_type = db.Column(db.String(60), default='certificate', nullable=False)
    title = db.Column(db.String(160), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    mimetype = db.Column(db.String(120), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship('User', foreign_keys=[user_id], backref='employee_documents')
    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id])


class EmployeeSalaryHistory(db.Model):
    __tablename__ = 'employee_salary_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    annual_ctc = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    flexible_benefit_plan = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    variable_pay = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    effective_from = db.Column(db.Date, default=date.today, nullable=False)
    change_reason = db.Column(db.String(180), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship('User', foreign_keys=[user_id], backref='salary_history')
    created_by = db.relationship('User', foreign_keys=[created_by_id])


class EmployeeSalaryComponent(db.Model):
    __tablename__ = 'employee_salary_components'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    component_group = db.Column(db.String(30), default='ctc', nullable=False)
    is_fbp = db.Column(db.Boolean, default=False, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('User', foreign_keys=[user_id], backref='salary_components')
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
