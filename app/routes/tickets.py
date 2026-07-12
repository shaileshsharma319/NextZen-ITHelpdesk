from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime, timedelta
from app import db
from sqlalchemy import or_
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.models.reply import TicketReply, TicketActivity, TicketAttachment, TicketReplyTemplate
from app.models.user import User
from app.models.asset import Asset
from app.utils.assignment import apply_auto_assignment
from app.utils.email import send_ticket_created, send_ticket_updated, send_ticket_assigned, send_email_ticket_notification, send_ticket_reply, fetch_inbound_email_tickets, friendly_email_error
from app.utils.locations import location_code_for_name

tickets = Blueprint('tickets', __name__)

SLA_HOURS = {'low': 72, 'medium': 24, 'high': 8, 'critical': 4}
VALID_TICKET_STATUSES = {'open', 'in_progress', 'pending', 'resolved', 'closed'}
SOURCE_LABELS = {
    'manual': ('Manual', 'fa-pen', 'badge-source-manual'),
    'email': ('Email', 'fa-envelope', 'badge-source-email'),
    'phone': ('Phone', 'fa-phone', 'badge-source-phone'),
    'walk_in': ('Walk-In', 'fa-person-walking', 'badge-source-walk_in'),
    'self_service': ('Self-Service', 'fa-user-check', 'badge-source-self_service'),
}
TICKET_SOURCE_CODES = {
    'manual': 'MN',
    'email': 'EM',
    'phone': 'PH',
    'walk_in': 'WK',
    'self_service': 'SS',
}
TICKET_LOCATION_CODES = {
    'mumbai': 'MUM',
    'mulund': 'MUM',
    'pune': 'PUN',
    'delhi': 'DEL',
    'new delhi': 'DEL',
    'bangalore': 'BLR',
    'bengaluru': 'BLR',
    'hyderabad': 'HYD',
    'chennai': 'CHE',
    'kolkata': 'KOL',
    'ahmedabad': 'AMD',
}

