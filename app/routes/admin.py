import csv
from io import StringIO

from flask import Blueprint, Response, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models.user import User
from app.models.ticket import Ticket
from app.models.asset import Asset
from app.models.department import Department
from app.models.assignment_rule import AssignmentRule
from app.models.reply import TicketReplyTemplate
from app.utils.email import send_welcome_email
from app.utils.locations import INDIA_LOCATION_OPTIONS, location_details_for_name

admin = Blueprint('admin', __name__)

COMPANY_DOMAIN_OPTIONS = ['Winsoft', 'TCS', 'Wipro', 'Infosys']
ROLE_MODE_OPTIONS = [
    ('department_admin', 'Admin - access based on selected department'),
    ('department_basic', 'Basic User - own/assigned tickets only'),
]

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.can_manage_system:
            flash('System owner access required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


def people_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.can_manage_user_accounts:
            flash('User account management access required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


def helpdesk_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.can_manage_helpdesk:
            flash('Helpdesk admin access required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


def role_options_for_current_user():
    return [
        ('department_admin', 'Admin - access based on selected department'),
        ('department_basic', 'Basic User - own/assigned tickets only'),
    ]


def role_mode_for_user(user):
    if user.role == 'master_admin':
        return 'master_admin'
    if user.role in ('admin_staff', 'hr_admin'):
        return 'department_admin'
    return 'department_basic'


def internal_role_from_mode(role_mode):
    role_map = {
        'master_admin': 'master_admin',
        'department_admin': 'admin_staff',
        'department_basic': 'hr_staff',
        # Backward compatibility for old forms/bookmarks.
        'admin_staff': 'admin_staff',
        'hr_admin': 'admin_staff',
        'hr_staff': 'hr_staff',
        'user': 'hr_staff',
    }
    return role_map.get(role_mode, 'hr_staff')


def can_manage_user_record(user):
    return current_user.can_manage_system or current_user.can_manage_user_accounts


def user_has_history(user):
    from app.models.audit import AuditPolicyAcknowledgement
    from app.models.comment import Comment
    from app.models.knowledge import KnowledgeAcknowledgement, KnowledgeArticle
    from app.models.reply import TicketReply

    checks = [
        Ticket.query.filter_by(user_id=user.id).count(),
        Ticket.query.filter_by(assigned_to=user.id).count(),
        Asset.query.filter_by(assigned_user_id=user.id).count(),
        Comment.query.filter_by(user_id=user.id).count(),
        TicketReply.query.filter_by(user_id=user.id).count(),
        KnowledgeArticle.query.filter_by(author_id=user.id).count(),
        KnowledgeAcknowledgement.query.filter_by(user_id=user.id).count(),
        AuditPolicyAcknowledgement.query.filter_by(user_id=user.id).count(),
    ]
    return any(checks)


def _assignment_form_options():
    from app.routes.tickets import TICKET_CATEGORY_MAP
    users = [
        user for user in User.query.filter(User._is_active.is_(True)).order_by(User.role, User.name).all()
        if user.can_manage_helpdesk
    ]
    departments = Department.query.order_by(Department.name).all()
    categories = [
        row[0] for row in db.session.query(Ticket.category)
        .filter(Ticket.category.isnot(None), Ticket.category != '')
        .distinct()
        .order_by(Ticket.category)
        .all()
    ]
    support_groups = [
        row[0] for row in db.session.query(Ticket.support_group)
        .filter(Ticket.support_group.isnot(None), Ticket.support_group != '')
        .distinct()
        .order_by(Ticket.support_group)
        .all()
    ]
    for department in departments:
        if department.name not in support_groups:
            support_groups.append(department.name)
    for category in TICKET_CATEGORY_MAP.keys():
        if category not in categories:
            categories.append(category)
    return users, sorted(categories), sorted(support_groups)


def _visible_ticket_query():
    query = Ticket.query
    if current_user.can_view_all_tickets:
        return query
    return query.filter(db.or_(
        Ticket.user_id == current_user.id,
        Ticket.assigned_to == current_user.id,
    ))


@admin.route('/users')
@login_required
@people_admin_required
def users():
    q = request.args.get('q', '').strip()
    role = request.args.get('role', '').strip()
    status = request.args.get('status', '').strip()
    department_id = request.args.get('department_id', type=int)

    query = User.query.filter(db.or_(User.username.is_(None), User.username != 'system_email_requester'))
    if q:
        like_q = f'%{q}%'
        query = query.filter(db.or_(
            User.name.ilike(like_q),
            User.email.ilike(like_q),
            User.username.ilike(like_q),
            User.employee_id.ilike(like_q),
            User.designation.ilike(like_q),
            User.work_location.ilike(like_q),
        ))
    if role == 'department_admin':
        query = query.filter(User.role.in_(['admin_staff', 'hr_admin']))
    elif role == 'department_basic':
        query = query.filter(User.role.in_(['hr_staff', 'user']))
    elif role:
        query = query.filter(User.role == role)
    if status == 'active':
        query = query.filter(User._is_active.is_(True))
    elif status == 'inactive':
        query = query.filter(User._is_active.is_(False))
    if department_id:
        query = query.filter(User.department_id == department_id)

    all_users = query.order_by(User.created_at.desc()).all()
    base_query = User.query.filter(db.or_(User.username.is_(None), User.username != 'system_email_requester'))
    metrics = {
        'total': base_query.count(),
        'active': base_query.filter(User._is_active.is_(True)).count(),
        'inactive': base_query.filter(User._is_active.is_(False)).count(),
        'masters': base_query.filter(User.role == 'master_admin').count(),
        'department_admins': base_query.filter(User.role.in_(['admin_staff', 'hr_admin'])).count(),
        'department_basic': base_query.filter(User.role.in_(['hr_staff', 'user'])).count(),
    }
    departments = Department.query.order_by(Department.name).all()
    return render_template(
        'admin/users.html',
        users=all_users,
        metrics=metrics,
        departments=departments,
        q=q,
        role=role,
        status=status,
        department_id=department_id,
    )


@admin.route('/users/create', methods=['GET', 'POST'])
@login_required
@people_admin_required
def create_user():
    departments = Department.query.order_by(Department.name).all()
    role_options = role_options_for_current_user()
    allowed_roles = {role for role, _label in role_options}
    last = User.query.order_by(User.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    suggested_user_code = f"USR{next_id:04d}"

    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name  = request.form.get('last_name', '').strip()
        full_name  = f"{first_name} {last_name}".strip() or request.form.get('name', '').strip()
        email      = request.form.get('email', '').strip()
        phone      = request.form.get('phone', '').strip()
        company_domain = request.form.get('company_domain', '').strip()
        username   = request.form.get('username', '').strip()
        password   = request.form.get('password')
        confirm    = request.form.get('confirm_password')
        role_mode  = request.form.get('role', 'department_basic')
        if role_mode not in allowed_roles:
            role_mode = 'department_basic'
        role = internal_role_from_mode(role_mode)
        department_id      = request.form.get('department_id') or None
        designation        = request.form.get('designation', '').strip()
        work_location      = request.form.get('work_location', '').strip()
        location_details   = location_details_for_name(work_location)
        employee_id        = request.form.get('user_code', '').strip()
        status             = request.form.get('status', 'active')
        module_helpdesk = request.form.get('allow_helpdesk_admin') == 'on'
        module_inventory = request.form.get('allow_inventory') == 'on'
        module_licenses = request.form.get('allow_licenses') == 'on'
        module_compliance = request.form.get('allow_compliance') == 'on'
        require_mfa = request.form.get('two_factor_required') == 'on'

        errors = []
        if not first_name:
            errors.append('First name is required.')
        if not last_name:
            errors.append('Last name is required.')
        if not email:
            errors.append('Email is required.')
        if not phone:
            errors.append('Mobile number is required.')
        if not username:
            errors.append('Username is required.')
        if User.query.filter_by(email=email).first():
            errors.append('Email already exists.')
        if username and User.query.filter_by(username=username).first():
            errors.append('Username already taken.')
        if employee_id and User.query.filter_by(employee_id=employee_id).first():
            errors.append('User code already exists.')
        if not department_id:
            errors.append('Department is required for login validation and department-wise access.')
        if not company_domain:
            errors.append('Company / Domain is required for login validation.')
        if not work_location:
            errors.append('Location is required for location-wise ticket numbering and ticket view.')
        elif not location_details:
            errors.append('Please select a valid location from the dropdown.')
        if password != confirm:
            errors.append('Passwords do not match.')
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('admin/create_user.html', departments=departments,
                                   suggested_user_code=employee_id or suggested_user_code, form=request.form,
                                   role_options=role_options, company_domains=COMPANY_DOMAIN_OPTIONS,
                                   location_options=INDIA_LOCATION_OPTIONS)

        # Store the helpdesk user code in the existing employee_id column for compatibility.
        if not employee_id:
            employee_id = suggested_user_code

        user = User(
            employee_id=employee_id,
            first_name=first_name,
            last_name=last_name,
            name=full_name,
            email=email,
            phone=phone,
            company_domain=company_domain or None,
            username=username or None,
            role=role,
            designation=designation,
            department_id=department_id,
            work_location=work_location or None,
            work_state=location_details['state'],
            state_code=location_details['state_code'],
            location_code=location_details['location_code'],
            allow_helpdesk_admin=module_helpdesk,
            allow_inventory=module_inventory,
            allow_licenses=module_licenses,
            allow_compliance=module_compliance,
            two_factor_required=require_mfa,
            created_by_id=current_user.id,
        )
        user._is_active = (status == 'active')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        try:
            send_welcome_email(user, password)
        except Exception:
            pass

        flash(f'User {full_name} ({employee_id}) created successfully!', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/create_user.html', departments=departments,
                           suggested_user_code=suggested_user_code, form={}, role_options=role_options,
                           company_domains=COMPANY_DOMAIN_OPTIONS, location_options=INDIA_LOCATION_OPTIONS)


@admin.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@people_admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if not can_manage_user_record(user):
        flash('System owner access required for this user.', 'danger')
        return redirect(url_for('admin.users'))
    departments = Department.query.order_by(Department.name).all()
    role_options = role_options_for_current_user()
    allowed_roles = {role for role, _label in role_options}
    if request.method == 'POST':
        user.name        = request.form.get('name', user.name).strip()
        user.email       = request.form.get('email', user.email).strip()
        user.phone       = request.form.get('phone', '').strip()
        user.company_domain = request.form.get('company_domain', '').strip() or None
        user.designation = request.form.get('designation', '').strip()
        user.work_location = request.form.get('work_location', '').strip() or None
        location_details = location_details_for_name(user.work_location)
        user.work_state = location_details['state'] if location_details else None
        user.state_code = location_details['state_code'] if location_details else None
        user.location_code = location_details['location_code'] if location_details else None
        requested_role = request.form.get('role', role_mode_for_user(user))
        if user.role == 'master_admin':
            pass
        elif requested_role in allowed_roles:
            user.role = internal_role_from_mode(requested_role)
        user.department_id = request.form.get('department_id') or None
        user.allow_helpdesk_admin = request.form.get('allow_helpdesk_admin') == 'on'
        user.allow_inventory = request.form.get('allow_inventory') == 'on'
        user.allow_licenses = request.form.get('allow_licenses') == 'on'
        user.allow_compliance = request.form.get('allow_compliance') == 'on'
        user.two_factor_required = request.form.get('two_factor_required') == 'on'
        if request.form.get('disable_two_factor') == 'on':
            user.two_factor_enabled = False
            user.two_factor_secret = None
            user.two_factor_backup_codes = None
            user.two_factor_required = False
        elif request.form.get('reset_two_factor') == 'on':
            user.two_factor_enabled = False
            user.two_factor_secret = None
            user.two_factor_backup_codes = None
            user.two_factor_required = True
        if not user.department_id:
            flash('Department is required for login validation and department-wise access.', 'danger')
            return render_template('admin/edit_user.html', user=user, departments=departments, role_options=role_options, role_mode=role_mode_for_user(user), company_domains=COMPANY_DOMAIN_OPTIONS, location_options=INDIA_LOCATION_OPTIONS)
        if not user.company_domain:
            flash('Company / Domain is required for login validation.', 'danger')
            return render_template('admin/edit_user.html', user=user, departments=departments, role_options=role_options, role_mode=role_mode_for_user(user), company_domains=COMPANY_DOMAIN_OPTIONS, location_options=INDIA_LOCATION_OPTIONS)
        if not user.work_location:
            flash('Location is required for location-wise ticket numbering and ticket view.', 'danger')
            return render_template('admin/edit_user.html', user=user, departments=departments, role_options=role_options, role_mode=role_mode_for_user(user), company_domains=COMPANY_DOMAIN_OPTIONS, location_options=INDIA_LOCATION_OPTIONS)
        if not user.state_code or not user.location_code:
            flash('Please select a valid location from the dropdown.', 'danger')
            return render_template('admin/edit_user.html', user=user, departments=departments, role_options=role_options, role_mode=role_mode_for_user(user), company_domains=COMPANY_DOMAIN_OPTIONS, location_options=INDIA_LOCATION_OPTIONS)
        user.employee_id = request.form.get('employee_id', user.employee_id).strip()
        pwd = request.form.get('password', '').strip()
        if pwd:
            user.set_password(pwd)
        db.session.commit()
        flash(f'User {user.name} updated.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/edit_user.html', user=user, departments=departments, role_options=role_options, role_mode=role_mode_for_user(user), company_domains=COMPANY_DOMAIN_OPTIONS, location_options=INDIA_LOCATION_OPTIONS)


@admin.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@people_admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Cannot deactivate yourself.', 'warning')
    elif not can_manage_user_record(user):
        flash('System owner access required for this user.', 'danger')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        flash(f'User {"activated" if user.is_active else "deactivated"}.', 'success')
    return redirect(url_for('admin.users'))


@admin.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@people_admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Cannot delete yourself.', 'warning')
    elif not can_manage_user_record(user):
        flash('System owner access required for this user.', 'danger')
    elif user_has_history(user):
        user.is_active = False
        db.session.commit()
        flash('User has tickets or linked history, so the profile was deactivated instead of deleted.', 'warning')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted.', 'success')
    return redirect(url_for('admin.users'))


@admin.route('/email-config', methods=['GET', 'POST'])
@login_required
@admin_required
def email_config():
    from app.models.email_config import EmailConfig
    from app.utils.email import test_email_config
    cfg = EmailConfig.get()

    if request.method == 'POST':
        action = request.form.get('action')
        if not cfg:
            cfg = EmailConfig()
            db.session.add(cfg)

        cfg.mail_server   = request.form.get('mail_server', '').strip()
        cfg.mail_port     = int(request.form.get('mail_port', 587))
        cfg.mail_use_tls  = request.form.get('mail_use_tls') == 'on'
        cfg.mail_use_ssl  = request.form.get('mail_use_ssl') == 'on'
        cfg.mail_username = request.form.get('mail_username', '').strip()
        cfg.mail_from     = request.form.get('mail_from', '').strip()
        cfg.mail_from_name = request.form.get('mail_from_name', 'IT HelpDesk').strip()
        cfg.notify_cc     = request.form.get('notify_cc', '').strip() or None
        cfg.notify_ticket_created  = request.form.get('notify_ticket_created')  == 'on'
        cfg.notify_ticket_updated  = request.form.get('notify_ticket_updated')  == 'on'
        cfg.notify_ticket_assigned = request.form.get('notify_ticket_assigned') == 'on'
        cfg.notify_email_ticket    = request.form.get('notify_email_ticket')    == 'on'
        cfg.inbound_enabled = request.form.get('inbound_enabled') == 'on'
        cfg.imap_server = request.form.get('imap_server', '').strip() or None
        cfg.imap_port = int(request.form.get('imap_port', 993) or 993)
        cfg.imap_use_ssl = request.form.get('imap_use_ssl') == 'on'
        cfg.imap_username = request.form.get('imap_username', '').strip() or None
        cfg.imap_folder = request.form.get('imap_folder', '').strip() or 'INBOX'
        imap_pwd = request.form.get('imap_password', '').strip()
        if imap_pwd:
            cfg.imap_password = imap_pwd
        # Only update password if provided
        pwd = request.form.get('mail_password', '').strip()
        if pwd:
            cfg.mail_password = pwd

        # Validate: mail_server must be a hostname, not an email address
        if '@' in cfg.mail_server:
            flash('Mail Server must be a hostname (e.g. smtp.hostinger.com), not an email address.', 'danger')
            return render_template('admin/email_config.html', cfg=cfg)

        db.session.commit()

        if action == 'test':
            test_recipient = request.form.get('test_recipient', '').strip() or current_user.email
            ok, err = test_email_config(cfg, test_recipient)
            if ok:
                flash(f'Test email sent successfully to {test_recipient}!', 'success')
            else:
                flash(f'Test failed: {err}', 'danger')
        else:
            flash('Email configuration saved.', 'success')
        return redirect(url_for('admin.email_config'))

    return render_template('admin/email_config.html', cfg=cfg)


@admin.route('/assignment-rules', methods=['GET', 'POST'])
@login_required
@helpdesk_admin_required
def assignment_rules():
    users, categories, support_groups = _assignment_form_options()
    editing_rule = None

    if request.method == 'POST':
        rule_id = request.form.get('rule_id')
        action = request.form.get('action', 'save')
        if rule_id:
            editing_rule = AssignmentRule.query.get_or_404(int(rule_id))
        else:
            editing_rule = AssignmentRule()
            db.session.add(editing_rule)

        if action == 'delete' and editing_rule.id:
            db.session.delete(editing_rule)
            db.session.commit()
            flash('Assignment rule deleted.', 'success')
            return redirect(url_for('admin.assignment_rules'))

        if action == 'toggle' and editing_rule.id:
            editing_rule.is_active = not editing_rule.is_active
            db.session.commit()
            flash(f'Assignment rule {"enabled" if editing_rule.is_active else "disabled"}.', 'success')
            return redirect(url_for('admin.assignment_rules'))

        editing_rule.name = request.form.get('name', '').strip()
        editing_rule.is_active = request.form.get('is_active') == 'on'
        editing_rule.priority_order = int(request.form.get('priority_order') or 100)
        editing_rule.match_source = request.form.get('match_source') or None
        editing_rule.match_ticket_type = request.form.get('match_ticket_type') or None
        editing_rule.match_priority = request.form.get('match_priority') or None
        editing_rule.match_category = request.form.get('match_category') or None
        editing_rule.match_support_group = request.form.get('match_support_group') or None
        editing_rule.keywords = request.form.get('keywords', '').strip() or None
        editing_rule.assign_to = int(request.form.get('assign_to')) if request.form.get('assign_to') else None
        editing_rule.set_support_group = request.form.get('set_support_group') or None
        editing_rule.set_priority = request.form.get('set_priority') or None
        editing_rule.set_status = request.form.get('set_status') or None

        if not editing_rule.name:
            flash('Rule name is required.', 'danger')
        elif not any([editing_rule.assign_to, editing_rule.set_support_group, editing_rule.set_priority, editing_rule.set_status]):
            flash('Set at least one action for the rule.', 'danger')
        else:
            db.session.commit()
            flash('Assignment rule saved.', 'success')
            return redirect(url_for('admin.assignment_rules'))

    edit_id = request.args.get('edit', type=int)
    if edit_id and not editing_rule:
        editing_rule = AssignmentRule.query.get_or_404(edit_id)

    rules = AssignmentRule.query.order_by(AssignmentRule.priority_order.asc(), AssignmentRule.id.asc()).all()
    return render_template(
        'admin/assignment_rules.html',
        rules=rules,
        editing_rule=editing_rule,
        users=users,
        categories=categories,
        support_groups=support_groups,
    )


@admin.route('/reply-templates', methods=['GET', 'POST'])
@login_required
@helpdesk_admin_required
def reply_templates():
    editing_template = None

    if request.method == 'POST':
        template_id = request.form.get('template_id')
        action = request.form.get('action', 'save')
        if template_id:
            editing_template = TicketReplyTemplate.query.get_or_404(int(template_id))
        else:
            editing_template = TicketReplyTemplate(created_by=current_user.id)
            db.session.add(editing_template)

        if action == 'delete' and editing_template.id:
            db.session.delete(editing_template)
            db.session.commit()
            flash('Reply template deleted.', 'success')
            return redirect(url_for('admin.reply_templates'))

        if action == 'toggle' and editing_template.id:
            editing_template.is_active = not editing_template.is_active
            db.session.commit()
            flash(f'Reply template {"enabled" if editing_template.is_active else "disabled"}.', 'success')
            return redirect(url_for('admin.reply_templates'))

        editing_template.name = request.form.get('name', '').strip()
        editing_template.category = request.form.get('category', '').strip() or None
        editing_template.body = request.form.get('body', '').strip()
        editing_template.is_internal = request.form.get('is_internal') == 'on'
        editing_template.is_active = request.form.get('is_active') == 'on'
        if not editing_template.name:
            flash('Template name is required.', 'danger')
        elif not editing_template.body:
            flash('Template body is required.', 'danger')
        else:
            db.session.commit()
            flash('Reply template saved.', 'success')
            return redirect(url_for('admin.reply_templates'))

    edit_id = request.args.get('edit', type=int)
    if edit_id and not editing_template:
        editing_template = TicketReplyTemplate.query.get_or_404(edit_id)

    templates = TicketReplyTemplate.query.order_by(
        TicketReplyTemplate.category.asc(),
        TicketReplyTemplate.name.asc(),
    ).all()
    categories = [
        row[0] for row in db.session.query(TicketReplyTemplate.category)
        .filter(TicketReplyTemplate.category.isnot(None), TicketReplyTemplate.category != '')
        .distinct()
        .order_by(TicketReplyTemplate.category)
        .all()
    ]
    return render_template(
        'admin/reply_templates.html',
        templates=templates,
        editing_template=editing_template,
        categories=categories,
    )


@admin.route('/signature', methods=['GET', 'POST'])
@login_required
@admin_required
def signature():
    from app.models.user_signature import UserSignature
    from app.utils.signatures import DEFAULT_SIGNATURE_HTML, normalize_signature_html, save_inline_signature_images
    signature = UserSignature.for_user(current_user)
    if request.method == 'POST':
        signature.signature_enabled = request.form.get('signature_enabled') == 'on'
        signature.auto_insert_signature = request.form.get('auto_insert_signature') == 'on'
        signature_html = normalize_signature_html(request.form.get('signature_html', '').strip())
        signature.signature_html = save_inline_signature_images(signature_html, current_user.id) if signature_html else None
        db.session.commit()
        flash('Signature settings saved.', 'success')
        return redirect(url_for('admin.signature'))
    return render_template(
        'settings/signature.html',
        signature=signature,
        target_user=current_user,
        default_signature=DEFAULT_SIGNATURE_HTML,
        admin_mode=True,
    )


@admin.route('/reports')
@login_required
def reports():
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    range_key = request.args.get('range', '30')
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    def parse_date(value, end=False):
        if not value:
            return None
        try:
            parsed = datetime.strptime(value, '%Y-%m-%d')
            return parsed + timedelta(days=1) - timedelta(seconds=1) if end else parsed
        except ValueError:
            return None

    end_dt = parse_date(end_date, end=True) or now
    if start_date:
        start_dt = parse_date(start_date)
    elif range_key == 'all':
        start_dt = None
    else:
        try:
            start_dt = now - timedelta(days=int(range_key))
        except ValueError:
            range_key = '30'
            start_dt = now - timedelta(days=30)

    ticket_query = _visible_ticket_query()
    if start_dt:
        ticket_query = ticket_query.filter(Ticket.created_at >= start_dt)
    if end_dt:
        ticket_query = ticket_query.filter(Ticket.created_at <= end_dt)

    total = ticket_query.count()
    open_t = ticket_query.filter_by(status='open').count()
    in_progress = ticket_query.filter_by(status='in_progress').count()
    pending = ticket_query.filter_by(status='pending').count()
    resolved = ticket_query.filter_by(status='resolved').count()
    closed = ticket_query.filter_by(status='closed').count()
    overdue = ticket_query.filter(Ticket.sla_due < now, Ticket.status.notin_(['resolved', 'closed'])).count()
    critical = ticket_query.filter_by(priority='critical').count()
    high = ticket_query.filter_by(priority='high').count()
    medium = ticket_query.filter_by(priority='medium').count()
    low = ticket_query.filter_by(priority='low').count()

    status_counts = [('Open', open_t, 'yellow'), ('In Progress', in_progress, 'orange'), ('Pending', pending, 'purple'), ('Resolved', resolved, 'green'), ('Closed', closed, 'gray')]
    priority_counts = [('Critical', critical, 'red'), ('High', high, 'orange'), ('Medium', medium, 'yellow'), ('Low', low, 'green')]
    source_counts = [
        (label, ticket_query.filter_by(source=value).count())
        for value, label in [('manual', 'Manual'), ('email', 'Email'), ('phone', 'Phone'), ('walk_in', 'Walk-In'), ('self_service', 'Self-Service')]
    ]
    category_counts = [
        (row[0] or 'Uncategorized', row[1])
        for row in ticket_query.with_entities(Ticket.category, db.func.count(Ticket.id))
        .group_by(Ticket.category)
        .order_by(db.func.count(Ticket.id).desc())
        .limit(8)
        .all()
    ]
    resolved_tickets = ticket_query.filter(Ticket.resolved_at.isnot(None)).all()
    avg_resolution_hours = None
    if resolved_tickets:
        total_seconds = sum(
            (ticket.resolved_at - ticket.created_at).total_seconds()
            for ticket in resolved_tickets
            if ticket.resolved_at and ticket.created_at
        )
        avg_resolution_hours = round(total_seconds / max(len(resolved_tickets), 1) / 3600, 1)
    sla_met = ticket_query.filter(
        Ticket.sla_due.isnot(None),
        db.or_(Ticket.resolved_at.is_(None), Ticket.resolved_at <= Ticket.sla_due),
    ).count()
    sla_total = ticket_query.filter(Ticket.sla_due.isnot(None)).count()
    sla_met_percent = round((sla_met / sla_total) * 100, 1) if sla_total else 0
    recent_tickets = ticket_query.order_by(Ticket.created_at.desc()).limit(10).all()

    can_export_admin_reports = current_user.can_manage_system or current_user.can_manage_inventory
    if can_export_admin_reports:
        total_assets = Asset.query.count()
        in_use = Asset.query.filter_by(status='in_use').count()
        available = Asset.query.filter_by(status='available').count()
        under_repair = Asset.query.filter_by(status='under_repair').count()
        retired = Asset.query.filter_by(status='retired').count()
        asset_type_counts = [
            (row[0].replace('_', ' ').title() if row[0] else 'Other', row[1])
            for row in Asset.query.with_entities(Asset.asset_type, db.func.count(Asset.id))
            .group_by(Asset.asset_type)
            .order_by(db.func.count(Asset.id).desc())
            .all()
        ]
    else:
        total_assets = in_use = available = under_repair = retired = 0
        asset_type_counts = []
    export_args = {'range': range_key, 'start_date': start_date, 'end_date': end_date}
    return render_template('admin/reports.html',
        total=total, open_t=open_t, in_progress=in_progress,
        pending=pending, resolved=resolved, closed=closed, overdue=overdue,
        critical=critical, high=high, medium=medium, low=low,
        total_assets=total_assets, in_use=in_use, available=available, under_repair=under_repair,
        retired=retired, status_counts=status_counts, priority_counts=priority_counts,
        source_counts=source_counts, category_counts=category_counts,
        avg_resolution_hours=avg_resolution_hours, sla_met_percent=sla_met_percent,
        sla_total=sla_total, recent_tickets=recent_tickets,
        asset_type_counts=asset_type_counts, range_key=range_key,
        start_date=start_date, end_date=end_date, export_args=export_args,
        can_export_admin_reports=can_export_admin_reports,
    )


@admin.route('/reports/export/<report_type>')
@login_required
def export_report(report_type):
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    range_key = request.args.get('range', '30')
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    def parse_date(value, end=False):
        if not value:
            return None
        try:
            parsed = datetime.strptime(value, '%Y-%m-%d')
            return parsed + timedelta(days=1) - timedelta(seconds=1) if end else parsed
        except ValueError:
            return None

    end_dt = parse_date(end_date, end=True) or now
    if start_date:
        start_dt = parse_date(start_date)
    elif range_key == 'all':
        start_dt = None
    else:
        try:
            start_dt = now - timedelta(days=int(range_key))
        except ValueError:
            start_dt = now - timedelta(days=30)

    output = StringIO()
    writer = csv.writer(output)

    if report_type == 'tickets':
        query = _visible_ticket_query()
        if start_dt:
            query = query.filter(Ticket.created_at >= start_dt)
        if end_dt:
            query = query.filter(Ticket.created_at <= end_dt)
        writer.writerow(['Ticket No', 'Title', 'Requester', 'Assignee', 'Status', 'Priority', 'Source', 'Category', 'SLA Due', 'Resolved At', 'Created At'])
        for ticket in query.order_by(Ticket.created_at.desc()).all():
            writer.writerow([
                ticket.ticket_number or ticket.id,
                ticket.title,
                ticket.creator.name if ticket.creator else '',
                ticket.assignee.name if ticket.assignee else '',
                ticket.status,
                ticket.priority,
                ticket.source,
                ticket.category or '',
                ticket.sla_due.strftime('%Y-%m-%d %H:%M') if ticket.sla_due else '',
                ticket.resolved_at.strftime('%Y-%m-%d %H:%M') if ticket.resolved_at else '',
                ticket.created_at.strftime('%Y-%m-%d %H:%M') if ticket.created_at else '',
            ])
    elif report_type == 'assets':
        if not (current_user.can_manage_system or current_user.can_manage_inventory):
            flash('Access denied for asset export.', 'danger')
            return redirect(url_for('admin.reports'))
        assets = Asset.query.order_by(Asset.created_at.desc()).all()
        hostname_counts = {}
        ip_counts = {}
        for asset in assets:
            hostname_key = (asset.hostname or '').strip().lower()
            ip_key = (asset.ip_address or '').strip().lower()
            if hostname_key:
                hostname_counts[hostname_key] = hostname_counts.get(hostname_key, 0) + 1
            if ip_key:
                ip_counts[ip_key] = ip_counts.get(ip_key, 0) + 1
        writer.writerow([
            'SR', 'Site Name', 'Asset Type', 'Asset Tag', 'Hostname', 'IP Address',
            'User Name', 'Team Leader', 'Previous Users', 'Designation', 'CPU',
            'CPU SR No.', 'Motherboard', 'SSD', 'OS', 'Full SR No.', 'RAM',
            'RAM Type', 'HDD', 'Monitor', 'Mouse', 'Keyboard', 'Status', 'Remarks',
            'Hostname Duplicate Count', 'IP Duplicate Count', 'Duplicate Issue'
        ])
        for index, asset in enumerate(assets, start=1):
            hostname_key = (asset.hostname or '').strip().lower()
            ip_key = (asset.ip_address or '').strip().lower()
            hostname_duplicate_count = hostname_counts.get(hostname_key, 0) if hostname_key else 0
            ip_duplicate_count = ip_counts.get(ip_key, 0) if ip_key else 0
            duplicate_issue = []
            if hostname_duplicate_count > 1:
                duplicate_issue.append('Duplicate Hostname')
            if ip_duplicate_count > 1:
                duplicate_issue.append('Duplicate IP')
            writer.writerow([
                index,
                asset.site_name or '',
                asset.asset_type,
                asset.asset_tag,
                asset.hostname or '',
                asset.ip_address or '',
                asset.assigned_user.name if asset.assigned_user else '',
                asset.team_leader or '',
                asset.previous_users or '',
                asset.designation or '',
                asset.cpu_model or '',
                asset.cpu_serial or '',
                asset.motherboard or '',
                asset.ssd_model or '',
                asset.operating_system or '',
                asset.full_serial_number or '',
                asset.ram_details or '',
                asset.ram_type or '',
                asset.internal_hdd or '',
                asset.monitor_model or '',
                asset.mouse_model or '',
                asset.keyboard_model or '',
                asset.status,
                asset.remarks or asset.notes or '',
                hostname_duplicate_count if hostname_duplicate_count > 1 else '',
                ip_duplicate_count if ip_duplicate_count > 1 else '',
                ', '.join(duplicate_issue),
            ])
    elif report_type == 'users':
        if not current_user.can_manage_user_accounts:
            flash('Access denied for user export.', 'danger')
            return redirect(url_for('admin.reports'))
        writer.writerow(['User Code', 'Name', 'Email', 'Phone', 'Department', 'Role', 'Company', 'Status', 'MFA Enabled'])
        for user in User.query.filter(db.or_(User.username.is_(None), User.username != 'system_email_requester')).order_by(User.name).all():
            writer.writerow([
                user.employee_id or '',
                user.name,
                user.email,
                user.phone or '',
                user.department.name if user.department else '',
                user.role_label,
                user.company_domain or '',
                'Active' if user.is_active else 'Inactive',
                'Yes' if user.two_factor_enabled else 'No',
            ])
    elif report_type == 'sla':
        query = _visible_ticket_query().filter(Ticket.sla_due.isnot(None))
        if start_dt:
            query = query.filter(Ticket.created_at >= start_dt)
        if end_dt:
            query = query.filter(Ticket.created_at <= end_dt)
        writer.writerow([
            'Ticket No', 'Title', 'Requester', 'Requester Department', 'Requester Branch',
            'Assigned User', 'Assigned Department', 'Support Group', 'Status', 'Priority',
            'SLA Due', 'Resolved At', 'SLA Status', 'SLA Breach Owner', 'Breach Hours'
        ])
        for ticket in query.order_by(Ticket.sla_due.desc()).all():
            missed = ticket.status not in ('resolved', 'closed') and ticket.sla_due and ticket.sla_due < now
            if ticket.resolved_at and ticket.sla_due:
                missed = ticket.resolved_at > ticket.sla_due
            breach_reference = ticket.resolved_at if ticket.resolved_at else now
            breach_hours = ''
            if missed and ticket.sla_due:
                breach_hours = round((breach_reference - ticket.sla_due).total_seconds() / 3600, 2)
            breach_owner = ticket.assignee.name if ticket.assignee else (ticket.support_group or 'Unassigned')
            writer.writerow([
                ticket.ticket_number or ticket.id,
                ticket.title,
                ticket.creator.name if ticket.creator else '',
                ticket.creator.department.name if ticket.creator and ticket.creator.department else '',
                ticket.creator.branch if ticket.creator and ticket.creator.branch else '',
                ticket.assignee.name if ticket.assignee else '',
                ticket.assignee.department.name if ticket.assignee and ticket.assignee.department else '',
                ticket.support_group or '',
                ticket.status,
                ticket.priority,
                ticket.sla_due.strftime('%Y-%m-%d %H:%M') if ticket.sla_due else '',
                ticket.resolved_at.strftime('%Y-%m-%d %H:%M') if ticket.resolved_at else '',
                'Missed' if missed else 'Met',
                breach_owner if missed else '',
                breach_hours,
            ])
    else:
        flash('Unknown report export.', 'danger')
        return redirect(url_for('admin.reports'))

    filename = f'helpdesk_{report_type}_report_{now.strftime("%Y%m%d_%H%M")}.csv'
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )
