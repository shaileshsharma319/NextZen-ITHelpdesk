import os
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.models.department import Department
from app.models.hrms import (
    AttendanceRecord,
    BiometricLog,
    EmployeeDocument,
    EmployeeProfile,
    EmployeeSalaryComponent,
    EmployeeSalaryHistory,
    Holiday,
    InvestmentDeclaration,
    LeaveRequest,
    LoanAdvance,
    PayrollProfile,
    ReimbursementClaim,
    StatutoryComponent,
)
from app.models.user import User

hrms = Blueprint('hrms', __name__)

ALLOWED_EMPLOYEE_DOCUMENT_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'webp'
}


def hr_can_manage():
    return current_user.can_manage_hrms


def _same_company_user(user):
    if not current_user.company_domain:
        return user.id == current_user.id
    return (user.company_domain or '').lower() == current_user.company_domain.lower()


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_time(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%H:%M').time()
    except ValueError:
        return None


def _parse_amount(value):
    try:
        amount = Decimal(str(value or '').strip())
    except Exception:
        return None
    if amount <= 0:
        return None
    return amount


def _financial_year(today=None):
    today = today or date.today()
    start_year = today.year if today.month >= 4 else today.year - 1
    return f'{start_year}-{str(start_year + 1)[-2:]}'


def _tax_estimate(taxable_income, regime='new'):
    taxable_income = Decimal(str(taxable_income or 0))
    slabs = [
        (Decimal('300000'), Decimal('0.00')),
        (Decimal('300000'), Decimal('0.05')),
        (Decimal('300000'), Decimal('0.10')),
        (Decimal('300000'), Decimal('0.15')),
        (Decimal('300000'), Decimal('0.20')),
        (None, Decimal('0.30')),
    ] if regime == 'new' else [
        (Decimal('250000'), Decimal('0.00')),
        (Decimal('250000'), Decimal('0.05')),
        (Decimal('500000'), Decimal('0.20')),
        (None, Decimal('0.30')),
    ]
    remaining = taxable_income
    tax = Decimal('0')
    for slab_amount, rate in slabs:
        if remaining <= 0:
            break
        taxable_part = remaining if slab_amount is None else min(remaining, slab_amount)
        tax += taxable_part * rate
        remaining -= taxable_part
    return tax + (tax * Decimal('0.04'))


def _profile_for(user):
    profile = PayrollProfile.query.filter_by(user_id=user.id).first()
    if not profile:
        profile = PayrollProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    return profile


def _employee_profile_for(user):
    profile = EmployeeProfile.query.filter_by(user_id=user.id).first()
    if not profile:
        profile = EmployeeProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    return profile


def _employee_document_allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EMPLOYEE_DOCUMENT_EXTENSIONS


def _save_employee_document(employee, upload, document_type, title, notes):
    if not upload or not upload.filename:
        return None
    original = secure_filename(upload.filename)
    if not original or not _employee_document_allowed(original):
        return None
    document = EmployeeDocument(
        user_id=employee.id,
        document_type=document_type or 'certificate',
        title=title or original,
        original_filename=original,
        stored_filename='pending',
        mimetype=upload.mimetype,
        notes=notes or None,
        uploaded_by_id=current_user.id,
    )
    db.session.add(document)
    db.session.flush()
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'hrms_documents', str(employee.id))
    os.makedirs(folder, exist_ok=True)
    stored = f'{uuid4().hex}_{original}'
    path = os.path.join(folder, stored)
    upload.save(path)
    document.stored_filename = stored
    document.file_size = os.path.getsize(path)
    return document


def _salary_changed(profile, annual_ctc, fbp, variable_pay):
    return (
        Decimal(str(profile.annual_ctc or 0)) != annual_ctc
        or Decimal(str(profile.flexible_benefit_plan or 0)) != fbp
        or Decimal(str(profile.variable_pay or 0)) != variable_pay
    )


SALARY_COMPONENT_NAMES = [
    'BASIC',
    'HRA',
    'Conveyance Allowance',
    'Special Allowance',
    'Provident Fund Employer',
    'Gratuity',
    'Labour Welfare Fund Employer',
    'Professional Allowance',
    'Miscellaneous Allowance',
    'Education Allowance',
    'Transport Allowance',
    'Lunch Coupons',
    'Telephone OR Mobile-Phone Bills',
    'Uniform Allowance',
    'NPS Employer Contribution',
    'Medical Reimbursement - Annual',
    'Performance Based Incentive',
    'Medical Reimbursement - Monthly',
    'Annual Bonus',
    'Project Allowance',
    'EDLI Charges',
    'Bonus',
    'Onsite Allowance',
    'Annual Sales Allowance',
    'One Time Bonus',
    'Business Performance Bonus',
]


FBP_COMPONENT_NAMES = {
    'Conveyance Allowance',
    'Education Allowance',
    'Transport Allowance',
    'Lunch Coupons',
    'Telephone OR Mobile-Phone Bills',
    'Uniform Allowance',
    'Medical Reimbursement - Annual',
    'Medical Reimbursement - Monthly',
}


def _money(value):
    return Decimal(str(value or 0)).quantize(Decimal('0.01'))


def _default_salary_components(profile):
    annual_ctc = _money(profile.annual_ctc)
    basic = _money(annual_ctc * Decimal(str(profile.basic_percent or 40)) / Decimal('100'))
    hra = _money(annual_ctc * Decimal(str(profile.hra_percent or 20)) / Decimal('100'))
    pf = min(_money(basic * Decimal('0.12')), Decimal('22500.00')) if profile.pf_enabled else Decimal('0.00')
    gratuity = _money(basic * Decimal('0.0481')) if annual_ctc else Decimal('0.00')
    education = Decimal('2400.00') if annual_ctc else Decimal('0.00')
    edli = Decimal('900.00') if profile.pf_enabled and annual_ctc else Decimal('0.00')
    bonus = Decimal('15000.00') if annual_ctc else Decimal('0.00')
    professional = _money(profile.variable_pay)
    amounts = {
        'BASIC': basic,
        'HRA': hra,
        'Conveyance Allowance': Decimal('0.00'),
        'Provident Fund Employer': pf,
        'Gratuity': gratuity,
        'Labour Welfare Fund Employer': Decimal('0.00'),
        'Professional Allowance': professional,
        'Miscellaneous Allowance': Decimal('0.00'),
        'Education Allowance': education,
        'Transport Allowance': Decimal('0.00'),
        'Lunch Coupons': Decimal('0.00'),
        'Telephone OR Mobile-Phone Bills': Decimal('0.00'),
        'Uniform Allowance': Decimal('0.00'),
        'NPS Employer Contribution': Decimal('0.00'),
        'Medical Reimbursement - Annual': Decimal('0.00'),
        'Performance Based Incentive': Decimal('0.00'),
        'Medical Reimbursement - Monthly': Decimal('0.00'),
        'Annual Bonus': Decimal('0.00'),
        'Project Allowance': Decimal('0.00'),
        'EDLI Charges': edli,
        'Bonus': bonus,
        'Onsite Allowance': Decimal('0.00'),
        'Annual Sales Allowance': Decimal('0.00'),
        'One Time Bonus': Decimal('0.00'),
        'Business Performance Bonus': Decimal('0.00'),
    }
    used = sum(amounts.values(), Decimal('0.00'))
    amounts['Special Allowance'] = max(annual_ctc - used, Decimal('0.00'))
    return [
        {
            'name': name,
            'amount': amounts.get(name, Decimal('0.00')),
            'component_group': 'ctc',
            'is_fbp': name in FBP_COMPONENT_NAMES,
            'sort_order': index + 1,
        }
        for index, name in enumerate(SALARY_COMPONENT_NAMES)
    ]


def _salary_components_for(user, profile):
    rows = EmployeeSalaryComponent.query.filter_by(user_id=user.id).order_by(EmployeeSalaryComponent.sort_order, EmployeeSalaryComponent.name).all()
    if rows:
        return rows
    return _default_salary_components(profile)


def _salary_component_total(components):
    return sum((_money(getattr(item, 'amount', item.get('amount', 0))) for item in components), Decimal('0.00'))


def _salary_component_totals_from_form():
    names = request.form.getlist('component_name[]')
    amounts = request.form.getlist('component_amount[]')
    fbp_names = set(request.form.getlist('component_fbp[]'))
    total = Decimal('0.00')
    fbp_total = Decimal('0.00')
    for index, name in enumerate(names):
        clean_name = (name or '').strip()
        if not clean_name:
            continue
        amount = max(_money(amounts[index] if index < len(amounts) else 0), Decimal('0.00'))
        total += amount
        if clean_name in fbp_names:
            fbp_total += amount
    return total, fbp_total


def _save_salary_components(user):
    names = request.form.getlist('component_name[]')
    amounts = request.form.getlist('component_amount[]')
    groups = request.form.getlist('component_group[]')
    fbp_names = set(request.form.getlist('component_fbp[]'))
    if not names:
        return
    EmployeeSalaryComponent.query.filter_by(user_id=user.id).delete()
    for index, name in enumerate(names):
        clean_name = (name or '').strip()
        if not clean_name:
            continue
        db.session.add(EmployeeSalaryComponent(
            user_id=user.id,
            name=clean_name,
            amount=max(_money(amounts[index] if index < len(amounts) else 0), Decimal('0.00')),
            component_group=(groups[index] if index < len(groups) and groups[index] else 'ctc'),
            is_fbp=clean_name in fbp_names,
            sort_order=index + 1,
            updated_by_id=current_user.id,
        ))


def _employee_directory_key(user):
    if user.employee_id:
        return f'emp:{user.employee_id.strip().lower()}'
    normalized_name = ' '.join((user.name or '').strip().lower().split())
    if normalized_name:
        return f'name:{normalized_name}'
    return f'user:{user.id}'


def _employee_profile_score(user):
    return sum([
        4 if user.employee_id else 0,
        2 if user.designation else 0,
        2 if user.department_id else 0,
        1 if user.phone else 0,
        1 if user.work_location else 0,
        1 if user.reporting_manager_id else 0,
    ])


def _dedupe_employee_directory(users):
    visible = {}
    duplicate_map = {}
    for user in users:
        key = _employee_directory_key(user)
        current = visible.get(key)
        if not current:
            visible[key] = user
            continue
        current_rank = (_employee_profile_score(current), -(current.id or 0))
        user_rank = (_employee_profile_score(user), -(user.id or 0))
        if user_rank > current_rank:
            duplicate_map.setdefault(key, []).append(current)
            visible[key] = user
        else:
            duplicate_map.setdefault(key, []).append(user)
    employees = sorted(visible.values(), key=lambda item: ((item.name or '').lower(), item.id or 0))
    hidden_count = sum(len(items) for items in duplicate_map.values())
    return employees, hidden_count


def _save_reimbursement_receipt(claim, upload):
    if not upload or not upload.filename:
        return
    original = secure_filename(upload.filename)
    if not original:
        return
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reimbursements', str(claim.id))
    os.makedirs(folder, exist_ok=True)
    stored = f'{uuid4().hex}_{original}'
    upload.save(os.path.join(folder, stored))
    claim.receipt_filename = stored
    claim.receipt_original_name = original
    claim.receipt_mimetype = upload.mimetype
    claim.receipt_size = os.path.getsize(os.path.join(folder, stored))