TICKET_CATEGORY_MAP = {
    'Hardware': [
        'Desktop / Laptop', 'Monitor', 'Keyboard / Mouse', 'Printer', 'Scanner',
        'UPS / Power', 'CCTV / Camera', 'Biometric Device', 'Mobile Device',
        'Peripheral', 'Other Hardware',
    ],
    'Software': [
        'Operating System', 'Office Suite', 'ERP / CRM', 'Antivirus', 'Browser',
        'Driver', 'License Activation', 'Application Error', 'Patch / Update',
        'Uninstall Request', 'Other Software',
    ],
    'Software Installation': [
        'Other Software',
    ],
    'Network': [
        'No Connectivity', 'Slow Speed', 'VPN', 'Wi-Fi', 'LAN Port', 'Switch / Router',
        'Firewall', 'DNS / DHCP', 'Internet Down', 'Other Network',
    ],
    'Internet & ISP': [
        'Internet Down', 'Slow Internet', 'ISP Link Flapping', 'Static IP Issue',
        'Public IP Change', 'Bandwidth Upgrade', 'Router Handover', 'Other ISP',
    ],
    'Email': [
        'Cannot Send', 'Cannot Receive', 'Spam / Phishing', 'Configuration',
        'Mailbox Full', 'Password / MFA', 'Distribution List', 'Signature Issue',
        'Other Email',
    ],
    'Access & Permissions': [
        'New Access Request', 'Revoke Access', 'Password Reset', 'Role Change',
        'Account Locked', 'MFA / OTP', 'Folder Permission', 'Application Permission',
        'Other Access',
    ],
    'Data & File Share': [
        'Shared Folder Access', 'File Restore', 'Data Migration', 'OneDrive / SharePoint',
        'Google Drive', 'File Server Issue', 'Quota Increase', 'Deleted File Recovery',
        'Other Data Request',
    ],
    'Asset Request': [
        'Laptop Request', 'Desktop Request', 'Monitor Request', 'Keyboard / Mouse',
        'Headset', 'Phone', 'Replacement', 'Return / Handover', 'Other Asset Request',
    ],
    'Endpoint Management': [
        'OS Imaging', 'Patch Deployment', 'MDM Enrollment', 'Device Encryption',
        'Remote Wipe', 'Endpoint Compliance', 'Agent Installation', 'Other Endpoint',
    ],
    'Security': [
        'Malware / Virus', 'Phishing Report', 'Suspicious Login', 'Data Loss',
        'Policy Violation', 'Endpoint Alert', 'Other Security',
    ],
    'Compliance / Audit': [
        'Audit Evidence', 'Policy Acknowledgement', 'Access Review', 'Asset Verification',
        'License Compliance', 'Security Exception', 'Control Failure', 'Other Compliance',
    ],
    'Server': [
        'Server Down', 'Service Restart', 'Storage Full', 'Backup / Restore',
        'Patch / Update', 'Performance', 'Other Server',
    ],
    'Database': [
        'Database Down', 'User Access', 'Backup / Restore', 'Performance',
        'Query Support', 'Storage Growth', 'Replication Issue', 'Other Database',
    ],
    'Backup & Recovery': [
        'Backup Failed', 'Restore Request', 'Backup Report', 'Retention Change',
        'DR Drill', 'Snapshot Issue', 'Other Backup',
    ],
    'Cloud / SaaS': [
        'Microsoft 365', 'Google Workspace', 'Azure', 'AWS', 'Hosting / Domain',
        'SaaS Access', 'Other Cloud',
    ],
    'Website / Domain': [
        'Website Down', 'DNS Change', 'SSL Certificate', 'Domain Renewal',
        'Hosting Issue', 'Content Update', 'Redirect Request', 'Other Website',
    ],
    'Telephony': [
        'Extension Issue', 'Call Quality', 'Phone Setup', 'IVR / Routing',
        'Mobile SIM', 'Other Telephony',
    ],
    'Meeting Room / AV': [
        'Projector', 'Conference Phone', 'Teams Room', 'Camera / Mic',
        'Display Issue', 'Cable / Adapter', 'Other AV',
    ],
    'Remote Work': [
        'VPN Setup', 'VDI / Remote Desktop', 'Home Wi-Fi Guidance', 'Remote Access Issue',
        'Laptop Courier', 'Other Remote Work',
    ],
    'Vendor / Procurement': [
        'Vendor Support', 'Warranty Claim', 'Purchase Request', 'Quotation',
        'AMC Renewal', 'Repair Follow-up', 'Other Vendor',
    ],
    'Facilities IT': [
        'Desk Setup', 'Network Point', 'Power Point', 'Printer Placement',
        'CCTV Support', 'Biometric Setup', 'Other Facilities IT',
    ],
    'Onboarding / Offboarding': [
        'New Joiner Setup', 'Exit Clearance', 'Email Creation', 'Asset Allocation',
        'Access Provisioning', 'Access Removal',
    ],
    'Training / How-To': [
        'Software How-To', 'Email Training', 'Security Awareness', 'Portal Guidance',
        'Knowledge Base Request', 'Other Training',
    ],
    'Other': ['General Inquiry', 'Other'],
}

ALLOWED_ATTACHMENT_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'doc', 'docx',
    'xls', 'xlsx', 'csv', 'ppt', 'pptx', 'zip', 'log'
}
DEFAULT_REPLY_TEMPLATES = [
    {
        'name': 'Request More Information',
        'category': 'Public',
        'body': '<p>Hi,</p><p>Thanks for contacting IT HelpDesk. Could you please share a little more detail about the issue, including any error message, screenshot, and the time it started?</p><p>Regards,<br>IT Support</p>',
        'is_internal': False,
    },
    {
        'name': 'Issue Resolved',
        'category': 'Public',
        'body': '<p>Hi,</p><p>We have completed the requested work and marked this ticket as resolved. Please reply if you still see the issue.</p><p>Regards,<br>IT Support</p>',
        'is_internal': False,
    },
    {
        'name': 'Internal Troubleshooting',
        'category': 'Internal',
        'body': '<p><strong>Internal note:</strong></p><ul><li>Observed:</li><li>Action taken:</li><li>Next step:</li></ul>',
        'is_internal': True,
    },
]


def user_can_view_ticket(ticket):
    return (
        current_user.can_view_all_tickets
        or ticket.user_id == current_user.id
        or ticket.assigned_to == current_user.id
    )


def user_can_edit_ticket(ticket):
    return current_user.can_manage_helpdesk or (
        ticket.user_id == current_user.id and ticket.status not in ('resolved', 'closed')
    )