@hrms.route('/')
@login_required
def dashboard():
    employee_query = User.query.filter(db.or_(User.username.is_(None), User.username != 'system_email_requester'))
    if not hr_can_manage():
        employee_query = employee_query.filter(User.id == current_user.id)

    employees = employee_query.count()
    active = employee_query.filter(User._is_active.is_(True)).count()
    pending_leaves = LeaveRequest.query.filter_by(status='pending')
    pending_reimbursements = ReimbursementClaim.query.filter_by(status='pending')
    pending_investments = InvestmentDeclaration.query.filter_by(status='submitted')
    pending_loans = LoanAdvance.query.filter_by(status='pending')
    attendance_today = AttendanceRecord.query.filter_by(attendance_date=date.today())
    if not hr_can_manage():
        pending_leaves = pending_leaves.filter_by(user_id=current_user.id)
        pending_reimbursements = pending_reimbursements.filter_by(user_id=current_user.id)
        pending_investments = pending_investments.filter_by(user_id=current_user.id)
        pending_loans = pending_loans.filter_by(user_id=current_user.id)
        attendance_today = attendance_today.filter_by(user_id=current_user.id)

    recent_leaves = LeaveRequest.query.order_by(LeaveRequest.created_at.desc())
    if not hr_can_manage():
        recent_leaves = recent_leaves.filter_by(user_id=current_user.id)
    recent_leaves = recent_leaves.limit(8).all()
    upcoming_holidays = Holiday.query.filter(Holiday.holiday_date >= date.today()).order_by(Holiday.holiday_date.asc()).limit(5).all()
    active_payroll_profiles = PayrollProfile.query.count() if hr_can_manage() else PayrollProfile.query.filter_by(user_id=current_user.id).count()
    active_statutory_components = StatutoryComponent.query.filter_by(is_active=True).count()
    biometric_logs_today = BiometricLog.query.filter(BiometricLog.punch_time >= datetime.combine(date.today(), datetime.min.time()))
    if not hr_can_manage():
        biometric_logs_today = biometric_logs_today.filter_by(user_id=current_user.id)
    my_profile = _profile_for(current_user)
    taxable_income = my_profile.estimated_taxable_income
    monthly_tax = _tax_estimate(taxable_income, my_profile.tax_regime) / 12

    return render_template(
        'hrms/dashboard.html',
        employees=employees,
        active=active,
        pending_leaves=pending_leaves.count(),
        pending_reimbursements=pending_reimbursements.count(),
        pending_investments=pending_investments.count(),
        pending_loans=pending_loans.count(),
        attendance_today=attendance_today.count(),
        active_payroll_profiles=active_payroll_profiles,
        active_statutory_components=active_statutory_components,
        biometric_logs_today=biometric_logs_today.count(),
        financial_year=_financial_year(),
        taxable_income=taxable_income,
        monthly_tax=monthly_tax,
        recent_leaves=recent_leaves,
        upcoming_holidays=upcoming_holidays,
    )


@hrms.route('/employees')
@login_required
def employees():
    q = request.args.get('q', '').strip()
    department_id = request.args.get('department_id', type=int)
    status = request.args.get('status', '').strip()
    show_duplicates = request.args.get('duplicates') == 'show'

    query = User.query.filter(db.or_(User.username.is_(None), User.username != 'system_email_requester'))
    if not hr_can_manage():
        query = query.filter(User.id == current_user.id)
    if q:
        like_q = f'%{q}%'
        query = query.filter(db.or_(
            User.name.ilike(like_q),
            User.email.ilike(like_q),
            User.employee_id.ilike(like_q),
            User.designation.ilike(like_q),
            User.work_location.ilike(like_q),
        ))
    if department_id:
        query = query.filter(User.department_id == department_id)
    if status == 'active':
        query = query.filter(User._is_active.is_(True))
    elif status == 'inactive':
        query = query.filter(User._is_active.is_(False))
    all_employees = query.order_by(User.name, User.id).all()
    employees = all_employees
    hidden_duplicate_count = 0
    if not show_duplicates:
        employees, hidden_duplicate_count = _dedupe_employee_directory(all_employees)

    return render_template(
        'hrms/employees.html',
        employees=employees,
        total_employee_records=len(all_employees),
        hidden_duplicate_count=hidden_duplicate_count,
        show_duplicates=show_duplicates,
        departments=Department.query.order_by(Department.name).all(),
        q=q,
        department_id=department_id,
        status=status,
    )


@hrms.route('/ess')
@login_required
def ess():
    profile = _profile_for(current_user)
    fy = _financial_year()
    leaves = LeaveRequest.query.filter_by(user_id=current_user.id).order_by(LeaveRequest.created_at.desc()).limit(5).all()
    claims = ReimbursementClaim.query.filter_by(user_id=current_user.id).order_by(ReimbursementClaim.created_at.desc()).limit(5).all()
    investments = InvestmentDeclaration.query.filter_by(user_id=current_user.id, financial_year=fy).order_by(InvestmentDeclaration.created_at.desc()).all()
    loans = LoanAdvance.query.filter_by(user_id=current_user.id).order_by(LoanAdvance.created_at.desc()).limit(5).all()
    attendance = AttendanceRecord.query.filter_by(user_id=current_user.id).order_by(AttendanceRecord.attendance_date.desc()).limit(7).all()
    return render_template(
        'hrms/ess.html',
        profile=profile,
        leaves=leaves,
        claims=claims,
        investments=investments,
        loans=loans,
        attendance=attendance,
        financial_year=fy,
        taxable_income=profile.estimated_taxable_income,
        monthly_tax=_tax_estimate(profile.estimated_taxable_income, profile.tax_regime) / 12,
    )


@hrms.route('/payroll', methods=['GET', 'POST'])
@login_required
def payroll():
    if not hr_can_manage():
        return redirect(url_for('hrms.ess'))
    if request.method == 'POST':
        user = User.query.get_or_404(request.form.get('user_id', type=int))
        profile = _profile_for(user)
        annual_ctc = _parse_amount(request.form.get('annual_ctc')) or Decimal('0')
        fbp = _parse_amount(request.form.get('flexible_benefit_plan')) or Decimal('0')
        variable_pay = _parse_amount(request.form.get('variable_pay')) or Decimal('0')
        if request.form.getlist('component_name[]'):
            annual_ctc, fbp = _salary_component_totals_from_form()
        salary_changed = _salary_changed(profile, annual_ctc, fbp, variable_pay)
        profile.annual_ctc = annual_ctc
        profile.flexible_benefit_plan = fbp
        profile.variable_pay = variable_pay
        profile.basic_percent = _parse_amount(request.form.get('basic_percent')) or Decimal('40')
        profile.hra_percent = _parse_amount(request.form.get('hra_percent')) or Decimal('20')
        profile.tax_regime = request.form.get('tax_regime', 'new')
        profile.pf_enabled = request.form.get('pf_enabled') == 'on'
        profile.esi_enabled = request.form.get('esi_enabled') == 'on'
        profile.pt_enabled = request.form.get('pt_enabled') == 'on'
        profile.pf_number = request.form.get('pf_number', '').strip() or None
        profile.uan_number = request.form.get('uan_number', '').strip() or None
        profile.esi_number = request.form.get('esi_number', '').strip() or None
        profile.eps_number = request.form.get('eps_number', '').strip() or None
        profile.pan_number = request.form.get('pan_number', '').strip() or None
        profile.bank_name = request.form.get('bank_name', '').strip() or None
        profile.bank_account = request.form.get('bank_account', '').strip() or None
        profile.ifsc_code = request.form.get('ifsc_code', '').strip() or None
        profile.updated_by_id = current_user.id
        _save_salary_components(user)
        if salary_changed:
            db.session.add(EmployeeSalaryHistory(
                user_id=user.id,
                annual_ctc=annual_ctc,
                flexible_benefit_plan=fbp,
                variable_pay=variable_pay,
                effective_from=_parse_date(request.form.get('effective_from')) or date.today(),
                change_reason=request.form.get('change_reason', '').strip() or 'Payroll profile update',
                created_by_id=current_user.id,
            ))
        db.session.commit()
        flash('Payroll profile saved.', 'success')
        return redirect(url_for('hrms.payroll', employee_id=user.id))

    employee_id = request.args.get('employee_id', type=int)
    selected_employee = User.query.get(employee_id) if employee_id else User.query.filter(User._is_active.is_(True)).order_by(User.name).first()
    selected_profile = _profile_for(selected_employee) if selected_employee else None
    payroll_rows = PayrollProfile.query.order_by(PayrollProfile.updated_at.desc()).limit(80).all()
    salary_components = _salary_components_for(selected_employee, selected_profile) if selected_employee and selected_profile else []
    return render_template(
        'hrms/payroll.html',
        employees=User.query.filter(User._is_active.is_(True)).order_by(User.name).all(),
        selected_employee=selected_employee,
        selected_profile=selected_profile,
        payroll_rows=payroll_rows,
        salary_components=salary_components,
        salary_component_total=_salary_component_total(salary_components),
        tax_estimate=_tax_estimate(selected_profile.estimated_taxable_income, selected_profile.tax_regime) if selected_profile else 0,
    )


@hrms.route('/compliance', methods=['GET', 'POST'])
@login_required
def compliance():
    if not hr_can_manage():
        flash('Access denied.', 'danger')
        return redirect(url_for('hrms.dashboard'))
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        component = StatutoryComponent.query.filter_by(code=code).first() if code else None
        if not component:
            component = StatutoryComponent(code=code, created_by_id=current_user.id)
            db.session.add(component)
        component.name = request.form.get('name', '').strip()
        component.component_type = request.form.get('component_type', 'deduction')
        component.formula = request.form.get('formula', '').strip()
        component.applies_to = request.form.get('applies_to', 'all').strip() or 'all'
        component.is_active = request.form.get('is_active') == 'on'
        if not component.code or not component.name or not component.formula:
            flash('Code, name, and formula are required.', 'danger')
        else:
            db.session.commit()
            flash('Compliance component saved.', 'success')
        return redirect(url_for('hrms.compliance'))
    return render_template('hrms/compliance.html', components=StatutoryComponent.query.order_by(StatutoryComponent.name).all())


@hrms.route('/investments', methods=['GET', 'POST'])
@login_required
def investments():
    if request.method == 'POST':
        user_id = request.form.get('user_id', type=int) if hr_can_manage() else current_user.id
        amount = _parse_amount(request.form.get('declared_amount'))
        if not user_id or not amount:
            flash('Employee and declared amount are required.', 'danger')
            return redirect(url_for('hrms.investments'))
        declaration = InvestmentDeclaration(
            user_id=user_id,
            financial_year=request.form.get('financial_year', '').strip() or _financial_year(),
            section=request.form.get('section', '80C'),
            description=request.form.get('description', '').strip() or None,
            declared_amount=amount,
        )
        db.session.add(declaration)
        db.session.commit()
        flash('Investment declaration submitted.', 'success')
        return redirect(url_for('hrms.investments'))

    query = InvestmentDeclaration.query.order_by(InvestmentDeclaration.created_at.desc())
    if not hr_can_manage():
        query = query.filter_by(user_id=current_user.id)
    return render_template(
        'hrms/investments.html',
        declarations=query.limit(100).all(),
        employees=User.query.filter(User._is_active.is_(True)).order_by(User.name).all(),
        financial_year=_financial_year(),
    )


@hrms.route('/investments/<int:declaration_id>/decision', methods=['POST'])
@login_required
def investment_decision(declaration_id):
    if not hr_can_manage():
        flash('Access denied.', 'danger')
        return redirect(url_for('hrms.investments'))
    declaration = InvestmentDeclaration.query.get_or_404(declaration_id)
    action = request.form.get('action')
    if action not in ('approved', 'rejected'):
        flash('Invalid decision.', 'danger')
        return redirect(url_for('hrms.investments'))
    declaration.status = action
    declaration.approved_amount = _parse_amount(request.form.get('approved_amount')) if action == 'approved' else Decimal('0')
    declaration.reviewer_id = current_user.id
    declaration.decision_note = request.form.get('decision_note', '').strip() or None
    declaration.decided_at = datetime.utcnow()
    db.session.commit()
    flash(f'Investment declaration {action}.', 'success')
    return redirect(url_for('hrms.investments'))