def allowed_attachment(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_ATTACHMENT_EXTENSIONS


def assignable_ticket_owners():
    return [
        user for user in User.query.filter(User._is_active.is_(True)).order_by(User.role, User.name).all()
        if user.can_manage_helpdesk
    ]


def user_location_value(user):
    return ((getattr(user, 'work_location', None) or getattr(user, 'branch', None) or '') if user else '').strip()


def normalize_location(value):
    return (value or '').strip().lower()


def location_code_for_user(user):
    stored_code = (getattr(user, 'location_code', None) or getattr(user, 'state_code', None) or '').strip().upper() if user else ''
    if stored_code:
        return stored_code
    value = user_location_value(user)
    clean = normalize_location(value)
    if not clean:
        return 'GEN'
    selected_code = location_code_for_name(value)
    if selected_code:
        return selected_code
    for key, code in TICKET_LOCATION_CODES.items():
        if key in clean:
            return code
    letters = ''.join(ch for ch in clean.upper() if ch.isalpha())
    return (letters[:3] or 'GEN').ljust(3, 'X')


def location_filter_for_user(user):
    location = normalize_location(user_location_value(user))
    if not location:
        return None
    matching_user_ids = [
        item.id for item in User.query.filter(User._is_active.is_(True)).all()
        if normalize_location(user_location_value(item)) == location
    ]
    return matching_user_ids or None


def normalize_ticket_tags(value):
    tags = []
    for tag in (value or '').replace('\n', ',').split(','):
        clean = tag.strip().strip('#')
        if clean and clean.lower() not in [item.lower() for item in tags]:
            tags.append(clean[:40])
    return ', '.join(tags[:12]) or None


def software_option_label(software):
    return f'{software.name} {software.version}'.strip() if software.version else software.name


def build_category_map(software_list=None):
    category_map = {category: items.copy() for category, items in TICKET_CATEGORY_MAP.items()}
    if software_list is not None:
        software_names = []
        seen = set()
        for software in software_list:
            label = software_option_label(software)
            key = label.lower()
            if key not in seen:
                seen.add(key)
                software_names.append(label)
        category_map['Software Installation'] = software_names + ['Other Software']
    return category_map


def software_id_from_subcategory(sub_category):
    if not sub_category:
        return None
    from app.models.software import Software
    software = Software.query.order_by(Software.name).all()
    for item in software:
        if software_option_label(item).lower() == sub_category.strip().lower():
            return item.id
    return None


def ticket_upload_folder(ticket_id):
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'tickets', str(ticket_id))
    os.makedirs(folder, exist_ok=True)
    return folder


def save_reply_attachments(ticket, reply):
    saved = []
    for upload in request.files.getlist('attachments') + request.files.getlist('attachment'):
        if not upload or not upload.filename:
            continue
        if not allowed_attachment(upload.filename):
            flash(f'Attachment skipped: {upload.filename} is not an allowed file type.', 'warning')
            continue
        original = secure_filename(upload.filename)
        ext = original.rsplit('.', 1)[1].lower() if '.' in original else ''
        stored = f'{uuid.uuid4().hex}.{ext}' if ext else uuid.uuid4().hex
        upload_path = os.path.join(ticket_upload_folder(ticket.id), stored)
        upload.save(upload_path)
        attachment = TicketAttachment(
            ticket_id=ticket.id,
            reply_id=reply.id,
            original_filename=original,
            stored_filename=stored,
            content_type=upload.mimetype,
            file_size=os.path.getsize(upload_path),
            uploaded_by=current_user.id,
        )
        db.session.add(attachment)
        saved.append(attachment)
    return saved


def ensure_default_reply_templates():
    if TicketReplyTemplate.query.first():
        return
    for item in DEFAULT_REPLY_TEMPLATES:
        db.session.add(TicketReplyTemplate(**item))
    db.session.commit()


def generate_ticket_number(source='manual', user=None, location_code=None):
    today = datetime.utcnow().strftime('%Y%m%d')
    source_code = TICKET_SOURCE_CODES.get(source, 'MN')
    location_code = (location_code or location_code_for_user(user)).strip().upper()
    last = Ticket.query.order_by(Ticket.id.desc()).first()
    next_id = (last.id + 1) if last else 1
    while True:
        ticket_number = f'{location_code}-HD-{source_code}-{today}{next_id:06d}'
        if not Ticket.query.filter_by(ticket_number=ticket_number).first():
            return ticket_number
        next_id += 1