@hrms.route('/loans', methods=['GET', 'POST'])
@login_required
def loans():
    if request.method == 'POST':
        user_id = request.form.get('user_id', type=int) if hr_can_manage() else current_user.id
        amount = _parse_amount(request.form.get('amount'))
        if not user_id or not amount:
            flash('Employee and amount are required.', 'danger')
            return redirect(url_for('hrms.loans'))
        loan = LoanAdvance(
            user_id=user_id,
            request_type=request.form.get('request_type', 'advance'),
            amount=amount,
            repayment_months=request.form.get('repayment_months', type=int) or 1,
            purpose=request.form.get('purpose', '').strip() or None,
        )
        db.session.add(loan)
        db.session.commit()
        flash('Loan/advance request submitted.', 'success')
        return redirect(url_for('hrms.loans'))
    query = LoanAdvance.query.order_by(LoanAdvance.created_at.desc())
    if not hr_can_manage():
        query = query.filter_by(user_id=current_user.id)
    return render_template('hrms/loans.html', loans=query.limit(100).all(), employees=User.query.filter(User._is_active.is_(True)).order_by(User.name).all())


@hrms.route('/loans/<int:loan_id>/decision', methods=['POST'])
@login_required
def loan_decision(loan_id):
    if not hr_can_manage():
        flash('Access denied.', 'danger')
        return redirect(url_for('hrms.loans'))
    loan = LoanAdvance.query.get_or_404(loan_id)
    action = request.form.get('action')
    if action not in ('approved', 'rejected', 'disbursed'):
        flash('Invalid decision.', 'danger')
        return redirect(url_for('hrms.loans'))
    loan.status = action
    loan.approver_id = current_user.id
    loan.decision_note = request.form.get('decision_note', '').strip() or None
    loan.decided_at = datetime.utcnow()
    if action == 'disbursed':
        loan.disbursed_at = datetime.utcnow()
    db.session.commit()
    flash(f'Loan/advance {action}.', 'success')
    return redirect(url_for('hrms.loans'))


@hrms.route('/biometric', methods=['GET', 'POST'])
@login_required
def biometric():
    if not hr_can_manage():
        flash('Access denied.', 'danger')
        return redirect(url_for('hrms.dashboard'))
    if request.method == 'POST':
        employee_code = request.form.get('employee_code', '').strip()
        punch_time = request.form.get('punch_time', '').strip()
        try:
            parsed_punch = datetime.fromisoformat(punch_time)
        except ValueError:
            parsed_punch = None
        if not employee_code or not parsed_punch:
            flash('Employee code and punch time are required.', 'danger')
            return redirect(url_for('hrms.biometric'))
        user = User.query.filter(db.or_(User.employee_id == employee_code, User.email == employee_code)).first()
        db.session.add(BiometricLog(
            employee_code=employee_code,
            user_id=user.id if user else None,
            device_name=request.form.get('device_name', '').strip() or None,
            punch_time=parsed_punch,
            punch_type=request.form.get('punch_type', 'in'),
            sync_source=request.form.get('sync_source', 'manual'),
        ))
        db.session.commit()
        flash('Biometric log captured.', 'success')
        return redirect(url_for('hrms.biometric'))
    logs = BiometricLog.query.order_by(BiometricLog.punch_time.desc()).limit(100).all()
    return render_template('hrms/biometric.html', logs=logs, now=datetime.utcnow())


@hrms.route('/employees/<int:user_id>')
@login_required
def employee_detail(user_id):
    employee = User.query.get_or_404(user_id)
    if not hr_can_manage():
        if current_user.id != user_id:
            flash('Access denied.', 'danger')
            return redirect(url_for('hrms.employees'))
        hr_profile = _employee_profile_for(employee)
        payroll_profile = _profile_for(employee)
        salary_history = EmployeeSalaryHistory.query.filter_by(user_id=user_id).order_by(EmployeeSalaryHistory.effective_from.desc(), EmployeeSalaryHistory.created_at.desc()).limit(12).all()
        salary_components = _salary_components_for(employee, payroll_profile)
        leaves = LeaveRequest.query.filter_by(user_id=user_id).order_by(LeaveRequest.created_at.desc()).limit(6).all()
        attendance = AttendanceRecord.query.filter_by(user_id=user_id).order_by(AttendanceRecord.attendance_date.desc()).limit(6).all()
        documents = EmployeeDocument.query.filter_by(user_id=user_id).order_by(EmployeeDocument.created_at.desc()).all()
        timeline = [
            ('Joined', employee.date_of_joining, employee.designation or 'Employee record created'),
            ('Probation Ends', employee.probation_end_date, employee.grade or 'Probation milestone'),
        ]
        timeline += [('CTC Changed', item.effective_from, item.change_reason or 'Salary revision') for item in salary_history]
        timeline = sorted([item for item in timeline if item[1]], key=lambda item: item[1], reverse=True)[:10]
        return render_template(
            'hrms/employee_public_detail.html',
            employee=employee,
            hr_profile=hr_profile,
            payroll_profile=payroll_profile,
            salary_components=salary_components,
            salary_component_total=_salary_component_total(salary_components),
            salary_history=salary_history,
            leaves=leaves,
            attendance=attendance,
            documents=documents,
            timeline=timeline,
        )
    hr_profile = _employee_profile_for(employee)
    payroll_profile = _profile_for(employee)
    leaves = LeaveRequest.query.filter_by(user_id=user_id).order_by(LeaveRequest.created_at.desc()).limit(8).all()
    attendance = AttendanceRecord.query.filter_by(user_id=user_id).order_by(AttendanceRecord.attendance_date.desc()).limit(10).all()
    documents = EmployeeDocument.query.filter_by(user_id=user_id).order_by(EmployeeDocument.created_at.desc()).all()
    salary_history = EmployeeSalaryHistory.query.filter_by(user_id=user_id).order_by(EmployeeSalaryHistory.effective_from.desc(), EmployeeSalaryHistory.created_at.desc()).limit(12).all()
    salary_components = _salary_components_for(employee, payroll_profile)
    claims = ReimbursementClaim.query.filter_by(user_id=user_id).order_by(ReimbursementClaim.created_at.desc()).limit(5).all()
    investments = InvestmentDeclaration.query.filter_by(user_id=user_id).order_by(InvestmentDeclaration.created_at.desc()).limit(5).all()
    timeline = [
        ('Joined', employee.date_of_joining, employee.designation or 'Employee record created'),
        ('Probation Ends', employee.probation_end_date, employee.grade or 'Probation milestone'),
    ]
    timeline += [('CTC Changed', item.effective_from, item.change_reason or 'Salary revision') for item in salary_history]
    timeline = sorted([item for item in timeline if item[1]], key=lambda item: item[1], reverse=True)[:10]
    return render_template(
        'hrms/employee_detail.html',
        employee=employee,
        hr_profile=hr_profile,
        payroll_profile=payroll_profile,
        leaves=leaves,
        attendance=attendance,
        documents=documents,
        salary_history=salary_history,
        salary_components=salary_components,
        salary_component_total=_salary_component_total(salary_components),
        claims=claims,
        investments=investments,
        timeline=timeline,
        managers=User.query.filter(User._is_active.is_(True), User.id != employee.id).order_by(User.name).all(),
        today=date.today(),
    )


@hrms.route('/employees/<int:user_id>/profile', methods=['POST'])
@login_required
def update_employee_profile(user_id):
    if not hr_can_manage():
        flash('HR access required.', 'danger')
        return redirect(url_for('hrms.employee_detail', user_id=user_id))
    employee = User.query.get_or_404(user_id)
    hr_profile = _employee_profile_for(employee)
    payroll_profile = _profile_for(employee)

    employee.phone = request.form.get('phone', '').strip() or None
    employee.designation = request.form.get('designation', '').strip() or None
    employee.reporting_manager_id = request.form.get('reporting_manager_id') or None
    employee.employment_type = request.form.get('employment_type', '').strip() or None
    employee.work_location = request.form.get('work_location', '').strip() or None
    employee.branch = request.form.get('branch', '').strip() or None
    employee.cost_center = request.form.get('cost_center', '').strip() or None
    employee.grade = request.form.get('grade', '').strip() or None
    employee.shift = request.form.get('shift', '').strip() or None
    employee.date_of_joining = _parse_date(request.form.get('date_of_joining'))
    employee.probation_end_date = _parse_date(request.form.get('probation_end_date'))
    employee.emergency_contact_name = request.form.get('emergency_contact_name', '').strip() or None
    employee.emergency_contact_phone = request.form.get('emergency_contact_phone', '').strip() or None

    hr_profile.date_of_birth = _parse_date(request.form.get('date_of_birth'))
    hr_profile.gender = request.form.get('gender', '').strip() or None
    hr_profile.marital_status = request.form.get('marital_status', '').strip() or None
    hr_profile.personal_email = request.form.get('personal_email', '').strip() or None
    hr_profile.blood_group = request.form.get('blood_group', '').strip() or None
    hr_profile.address_line1 = request.form.get('address_line1', '').strip() or None
    hr_profile.address_line2 = request.form.get('address_line2', '').strip() or None
    hr_profile.city = request.form.get('city', '').strip() or None
    hr_profile.state = request.form.get('state', '').strip() or None
    hr_profile.postal_code = request.form.get('postal_code', '').strip() or None
    hr_profile.country = request.form.get('country', '').strip() or 'India'
    hr_profile.mobile_app_enabled = request.form.get('mobile_app_enabled') == 'on'
    hr_profile.mobile_device_id = request.form.get('mobile_device_id', '').strip() or None
    hr_profile.other_info = request.form.get('other_info', '').strip() or None
    hr_profile.updated_by_id = current_user.id

    annual_ctc = _parse_amount(request.form.get('annual_ctc')) or Decimal('0')
    fbp = _parse_amount(request.form.get('flexible_benefit_plan')) or Decimal('0')
    variable_pay = _parse_amount(request.form.get('variable_pay')) or Decimal('0')
    if request.form.getlist('component_name[]'):
        annual_ctc, fbp = _salary_component_totals_from_form()
    salary_changed = _salary_changed(payroll_profile, annual_ctc, fbp, variable_pay)
    payroll_profile.annual_ctc = annual_ctc
    payroll_profile.flexible_benefit_plan = fbp
    payroll_profile.variable_pay = variable_pay
    payroll_profile.pan_number = request.form.get('pan_number', '').strip() or None
    payroll_profile.pf_number = request.form.get('pf_number', '').strip() or None
    payroll_profile.uan_number = request.form.get('uan_number', '').strip() or None
    payroll_profile.esi_number = request.form.get('esi_number', '').strip() or None
    payroll_profile.eps_number = request.form.get('eps_number', '').strip() or None
    payroll_profile.bank_name = request.form.get('bank_name', '').strip() or None
    payroll_profile.bank_account = request.form.get('bank_account', '').strip() or None
    payroll_profile.ifsc_code = request.form.get('ifsc_code', '').strip() or None
    payroll_profile.updated_by_id = current_user.id
    _save_salary_components(employee)
    if salary_changed:
        db.session.add(EmployeeSalaryHistory(
            user_id=employee.id,
            annual_ctc=annual_ctc,
            flexible_benefit_plan=fbp,
            variable_pay=variable_pay,
            effective_from=_parse_date(request.form.get('effective_from')) or date.today(),
            change_reason=request.form.get('change_reason', '').strip() or 'Employee profile salary update',
            created_by_id=current_user.id,
        ))

    db.session.commit()
    flash('Employee profile updated.', 'success')
    return redirect(url_for('hrms.employee_detail', user_id=employee.id))