@tickets.route('/')
@login_required
def list():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    ticket_type = request.args.get('ticket_type', '')
    source = request.args.get('source', '')
    tag = request.args.get('tag', '').strip()
    location = request.args.get('location', '').strip()
    q = request.args.get('q', '').strip()

    base_query = Ticket.query
    if not current_user.can_view_all_tickets:
        if current_user.can_manage_helpdesk:
            location_user_ids = location_filter_for_user(current_user)
            location_condition = Ticket.user_id.in_(location_user_ids) if location_user_ids else Ticket.user_id == current_user.id
            base_query = base_query.filter(or_(
                Ticket.user_id == current_user.id,
                Ticket.assigned_to == current_user.id,
                location_condition,
            ))
        else:
            base_query = base_query.filter(or_(
                Ticket.user_id == current_user.id,
                Ticket.assigned_to == current_user.id,
            ))

    metrics = {
        'total': base_query.count(),
        'open': base_query.filter_by(status='open').count(),
        'in_progress': base_query.filter_by(status='in_progress').count(),
        'pending': base_query.filter_by(status='pending').count(),
        'resolved': base_query.filter_by(status='resolved').count(),
        'closed': base_query.filter_by(status='closed').count(),
        'overdue': base_query.filter(Ticket.sla_due.isnot(None), Ticket.sla_due < datetime.utcnow(), Ticket.status.notin_(['resolved', 'closed'])).count(),
        'email': base_query.filter_by(source='email').count(),
        'unassigned': base_query.filter(Ticket.assigned_to.is_(None)).count(),
        'critical': base_query.filter_by(priority='critical').count(),
    }

    query = base_query
    if q:
        like_q = f'%{q}%'
        query = query.filter(or_(
            Ticket.ticket_number.ilike(like_q),
            Ticket.title.ilike(like_q),
            Ticket.description.ilike(like_q),
            Ticket.email_from.ilike(like_q),
            Ticket.category.ilike(like_q),
            Ticket.tags.ilike(like_q),
        ))
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if ticket_type:
        query = query.filter_by(ticket_type=ticket_type)
    if source:
        query = query.filter_by(source=source)
    if tag:
        query = query.filter(Ticket.tags.ilike(f'%{tag}%'))
    location_options = []
    if current_user.can_view_all_tickets:
        users_for_locations = User.query.filter(User._is_active.is_(True)).order_by(User.work_location, User.branch, User.name).all()
        seen_locations = set()
        for user in users_for_locations:
            loc_value = user_location_value(user)
            loc_key = normalize_location(loc_value)
            if loc_key and loc_key not in seen_locations:
                seen_locations.add(loc_key)
                location_options.append(loc_value)
        if location:
            location_ids = [
                user.id for user in users_for_locations
                if normalize_location(user_location_value(user)) == normalize_location(location)
            ]
            query = query.filter(Ticket.user_id.in_(location_ids or [-1]))

    tickets_list = query.order_by(Ticket.created_at.desc()).paginate(page=page, per_page=10)
    return render_template('tickets/list.html', tickets=tickets_list,
                           status=status, priority=priority, ticket_type=ticket_type,
                           source=source, tag=tag, location=location, location_options=location_options,
                           q=q, metrics=metrics,
                           source_labels=SOURCE_LABELS, now=datetime.utcnow())