@hrms.route('/employees/<int:user_id>/documents', methods=['POST'])
@login_required
def upload_employee_document(user_id):
    if not hr_can_manage():
        flash('HR access required.', 'danger')
        return redirect(url_for('hrms.employee_detail', user_id=user_id))
    employee = User.query.get_or_404(user_id)
    document = _save_employee_document(
        employee,
        request.files.get('document'),
        request.form.get('document_type', '').strip(),
        request.form.get('title', '').strip(),
        request.form.get('notes', '').strip(),
    )
    if not document:
        flash('Please upload a valid employee document.', 'danger')
    else:
        db.session.commit()
        flash('Employee document uploaded.', 'success')
    return redirect(url_for('hrms.employee_detail', user_id=employee.id))


@hrms.route('/employees/documents/<int:document_id>/download')
@login_required
def employee_document_download(document_id):
    document = EmployeeDocument.query.get_or_404(document_id)
    if not hr_can_manage() and current_user.id != document.user_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('hrms.dashboard'))
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'hrms_documents', str(document.user_id))
    return send_from_directory(folder, document.stored_filename, as_attachment=True, download_name=document.original_filename)


@hrms.route('/leave', methods=['GET', 'POST'])
@login_required
def leave():
    if request.method == 'POST':
        user_id = request.form.get('user_id', type=int) if hr_can_manage() else current_user.id
        start = _parse_date(request.form.get('start_date'))
        end = _parse_date(request.form.get('end_date'))
        if not user_id or not start or not end or end < start:
            flash('Please provide a valid employee and leave date range.', 'danger')
            return redirect(url_for('hrms.leave'))
        days = Decimal(str((end - start).days + 1))
        leave_request = LeaveRequest(
            user_id=user_id,
            leave_type=request.form.get('leave_type', 'casual'),
            start_date=start,
            end_date=end,
            days=days,
            reason=request.form.get('reason', '').strip() or None,
        )
        db.session.add(leave_request)
        db.session.commit()
        flash('Leave request submitted.', 'success')
        return redirect(url_for('hrms.leave'))

    query = LeaveRequest.query.order_by(LeaveRequest.created_at.desc())
    if not hr_can_manage():
        query = query.filter_by(user_id=current_user.id)
    return render_template(
        'hrms/leave.html',
        leave_requests=query.all(),
        employees=User.query.filter(User._is_active.is_(True)).order_by(User.name).all(),
    )


@hrms.route('/leave/<int:leave_id>/decision', methods=['POST'])
@login_required
def leave_decision(leave_id):
    if not hr_can_manage():
        flash('Access denied.', 'danger')
        return redirect(url_for('hrms.leave'))
    leave_request = LeaveRequest.query.get_or_404(leave_id)
    action = request.form.get('action')
    if action not in ('approved', 'rejected'):
        flash('Invalid leave decision.', 'danger')
        return redirect(url_for('hrms.leave'))
    leave_request.status = action
    leave_request.approver_id = current_user.id
    leave_request.decision_note = request.form.get('decision_note', '').strip() or None
    leave_request.decided_at = datetime.utcnow()
    db.session.commit()
    flash(f'Leave request {action}.', 'success')
    return redirect(url_for('hrms.leave'))


@hrms.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    if request.method == 'POST':
        user_id = request.form.get('user_id', type=int) if hr_can_manage() else current_user.id
        attendance_date = _parse_date(request.form.get('attendance_date')) or date.today()
        record = AttendanceRecord.query.filter_by(user_id=user_id, attendance_date=attendance_date).first()
        created = False
        if not record:
            record = AttendanceRecord(user_id=user_id, attendance_date=attendance_date, created_by_id=current_user.id)
            db.session.add(record)
            created = True
        record.check_in = _parse_time(request.form.get('check_in'))
        record.check_out = _parse_time(request.form.get('check_out'))
        record.status = request.form.get('status', 'present')
        record.work_mode = request.form.get('work_mode', 'office')
        record.remarks = request.form.get('remarks', '').strip() or None
        db.session.commit()
        flash(f'Attendance record {"created" if created else "updated"}.', 'success')
        return redirect(url_for('hrms.attendance'))

    employee_id = request.args.get('employee_id', type=int)
    status = request.args.get('status', '').strip()
    month = request.args.get('month', date.today().strftime('%Y-%m'))
    start = None
    end = None
    try:
        start = date.fromisoformat(f'{month}-01')
        end = date(start.year + (1 if start.month == 12 else 0), 1 if start.month == 12 else start.month + 1, 1)
    except ValueError:
        month = ''

    query = AttendanceRecord.query.order_by(AttendanceRecord.attendance_date.desc(), AttendanceRecord.created_at.desc())
    if not hr_can_manage():
        query = query.filter_by(user_id=current_user.id)
    elif employee_id:
        query = query.filter_by(user_id=employee_id)
    if status:
        query = query.filter_by(status=status)
    if start and end:
        query = query.filter(AttendanceRecord.attendance_date >= start, AttendanceRecord.attendance_date < end)

    summary_query = AttendanceRecord.query
    if not hr_can_manage():
        summary_query = summary_query.filter_by(user_id=current_user.id)
    elif employee_id:
        summary_query = summary_query.filter_by(user_id=employee_id)
    if start and end:
        summary_query = summary_query.filter(AttendanceRecord.attendance_date >= start, AttendanceRecord.attendance_date < end)
    summary = {
        'present': summary_query.filter_by(status='present').count(),
        'absent': summary_query.filter_by(status='absent').count(),
        'late': summary_query.filter_by(status='late').count(),
        'half_day': summary_query.filter_by(status='half_day').count(),
        'on_leave': summary_query.filter_by(status='on_leave').count(),
    }
    return render_template(
        'hrms/attendance.html',
        records=query.limit(100).all(),
        employees=User.query.filter(User._is_active.is_(True)).order_by(User.name).all(),
        today=date.today(),
        employee_id=employee_id,
        status=status,
        month=month,
        summary=summary,
    )