@tickets.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        priority = request.form.get('priority', 'medium')
        source   = request.form.get('source', 'manual')
        title    = request.form.get('title', '').strip()
        description = request.form.get('description', '')
        is_draft = request.form.get('save_draft') == '1'

        if not current_user.can_view_all_tickets:
            source = 'self_service'

        if source == 'email':
            to      = request.form.get('email_to', '')
            cc      = request.form.get('email_cc', '')
            bcc     = request.form.get('email_bcc', '')
            recv    = request.form.get('email_received', '')
            client  = request.form.get('email_source_client', '')
            header  = ''
            if to:     header += f'To: {to}\n'
            if cc:     header += f'CC: {cc}\n'
            if bcc:    header += f'BCC: {bcc}\n'
            if recv:   header += f'Received: {recv}\n'
            if client: header += f'Client: {client}\n'
            if header: description = f'{header}\n{description}'

        due_date_str = request.form.get('due_date', '')
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        support_group = None
        assigned_to_id = None
        requested_status = 'open'
        manual_assignment = False
        if current_user.can_view_all_tickets:
            support_group = request.form.get('support_group') or None
            requested_status = request.form.get('status', 'open')
            if requested_status not in VALID_TICKET_STATUSES:
                requested_status = 'open'
            assigned_to_id = request.form.get('assigned_to', type=int)
            if assigned_to_id:
                valid_owners = {user.id: user for user in assignable_ticket_owners()}
                selected_owner = valid_owners.get(assigned_to_id)
                selected_owner_group = selected_owner.department.name if selected_owner and selected_owner.department else ''
                if selected_owner and (not support_group or selected_owner_group == support_group):
                    manual_assignment = True
                else:
                    assigned_to_id = None
                    flash('Selected owner is not valid for the selected support group. Ticket was created without manual ownership.', 'warning')
            if is_draft:
                requested_status = 'open'

        selected_asset_id = None
        if current_user.can_view_all_tickets:
            selected_asset_id = request.form.get('asset_id') or None
        else:
            user_asset_ids = [
                asset.id for asset in Asset.query.filter_by(assigned_user_id=current_user.id).all()
            ]
            posted_asset_id = request.form.get('asset_id', type=int)
            if posted_asset_id in user_asset_ids:
                selected_asset_id = posted_asset_id
            elif user_asset_ids:
                selected_asset_id = user_asset_ids[0]

        ticket = Ticket(
            ticket_number=generate_ticket_number(source, current_user),
            title=title,
            description=description,
            ticket_type=request.form.get('ticket_type', 'incident'),
            priority=priority,
            status=requested_status,
            category=request.form.get('category') or None,
            tags=normalize_ticket_tags(request.form.get('tags')),
            sub_category=request.form.get('sub_category') or None,
            source=source,
            impact=request.form.get('impact', 'medium'),
            urgency=request.form.get('urgency', 'medium'),
            support_group=support_group,
            assigned_to=assigned_to_id,
            asset_id=selected_asset_id,
            software_id=software_id_from_subcategory(request.form.get('sub_category')) if request.form.get('category') == 'Software Installation' else (int(request.form.get('software_id')) if request.form.get('software_id') else None),
            due_date=due_date,
            user_id=current_user.id,
            sla_due=datetime.utcnow() + timedelta(hours=SLA_HOURS[priority]),
            email_message_id=request.form.get('email_message_id') or None,
            email_from=request.form.get('email_to') or None,
            email_to=request.form.get('email_from') or None,
            email_cc=request.form.get('email_cc') or None,
            email_subject=request.form.get('email_subject') or title,
            is_auto_generated=(source == 'email'),
        )
        if requested_status in ('resolved', 'closed'):
            ticket.resolved_at = datetime.utcnow()
        db.session.add(ticket)
        db.session.flush()
        if support_group:
            db.session.add(TicketActivity(
                ticket_id=ticket.id,
                activity_type='assignment',
                description=f'Support group set to {support_group} during ticket creation',
                user_id=current_user.id,
            ))
        if manual_assignment:
            assignee = User.query.get(assigned_to_id)
            db.session.add(TicketActivity(
                ticket_id=ticket.id,
                activity_type='assignment',
                description=f'Ticket assigned to {assignee.name if assignee else "selected owner"} during ticket creation',
                user_id=current_user.id,
            ))
        apply_auto_assignment(ticket, current_user.id)
        if current_user.can_view_all_tickets and requested_status != 'open':
            ticket.status = requested_status
        db.session.commit()
        if manual_assignment:
            try:
                send_ticket_assigned(ticket, ticket.assignee)
            except Exception:
                pass
        if is_draft:
            flash('Ticket saved as draft.', 'info')
            return redirect(url_for('tickets.detail', ticket_id=ticket.id))
        try:
            send_ticket_created(ticket, current_user)
            flash('Ticket created successfully!', 'success')
        except Exception as e:
            flash(f'Ticket created, but notification email failed: {e}', 'warning')
        if source == 'email':
            try:
                from app.models.email_config import EmailConfig
                cfg = EmailConfig.get()
                send_email_ticket_notification(ticket, cfg.mail_from if cfg else '')
            except Exception:
                pass
        return redirect(url_for('tickets.detail', ticket_id=ticket.id))

    from app.models.department import Department
    from app.models.email_config import EmailConfig
    from app.models.software import Software
    departments  = Department.query.order_by(Department.name).all()
    staff_users  = assignable_ticket_owners()
    all_assets   = Asset.query.order_by(Asset.name).all() if current_user.can_view_all_tickets else Asset.query.filter_by(assigned_user_id=current_user.id).order_by(Asset.name).all()
    default_asset = all_assets[0] if all_assets and not current_user.can_view_all_tickets else None
    all_software = Software.query.order_by(Software.name).all()
    category_map = build_category_map(all_software)
    software_subcategory_map = {software_option_label(item): item.id for item in all_software}
    email_cfg    = EmailConfig.get()
    return render_template('tickets/create.html',
                           departments=departments, staff_users=staff_users,
                           all_assets=all_assets, default_asset=default_asset, all_software=all_software,
                           source_labels=SOURCE_LABELS, email_cfg=email_cfg,
                           category_map=category_map, software_subcategory_map=software_subcategory_map)