@hrms.route('/holidays', methods=['GET', 'POST'])
@login_required
def holidays():
    if request.method == 'POST':
        if not hr_can_manage():
            flash('Access denied.', 'danger')
            return redirect(url_for('hrms.holidays'))
        holiday_date = _parse_date(request.form.get('holiday_date'))
        name = request.form.get('name', '').strip()
        if not name or not holiday_date:
            flash('Holiday name and date are required.', 'danger')
            return redirect(url_for('hrms.holidays'))
        holiday = Holiday(
            name=name,
            holiday_date=holiday_date,
            holiday_type=request.form.get('holiday_type', 'public'),
            location=request.form.get('location', '').strip() or None,
            description=request.form.get('description', '').strip() or None,
            created_by_id=current_user.id,
        )
        db.session.add(holiday)
        db.session.commit()
        flash('Holiday added.', 'success')
        return redirect(url_for('hrms.holidays'))

    year = request.args.get('year', date.today().year, type=int)
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    return render_template(
        'hrms/holidays.html',
        holidays=Holiday.query.filter(Holiday.holiday_date >= start, Holiday.holiday_date < end).order_by(Holiday.holiday_date.asc()).all(),
        year=year,
    )


@hrms.route('/holidays/<int:holiday_id>/delete', methods=['POST'])
@login_required
def delete_holiday(holiday_id):
    if not hr_can_manage():
        flash('Access denied.', 'danger')
        return redirect(url_for('hrms.holidays'))
    holiday = Holiday.query.get_or_404(holiday_id)
    db.session.delete(holiday)
    db.session.commit()
    flash('Holiday deleted.', 'success')
    return redirect(url_for('hrms.holidays'))


@hrms.route('/reimbursements', methods=['GET', 'POST'])
@login_required
def reimbursements():
    if request.method == 'POST':
        user_id = request.form.get('user_id', type=int) if hr_can_manage() else current_user.id
        expense_date = _parse_date(request.form.get('expense_date')) or date.today()
        amount = _parse_amount(request.form.get('amount'))
        if not user_id or not amount:
            flash('Please provide a valid employee and amount.', 'danger')
            return redirect(url_for('hrms.reimbursements'))
        claim = ReimbursementClaim(
            user_id=user_id,
            expense_date=expense_date,
            category=request.form.get('category', 'travel'),
            merchant=request.form.get('merchant', '').strip() or None,
            amount=amount,
            currency=request.form.get('currency', 'INR').strip() or 'INR',
            payment_method=request.form.get('payment_method', '').strip() or None,
            description=request.form.get('description', '').strip() or None,
        )
        db.session.add(claim)
        db.session.flush()
        _save_reimbursement_receipt(claim, request.files.get('receipt'))
        db.session.commit()
        flash('Reimbursement claim submitted.', 'success')
        return redirect(url_for('hrms.reimbursements'))

    employee_id = request.args.get('employee_id', type=int)
    status = request.args.get('status', '').strip()
    category = request.args.get('category', '').strip()

    query = ReimbursementClaim.query.order_by(ReimbursementClaim.created_at.desc())
    if not hr_can_manage():
        query = query.filter_by(user_id=current_user.id)
    elif employee_id:
        query = query.filter_by(user_id=employee_id)
    if status:
        query = query.filter_by(status=status)
    if category:
        query = query.filter_by(category=category)

    summary_query = ReimbursementClaim.query
    if not hr_can_manage():
        summary_query = summary_query.filter_by(user_id=current_user.id)
    elif employee_id:
        summary_query = summary_query.filter_by(user_id=employee_id)
    summary = {
        'pending': summary_query.filter_by(status='pending').count(),
        'approved': summary_query.filter_by(status='approved').count(),
        'paid': summary_query.filter_by(status='paid').count(),
        'rejected': summary_query.filter_by(status='rejected').count(),
    }
    return render_template(
        'hrms/reimbursements.html',
        claims=query.limit(100).all(),
        employees=User.query.filter(User._is_active.is_(True)).order_by(User.name).all(),
        employee_id=employee_id,
        status=status,
        category=category,
        today=date.today(),
        summary=summary,
    )


@hrms.route('/reimbursements/<int:claim_id>/decision', methods=['POST'])
@login_required
def reimbursement_decision(claim_id):
    if not hr_can_manage():
        flash('Access denied.', 'danger')
        return redirect(url_for('hrms.reimbursements'))
    claim = ReimbursementClaim.query.get_or_404(claim_id)
    action = request.form.get('action')
    if action not in ('approved', 'rejected', 'paid'):
        flash('Invalid reimbursement action.', 'danger')
        return redirect(url_for('hrms.reimbursements'))
    if action == 'paid':
        claim.paid_at = datetime.utcnow()
    claim.status = action
    claim.reviewer_id = current_user.id
    claim.decision_note = request.form.get('decision_note', '').strip() or None
    claim.decided_at = datetime.utcnow()
    db.session.commit()
    flash(f'Reimbursement claim {action}.', 'success')
    return redirect(url_for('hrms.reimbursements'))


@hrms.route('/reimbursements/<int:claim_id>/receipt')
@login_required
def reimbursement_receipt(claim_id):
    claim = ReimbursementClaim.query.get_or_404(claim_id)
    if not hr_can_manage() and claim.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('hrms.reimbursements'))
    if not claim.receipt_filename:
        flash('Receipt not available.', 'warning')
        return redirect(url_for('hrms.reimbursements'))
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reimbursements', str(claim.id))
    return send_from_directory(folder, claim.receipt_filename, as_attachment=True, download_name=claim.receipt_original_name)