@tickets.route('/fetch-email', methods=['POST'])
@login_required
def fetch_email_tickets():
    if not current_user.can_view_all_tickets:
        flash('Access denied.', 'danger')
        return redirect(url_for('tickets.list'))
    created, error = fetch_inbound_email_tickets()
    if error:
        flash(f'Email fetch failed: {error}', 'danger')
    else:
        flash(f'{created} email ticket(s) imported.', 'success')
    return redirect(url_for('tickets.list'))


@tickets.route('/<int:ticket_id>')
@login_required
def detail(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if not user_can_view_ticket(ticket):
        flash('Access denied.', 'danger')
        return redirect(url_for('tickets.list'))
    if not user_can_edit_ticket(ticket):
        flash('Only Helpdesk agents can edit resolved or closed tickets.', 'danger')
        return redirect(url_for('tickets.detail', ticket_id=ticket.id))
    staff_users = assignable_ticket_owners()
    if (
        current_user.can_view_all_tickets
        and ticket.assigned_to is None
        and ticket.status not in ('resolved', 'closed')
    ):
        ticket.assigned_to = current_user.id
        db.session.add(TicketActivity(
            ticket_id=ticket.id,
            activity_type='assignment',
            description=f'Ticket auto-assigned to {current_user.name} when opened',
            user_id=current_user.id,
        ))
    db.session.commit()
    return render_template('tickets/detail.html', ticket=ticket, staff_users=staff_users,
                           now=datetime.utcnow(), source_labels=SOURCE_LABELS,
                           )


@tickets.route('/<int:ticket_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if not user_can_view_ticket(ticket):
        flash('Access denied.', 'danger')
        return redirect(url_for('tickets.list'))
    if request.method == 'POST':
        old_status = ticket.status
        ticket.title       = request.form.get('title')
        ticket.description = request.form.get('description')
        ticket.ticket_type = request.form.get('ticket_type', ticket.ticket_type)
        ticket.priority    = request.form.get('priority')
        ticket.category    = request.form.get('category') or None
        ticket.tags        = normalize_ticket_tags(request.form.get('tags'))
        ticket.sub_category= request.form.get('sub_category') or None
        if current_user.can_manage_helpdesk:
            ticket.source = request.form.get('source', ticket.source)
        ticket.impact      = request.form.get('impact', ticket.impact)
        ticket.urgency     = request.form.get('urgency', ticket.urgency)
        ticket.asset_id    = request.form.get('asset_id') or None
        ticket.software_id = software_id_from_subcategory(request.form.get('sub_category')) if ticket.category == 'Software Installation' else (int(request.form.get('software_id')) if request.form.get('software_id') else None)
        due_date_str = request.form.get('due_date', '')
        if due_date_str:
            try:
                ticket.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        else:
            ticket.due_date = None
        if current_user.can_manage_helpdesk:
            new_status = request.form.get('status')
            ticket.status = new_status
            ticket.support_group = request.form.get('support_group') or None
            assigned_to = request.form.get('assigned_to')
            ticket.assigned_to = int(assigned_to) if assigned_to else None
            if new_status == 'resolved' and not ticket.resolved_at:
                ticket.resolved_at = datetime.utcnow()
            if ticket.assigned_to:
                assignee = User.query.get(ticket.assigned_to)
                try:
                    send_ticket_assigned(ticket, assignee)
                except Exception:
                    pass
        db.session.commit()
        if old_status != ticket.status:
            try:
                send_ticket_updated(ticket, ticket.creator)
            except Exception:
                pass
        flash('Ticket updated!', 'success')
        return redirect(url_for('tickets.detail', ticket_id=ticket.id))
    from app.models.department import Department
    from app.models.software import Software
    from app.models.email_config import EmailConfig
    departments  = Department.query.order_by(Department.name).all()
    staff_users  = assignable_ticket_owners()
    all_assets   = Asset.query.order_by(Asset.name).all()
    all_software = Software.query.order_by(Software.name).all()
    category_map = build_category_map(all_software)
    software_subcategory_map = {software_option_label(item): item.id for item in all_software}
    email_cfg    = EmailConfig.get()
    return render_template('tickets/edit.html', ticket=ticket,
                           departments=departments, staff_users=staff_users,
                           all_assets=all_assets, all_software=all_software,
                           source_labels=SOURCE_LABELS, email_cfg=email_cfg,
                           category_map=category_map, software_subcategory_map=software_subcategory_map)


@tickets.route('/<int:ticket_id>/reply', methods=['GET', 'POST'])
@login_required
def add_reply(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if not user_can_view_ticket(ticket):
        flash('Access denied.', 'danger')
        return redirect(url_for('tickets.list'))

    if request.method == 'GET':
        ensure_default_reply_templates()
        staff_users = assignable_ticket_owners()
        templates = TicketReplyTemplate.query.filter_by(is_active=True).order_by(
            TicketReplyTemplate.category, TicketReplyTemplate.name
        ).all()
        if not current_user.can_manage_helpdesk:
            templates = [template for template in templates if not template.is_internal]
        return render_template('tickets/reply.html', ticket=ticket, staff_users=staff_users,
                               reply_templates=templates, now=datetime.utcnow(),
                               source_labels=SOURCE_LABELS)

    if ticket.status == 'closed':
        flash('This ticket is closed. Re-open it before replying.', 'warning')
        return redirect(url_for('tickets.add_reply', ticket_id=ticket_id))

    reply_type = request.form.get('reply_type', 'public')
    action = request.form.get('action', 'reply')
    message = request.form.get('message', '').strip()
    text_only = message.replace('<p><br></p>', '').replace('<br>', '').strip()

    if reply_type not in ('public', 'internal', 'email'):
        reply_type = 'public'
    if reply_type == 'internal' and not current_user.can_manage_helpdesk:
        reply_type = 'public'
    if not text_only:
        flash('Reply message cannot be empty.', 'danger')
        return redirect(request.referrer or url_for('tickets.add_reply', ticket_id=ticket_id))

    old_status = ticket.status
    old_assignee = ticket.assigned_to
    is_public = reply_type != 'internal'
    reply = TicketReply(
        ticket_id=ticket_id,
        reply_type=reply_type,
        message=message,
        user_id=current_user.id,
        is_public=is_public,
    )
    db.session.add(reply)
    db.session.flush()

    attachments = save_reply_attachments(ticket, reply)
    if attachments and not reply.attachment_path:
        reply.attachment_path = attachments[0].stored_filename

    activity_map = {'public': 'Public reply', 'internal': 'Internal note', 'email': 'Email reply'}
    description = f'{activity_map.get(reply_type, "Reply")} added by {current_user.name}'
    if attachments:
        description += f' with {len(attachments)} attachment(s)'
    db.session.add(TicketActivity(ticket_id=ticket_id, activity_type='reply',
                                  description=description, user_id=current_user.id))

    if current_user.can_manage_helpdesk:
        new_status = request.form.get('status')
        assigned_to = request.form.get('assigned_to')
        if action == 'resolve':
            new_status = 'resolved'
        elif action == 'close':
            new_status = 'closed'
        if new_status in ('open', 'in_progress', 'pending', 'resolved', 'closed'):
            ticket.status = new_status
            if new_status == 'resolved' and not ticket.resolved_at:
                ticket.resolved_at = datetime.utcnow()
            elif new_status not in ('resolved', 'closed'):
                ticket.resolved_at = None
        ticket.assigned_to = int(assigned_to) if assigned_to else None

    if old_status != ticket.status:
        db.session.add(TicketActivity(ticket_id=ticket_id, activity_type='status_change',
                                      description=f'Status changed from {old_status.replace("_", " ").title()} to {ticket.status.replace("_", " ").title()} by {current_user.name}',
                                      user_id=current_user.id))
    if old_assignee != ticket.assigned_to:
        assignee = User.query.get(ticket.assigned_to) if ticket.assigned_to else None
        assignee_name = assignee.name if assignee else 'Unassigned'
        db.session.add(TicketActivity(ticket_id=ticket_id, activity_type='assignment',
                                      description=f'Ticket assigned to {assignee_name} by {current_user.name}',
                                      user_id=current_user.id))
        if assignee:
            try:
                send_ticket_assigned(ticket, assignee)
            except Exception:
                pass

    db.session.commit()
    if reply.is_public:
        try:
            send_ticket_reply(ticket, reply, attachments)
            db.session.add(TicketActivity(ticket_id=ticket_id, activity_type='email_sent',
                                          description=f'Reply emailed to {ticket.email_from or ticket.creator.email}',
                                          user_id=current_user.id))
            db.session.commit()
        except Exception as e:
            flash(f'Reply saved, but email delivery failed: {friendly_email_error(e)}', 'warning')
    if old_status != ticket.status:
        try:
            send_ticket_updated(ticket, ticket.creator)
        except Exception:
            pass

    if action == 'resolve':
        flash('Reply added and ticket resolved.', 'success')
    elif action == 'close':
        flash('Reply added and ticket closed.', 'success')
    elif reply_type == 'internal':
        flash('Internal note added.', 'success')
    else:
        flash('Reply added.', 'success')
    return_to = request.form.get('return_to', 'reply')
    if return_to == 'detail':
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))
    return redirect(url_for('tickets.add_reply', ticket_id=ticket_id))


@tickets.route('/attachments/<int:attachment_id>/download')
@login_required
def download_attachment(attachment_id):
    attachment = TicketAttachment.query.get_or_404(attachment_id)
    ticket = attachment.ticket
    if not user_can_view_ticket(ticket):
        abort(403)
    folder = ticket_upload_folder(ticket.id)
    return send_from_directory(folder, attachment.stored_filename,
                               as_attachment=True,
                               download_name=attachment.original_filename)


@tickets.route('/<int:ticket_id>/quick-action', methods=['POST'])
@login_required
def quick_action(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if not current_user.can_manage_helpdesk:
        flash('Helpdesk agent access required.', 'danger')
        return redirect(url_for('tickets.detail', ticket_id=ticket.id))
    action = request.form.get('action')
    if action == 'resolve':
        ticket.status = 'resolved'
        ticket.resolved_at = datetime.utcnow()
        db.session.add(TicketActivity(ticket_id=ticket_id, activity_type='status_change',
                                      description=f'Ticket resolved by {current_user.name}', user_id=current_user.id))
        flash('Ticket resolved.', 'success')
    elif action == 'close':
        ticket.status = 'closed'
        db.session.add(TicketActivity(ticket_id=ticket_id, activity_type='status_change',
                                      description=f'Ticket closed by {current_user.name}', user_id=current_user.id))
        flash('Ticket closed.', 'success')
    db.session.commit()
    return redirect(url_for('tickets.detail', ticket_id=ticket_id))


@tickets.route('/<int:ticket_id>/comment', methods=['POST'])
@login_required
def add_comment(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if not user_can_view_ticket(ticket):
        flash('Access denied.', 'danger')
        return redirect(url_for('tickets.list'))
    content = request.form.get('content')
    if content:
        comment = Comment(content=content, ticket_id=ticket.id, user_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
        flash('Comment added.', 'success')
    return redirect(url_for('tickets.detail', ticket_id=ticket.id))


@tickets.route('/<int:ticket_id>/delete', methods=['POST'])
@login_required
def delete(ticket_id):
    if not current_user.can_manage_system:
        flash('Access denied.', 'danger')
        return redirect(url_for('tickets.list'))
    ticket = Ticket.query.get_or_404(ticket_id)
    db.session.delete(ticket)
    db.session.commit()
    flash('Ticket deleted.', 'success')
    return redirect(url_for('tickets.list'))
