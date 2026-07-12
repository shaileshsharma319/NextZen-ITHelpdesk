import base64
import os
import re
import zipfile
from html import escape
from io import BytesIO
from datetime import date, datetime
from functools import wraps
from uuid import uuid4

from flask import Blueprint, abort, current_app, flash, make_response, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.models.audit import (
    AuditCorrectiveAction,
    AuditFinding,
    AuditPlan,
    AuditPolicy,
    AuditPolicyAcknowledgement,
    AuditPolicyAttachment,
)
from app.models.department import Department
from app.models.user import User

audit = Blueprint('audit', __name__)

POLICY_CATEGORIES = [
    'IT Security',
    'Access Control',
    'Data Privacy',
    'Asset Management',
    'HR Policy',
    'Finance',
    'Operations',
    'Vendor Management',
    'Business Continuity',
    'Compliance',
]

RISK_LEVELS = ['low', 'medium', 'high', 'critical']
POLICY_STATUSES = ['draft', 'active', 'under_review', 'retired']
AUDIT_TYPES = ['internal', 'external', 'vendor', 'security', 'process', 'compliance']
AUDIT_STATUSES = ['planned', 'in_progress', 'completed', 'cancelled']
FINDING_STATUSES = ['open', 'in_progress', 'accepted', 'closed']
ACTION_STATUSES = ['open', 'in_progress', 'completed', 'blocked']
ALLOWED_POLICY_ATTACHMENT_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'pdf', 'doc', 'docx',
    'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv'
}


def can_manage_audit():
    return (
        current_user.can_manage_system
        or current_user.can_manage_compliance
    )


def audit_manager_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not can_manage_audit():
            flash('Audit management access required.', 'danger')
            return redirect(url_for('audit.index'))
        return f(*args, **kwargs)
    return decorated


def parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def allowed_policy_attachment(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_POLICY_ATTACHMENT_EXTENSIONS


def policy_upload_folder(policy_id):
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'audit_policies', str(policy_id))
    os.makedirs(folder, exist_ok=True)
    return folder


def save_policy_attachments(policy):
    saved = 0
    uploads = request.files.getlist('evidence_attachments') + request.files.getlist('attachments')
    for upload in uploads:
        if not upload or not upload.filename:
            continue
        if not allowed_policy_attachment(upload.filename):
            flash(f'Attachment skipped: {upload.filename} is not an allowed file type.', 'warning')
            continue
        original = secure_filename(upload.filename)
        ext = original.rsplit('.', 1)[1].lower() if '.' in original else ''
        stored = f'{uuid4().hex}.{ext}' if ext else uuid4().hex
        path = os.path.join(policy_upload_folder(policy.id), stored)
        upload.save(path)
        db.session.add(AuditPolicyAttachment(
            policy_id=policy.id,
            original_filename=original,
            stored_filename=stored,
            content_type=upload.mimetype,
            file_size=os.path.getsize(path),
            uploaded_by=current_user.id,
        ))
        saved += 1
    if saved:
        policy.updated_at = datetime.utcnow()
    return saved


def policy_attachment_data_uri(attachment):
    if not attachment.is_image:
        return None
    path = os.path.join(policy_upload_folder(attachment.policy_id), attachment.stored_filename)
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as handle:
        encoded = base64.b64encode(handle.read()).decode('ascii')
    return f'data:{attachment.content_type or "image/png"};base64,{encoded}'


def policy_step_evidence(policy, include_data_uri=False):
    image_attachments = sorted(
        [attachment for attachment in policy.attachments if attachment.is_image],
        key=lambda item: item.id,
    )
    numbered_steps = []
    extra_lines = []
    for line in (policy.controls or '').splitlines():
        clean = line.strip()
        if not clean:
            continue
        if re.match(r'^\d+[\.\)]\s+', clean):
            numbered_steps.append(clean)
        else:
            extra_lines.append(clean)

    steps = []
    for index, step in enumerate(numbered_steps):
        attachment = image_attachments[index] if index < len(image_attachments) else None
        steps.append({
            'text': step,
            'attachment': attachment,
            'data_uri': policy_attachment_data_uri(attachment) if include_data_uri and attachment else None,
        })

    remaining_images = image_attachments[len(numbered_steps):]
    return steps, remaining_images, extra_lines


def policy_form_steps(policy):
    steps, _remaining_images, extra_lines = policy_step_evidence(policy)
    form_steps = [item['text'] for item in steps]
    while len(form_steps) < 4:
        form_steps.append('')
    return form_steps, '\n'.join(extra_lines)


def _xml_text(value):
    return escape(str(value or ''), quote=False)


def _docx_paragraph(text='', bold=False, size='22', center=False):
    safe = _xml_text(text)
    bold_xml = '<w:b/>' if bold else ''
    align_xml = '<w:pPr><w:jc w:val="center"/></w:pPr>' if center else ''
    return (
        '<w:p>'
        f'{align_xml}'
        '<w:r>'
        f'<w:rPr>{bold_xml}<w:sz w:val="{size}"/></w:rPr>'
        f'<w:t xml:space="preserve">{safe}</w:t>'
        '</w:r>'
        '</w:p>'
    )


def _docx_multiline(text):
    lines = (text or '').splitlines() or ['']
    return ''.join(_docx_paragraph(line) for line in lines)


def _docx_table(rows):
    cells = []
    for row in rows:
        cells.append('<w:tr>')
        for label, value in row:
            cells.append(
                '<w:tc><w:tcPr><w:tcW w:w="2400" w:type="dxa"/></w:tcPr>'
                f'{_docx_paragraph(label, bold=True, size="20")}'
                '</w:tc>'
                '<w:tc><w:tcPr><w:tcW w:w="3600" w:type="dxa"/></w:tcPr>'
                f'{_docx_paragraph(value, size="20")}'
                '</w:tc>'
            )
        cells.append('</w:tr>')
    borders = (
        '<w:tblPr><w:tblBorders>'
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="9CA3AF"/>'
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="9CA3AF"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="9CA3AF"/>'
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="9CA3AF"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="9CA3AF"/>'
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="9CA3AF"/>'
        '</w:tblBorders></w:tblPr>'
    )
    return f'<w:tbl>{borders}{"".join(cells)}</w:tbl>'


def _docx_image(rid, filename, index):
    cx = 7772400
    cy = 4370700
    name = _xml_text(filename)
    return f'''
    <w:p>
      <w:r>
        <w:drawing>
          <wp:inline distT="0" distB="0" distL="0" distR="0"
            xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
            <wp:extent cx="{cx}" cy="{cy}"/>
            <wp:docPr id="{index}" name="{name}"/>
            <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
              <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
                <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
                  <pic:nvPicPr><pic:cNvPr id="{index}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>
                  <pic:blipFill><a:blip r:embed="{rid}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
                  <pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
                </pic:pic>
              </a:graphicData>
            </a:graphic>
          </wp:inline>
        </w:drawing>
      </w:r>
    </w:p>
    '''


def build_policy_docx(policy):
    image_files = []
    for attachment in policy.attachments:
        if not attachment.is_image:
            continue
        ext = attachment.stored_filename.rsplit('.', 1)[-1].lower()
        if ext not in ('png', 'jpg', 'jpeg', 'gif', 'bmp'):
            continue
        path = os.path.join(policy_upload_folder(attachment.policy_id), attachment.stored_filename)
        if os.path.exists(path):
            image_files.append((attachment, path, ext))
    steps, remaining_images, extra_lines = policy_step_evidence(policy)
    image_lookup = {attachment.id: (attachment, path, ext) for attachment, path, ext in image_files}

    body = [
        _docx_paragraph(policy.title.upper(), bold=True, size='32', center=True),
        _docx_table([
            [('Policy Code', policy.code), ('Version', policy.version)],
            [('Category', policy.category or '-'), ('Risk Level', policy.risk_level.title())],
            [('Owner', policy.owner.name if policy.owner else 'Unassigned'), ('Status', policy.status.replace('_', ' ').title())],
            [('Effective Date', policy.effective_date.strftime('%d %b %Y') if policy.effective_date else '-'), ('Review Date', policy.review_date.strftime('%d %b %Y') if policy.review_date else '-')],
        ]),
        _docx_paragraph(''),
        _docx_paragraph('1. Purpose / Description :', bold=True, size='24'),
        _docx_multiline(policy.description or 'No description added.'),
        _docx_paragraph('2. Scope :', bold=True, size='24'),
        _docx_multiline(policy.scope or 'No scope added.'),
    ]

    image_relation_index = 2
    used_image_ids = set()
    if steps:
        body.append(_docx_paragraph('3. Step by Step Permission Evidence :', bold=True, size='24'))
        for step in steps:
            body.append(_docx_paragraph(step['text'], bold=True, size='22'))
            attachment = step['attachment']
            if attachment and attachment.id in image_lookup:
                used_image_ids.add(attachment.id)
                body.append(_docx_image(f'rId{image_relation_index}', attachment.original_filename, image_relation_index))
                image_relation_index += 1
        if extra_lines:
            body.append(_docx_paragraph('Additional Controls :', bold=True, size='22'))
            body.extend(_docx_paragraph(line) for line in extra_lines)
    else:
        body.append(_docx_paragraph('3. Controls and Requirements :', bold=True, size='24'))
        body.append(_docx_multiline(policy.controls or 'No controls added.'))

    unpaired_images = [item for item in image_files if item[0].id not in used_image_ids]
    if unpaired_images:
        body.append(_docx_paragraph('4. Screenshots / Evidence :', bold=True, size='24'))
        for attachment, _path, _ext in unpaired_images:
            body.append(_docx_paragraph(attachment.original_filename, size='20'))
            body.append(_docx_image(f'rId{image_relation_index}', attachment.original_filename, image_relation_index))
            image_relation_index += 1

    file_attachments = [attachment for attachment in policy.attachments if not attachment.is_image]
    if file_attachments:
        body.append(_docx_paragraph(f'{5 if image_files else 4}. Supporting Files :', bold=True, size='24'))
        for index, attachment in enumerate(file_attachments, start=1):
            size = f' ({attachment.file_size // 1024} KB)' if attachment.file_size else ''
            body.append(_docx_paragraph(f'{index}. {attachment.original_filename}{size}'))

    body.append(_docx_paragraph(''))
    body.append(_docx_paragraph(f'Generated from IT HelpDesk Audit & Policy Management on {datetime.utcnow().strftime("%d %b %Y %H:%M UTC")}', size='18'))

    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    {''.join(body)}
    <w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="900" w:right="900" w:bottom="900" w:left="900"/></w:sectPr>
  </w:body>
</w:document>'''

    rels = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>']
    content_types = [
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>',
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>',
    ]
    image_content_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'bmp': 'image/bmp',
    }
    for index, (_attachment, _path, ext) in enumerate(image_files, start=1):
        rels.append(f'<Relationship Id="rId{index + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image{index}.{ext}"/>')
        if f'<Default Extension="{ext}" ContentType="{image_content_types[ext]}"/>' not in content_types:
            content_types.append(f'<Default Extension="{ext}" ContentType="{image_content_types[ext]}"/>')

    output = BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as package:
        package.writestr('[Content_Types].xml', f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">{''.join(content_types)}</Types>''')
        package.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>''')
        package.writestr('word/_rels/document.xml.rels', f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{''.join(rels)}</Relationships>''')
        package.writestr('word/styles.xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/></w:rPr></w:style></w:styles>''')
        package.writestr('word/document.xml', document_xml)
        for index, (_attachment, path, ext) in enumerate(image_files, start=1):
            with open(path, 'rb') as image_handle:
                package.writestr(f'word/media/image{index}.{ext}', image_handle.read())
    output.seek(0)
    return output.getvalue()


def staff_options():
    return User.query.filter_by(_is_active=True).order_by(User.name.asc()).all()


def pending_acknowledgement_policies():
    policies = AuditPolicy.query.filter_by(
        status='active',
        requires_acknowledgement=True,
    ).order_by(AuditPolicy.review_date.asc(), AuditPolicy.title.asc()).all()
    acknowledgements = {
        acknowledgement.policy_id: acknowledgement
        for acknowledgement in AuditPolicyAcknowledgement.query
        .filter_by(user_id=current_user.id)
        .all()
    }
    return [policy for policy in policies if not policy.acknowledgement_is_current(acknowledgements.get(policy.id))]


def policy_query_for_user():
    query = AuditPolicy.query
    if not can_manage_audit():
        query = query.filter_by(status='active')
    return query


@audit.route('/')
@login_required
def index():
    today = date.today()
    policy_status = request.args.get('policy_status', '').strip()
    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip()

    policies_query = policy_query_for_user()
    if policy_status:
        policies_query = policies_query.filter_by(status=policy_status)
    if category:
        policies_query = policies_query.filter_by(category=category)
    if search:
        like_search = f'%{search}%'
        policies_query = policies_query.filter(db.or_(
            AuditPolicy.code.ilike(like_search),
            AuditPolicy.title.ilike(like_search),
            AuditPolicy.description.ilike(like_search),
            AuditPolicy.controls.ilike(like_search),
        ))

    policies = policies_query.order_by(
        AuditPolicy.status.asc(),
        AuditPolicy.review_date.asc(),
        AuditPolicy.title.asc(),
    ).all()

    audits_query = AuditPlan.query
    findings_query = AuditFinding.query
    actions_query = AuditCorrectiveAction.query
    if not can_manage_audit():
        audits_query = audits_query.filter_by(auditor_id=current_user.id)
        findings_query = findings_query.filter_by(owner_id=current_user.id)
        actions_query = actions_query.filter_by(owner_id=current_user.id)

    recent_audits = audits_query.order_by(AuditPlan.scheduled_date.desc(), AuditPlan.created_at.desc()).limit(6).all()
    open_findings = findings_query.filter(AuditFinding.status.notin_(['closed', 'accepted'])).order_by(
        AuditFinding.due_date.asc(),
        AuditFinding.severity.desc(),
    ).limit(8).all()
    due_actions = actions_query.filter(AuditCorrectiveAction.status != 'completed').order_by(
        AuditCorrectiveAction.due_date.asc(),
        AuditCorrectiveAction.created_at.desc(),
    ).limit(8).all()

    return render_template(
        'audit/index.html',
        policies=policies,
        recent_audits=recent_audits,
        open_findings=open_findings,
        due_actions=due_actions,
        pending_acknowledgements=pending_acknowledgement_policies(),
        total_policies=policy_query_for_user().count(),
        active_policies=policy_query_for_user().filter_by(status='active').count(),
        review_due=policy_query_for_user().filter(AuditPolicy.review_date.isnot(None), AuditPolicy.review_date <= today).count(),
        open_finding_count=findings_query.filter(AuditFinding.status.notin_(['closed', 'accepted'])).count(),
        overdue_action_count=actions_query.filter(
            AuditCorrectiveAction.status != 'completed',
            AuditCorrectiveAction.due_date.isnot(None),
            AuditCorrectiveAction.due_date < today,
        ).count(),
        categories=POLICY_CATEGORIES,
        policy_statuses=POLICY_STATUSES,
        policy_status=policy_status,
        category=category,
        search=search,
        can_manage=can_manage_audit(),
        today=today,
    )


@audit.route('/policies/create', methods=['GET', 'POST'])
@login_required
@audit_manager_required
def create_policy():
    policy = AuditPolicy(created_by=current_user.id)
    if request.method == 'POST':
        populate_policy(policy)
        if not policy.code or not policy.title:
            flash('Policy code and title are required.', 'danger')
        elif AuditPolicy.query.filter_by(code=policy.code).first():
            flash('Policy code already exists.', 'danger')
        else:
            db.session.add(policy)
            db.session.commit()
            saved = save_policy_attachments(policy)
            if saved:
                db.session.commit()
            flash('Audit policy created.', 'success')
            return redirect(url_for('audit.policy_detail', policy_id=policy.id))
    form_steps, additional_controls = policy_form_steps(policy)
    return render_template(
        'audit/policy_form.html',
        policy=policy,
        categories=POLICY_CATEGORIES,
        users=staff_options(),
        form_steps=form_steps,
        additional_controls=additional_controls,
        mode='create',
    )


@audit.route('/policies/<int:policy_id>')
@login_required
def policy_detail(policy_id):
    policy = AuditPolicy.query.get_or_404(policy_id)
    if policy.status != 'active' and not can_manage_audit():
        flash('This policy is not available.', 'warning')
        return redirect(url_for('audit.index'))
    acknowledgement = AuditPolicyAcknowledgement.query.filter_by(policy_id=policy.id, user_id=current_user.id).first()
    acknowledgement_current = policy.acknowledgement_is_current(acknowledgement)
    related_audits = AuditPlan.query.filter_by(policy_id=policy.id).order_by(AuditPlan.scheduled_date.desc()).limit(6).all()
    findings = AuditFinding.query.filter_by(policy_id=policy.id).order_by(AuditFinding.created_at.desc()).limit(8).all()
    step_evidence, remaining_images, extra_control_lines = policy_step_evidence(policy)
    current_acknowledgement_count = sum(
        1 for item in policy.acknowledgements
        if policy.acknowledgement_is_current(item)
    )
    return render_template(
        'audit/policy_detail.html',
        policy=policy,
        acknowledgement=acknowledgement,
        acknowledgement_current=acknowledgement_current,
        acknowledgement_count=AuditPolicyAcknowledgement.query.filter_by(policy_id=policy.id).count(),
        current_acknowledgement_count=current_acknowledgement_count,
        related_audits=related_audits,
        findings=findings,
        step_evidence=step_evidence,
        remaining_images=remaining_images,
        extra_control_lines=extra_control_lines,
        file_attachments=[attachment for attachment in policy.attachments if not attachment.is_image],
        can_manage=can_manage_audit(),
    )


@audit.route('/policies/<int:policy_id>/download')
@login_required
def download_policy(policy_id):
    policy = AuditPolicy.query.get_or_404(policy_id)
    if policy.status != 'active' and not can_manage_audit():
        flash('This policy is not available.', 'warning')
        return redirect(url_for('audit.index'))
    image_attachments = [
        (attachment, policy_attachment_data_uri(attachment))
        for attachment in policy.attachments
        if attachment.is_image
    ]
    step_evidence, remaining_images, extra_control_lines = policy_step_evidence(policy, include_data_uri=True)
    html = render_template(
        'audit/policy_download.html',
        policy=policy,
        generated_at=datetime.utcnow(),
        image_attachments=[item for item in image_attachments if item[1]],
        step_evidence=step_evidence,
        remaining_images=[(attachment, policy_attachment_data_uri(attachment)) for attachment in remaining_images],
        extra_control_lines=extra_control_lines,
        file_attachments=[attachment for attachment in policy.attachments if not attachment.is_image],
        word_export=False,
    )
    filename = f'{policy.code.lower()}-v{policy.version.replace(".", "_")}.html'
    response = make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@audit.route('/policies/<int:policy_id>/download-word')
@login_required
def download_policy_word(policy_id):
    policy = AuditPolicy.query.get_or_404(policy_id)
    if policy.status != 'active' and not can_manage_audit():
        flash('This policy is not available.', 'warning')
        return redirect(url_for('audit.index'))
    filename = f'{policy.code.lower()}-v{policy.version.replace(".", "_")}.docx'
    response = make_response(build_policy_docx(policy))
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@audit.route('/policies/<int:policy_id>/edit', methods=['GET', 'POST'])
@login_required
@audit_manager_required
def edit_policy(policy_id):
    policy = AuditPolicy.query.get_or_404(policy_id)
    original_code = policy.code
    if request.method == 'POST':
        populate_policy(policy)
        duplicate = AuditPolicy.query.filter(AuditPolicy.code == policy.code, AuditPolicy.id != policy.id).first()
        if not policy.code or not policy.title:
            flash('Policy code and title are required.', 'danger')
        elif duplicate:
            policy.code = original_code
            flash('Policy code already exists.', 'danger')
        else:
            db.session.commit()
            saved = save_policy_attachments(policy)
            if saved:
                db.session.commit()
            flash('Audit policy updated.', 'success')
            return redirect(url_for('audit.policy_detail', policy_id=policy.id))
    form_steps, additional_controls = policy_form_steps(policy)
    return render_template(
        'audit/policy_form.html',
        policy=policy,
        categories=POLICY_CATEGORIES,
        users=staff_options(),
        form_steps=form_steps,
        additional_controls=additional_controls,
        mode='edit',
    )


def populate_policy(policy):
    policy.code = request.form.get('code', '').strip().upper()
    policy.title = request.form.get('title', '').strip()
    policy.category = request.form.get('category', '').strip() or None
    policy.risk_level = request.form.get('risk_level', 'medium')
    policy.status = request.form.get('status', 'active')
    policy.version = request.form.get('version', '').strip() or '1.0'
    policy.owner_id = request.form.get('owner_id', type=int) or None
    policy.description = request.form.get('description', '').strip() or None
    policy.scope = request.form.get('scope', '').strip() or None
    evidence_steps = [item.strip() for item in request.form.getlist('evidence_steps') if item.strip()]
    if evidence_steps:
        normalized_steps = []
        for index, step in enumerate(evidence_steps, start=1):
            if re.match(r'^\d+[\.\)]\s+', step):
                normalized_steps.append(step)
            else:
                normalized_steps.append(f'{index}. {step}')
        additional_controls = request.form.get('additional_controls', '').strip()
        policy.controls = '\n'.join(normalized_steps + ([additional_controls] if additional_controls else []))
    else:
        policy.controls = request.form.get('controls', '').strip() or None
    policy.effective_date = parse_date(request.form.get('effective_date'))
    policy.review_date = parse_date(request.form.get('review_date'))
    policy.requires_acknowledgement = request.form.get('requires_acknowledgement') == 'on'


@audit.route('/policies/<int:policy_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_policy(policy_id):
    policy = AuditPolicy.query.get_or_404(policy_id)
    if policy.status != 'active' or not policy.requires_acknowledgement:
        flash('This policy does not require acknowledgement.', 'warning')
        return redirect(url_for('audit.policy_detail', policy_id=policy.id))
    acknowledgement = AuditPolicyAcknowledgement.query.filter_by(policy_id=policy.id, user_id=current_user.id).first()
    if acknowledgement:
        acknowledgement.policy_version = policy.version
        acknowledgement.acknowledged_at = datetime.utcnow()
    else:
        db.session.add(AuditPolicyAcknowledgement(
            policy_id=policy.id,
            user_id=current_user.id,
            policy_version=policy.version,
        ))
    db.session.commit()
    flash('Policy acknowledged.', 'success')
    return redirect(url_for('audit.policy_detail', policy_id=policy.id))


@audit.route('/attachments/<int:attachment_id>/download')
@login_required
def download_attachment(attachment_id):
    attachment = AuditPolicyAttachment.query.get_or_404(attachment_id)
    if attachment.policy.status != 'active' and not can_manage_audit():
        abort(403)
    inline_preview = request.args.get('inline') == '1' and attachment.is_image
    return send_from_directory(
        policy_upload_folder(attachment.policy_id),
        attachment.stored_filename,
        as_attachment=not inline_preview,
        download_name=attachment.original_filename,
    )


@audit.route('/attachments/<int:attachment_id>/delete', methods=['POST'])
@login_required
@audit_manager_required
def delete_attachment(attachment_id):
    attachment = AuditPolicyAttachment.query.get_or_404(attachment_id)
    policy_id = attachment.policy_id
    policy = attachment.policy
    path = os.path.join(policy_upload_folder(policy_id), attachment.stored_filename)
    if os.path.exists(path):
        os.remove(path)
    db.session.delete(attachment)
    policy.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Policy attachment deleted.', 'success')
    return redirect(url_for('audit.edit_policy', policy_id=policy_id))


@audit.route('/audits/create', methods=['GET', 'POST'])
@login_required
@audit_manager_required
def create_audit():
    audit_plan = AuditPlan(created_by=current_user.id)
    if request.method == 'POST':
        populate_audit(audit_plan)
        if not audit_plan.title:
            flash('Audit title is required.', 'danger')
        else:
            db.session.add(audit_plan)
            db.session.commit()
            flash('Audit plan created.', 'success')
            return redirect(url_for('audit.audit_detail', audit_id=audit_plan.id))
    return render_template('audit/audit_form.html', audit_plan=audit_plan, policies=AuditPolicy.query.order_by(AuditPolicy.title).all(), users=staff_options(), departments=Department.query.order_by(Department.name).all(), mode='create')


@audit.route('/audits/<int:audit_id>')
@login_required
def audit_detail(audit_id):
    audit_plan = AuditPlan.query.get_or_404(audit_id)
    if not can_manage_audit() and audit_plan.auditor_id != current_user.id:
        flash('Audit access denied.', 'danger')
        return redirect(url_for('audit.index'))
    users = staff_options()
    return render_template('audit/audit_detail.html', audit_plan=audit_plan, users=users, policies=AuditPolicy.query.order_by(AuditPolicy.title).all(), can_manage=can_manage_audit())


@audit.route('/audits/<int:audit_id>/edit', methods=['GET', 'POST'])
@login_required
@audit_manager_required
def edit_audit(audit_id):
    audit_plan = AuditPlan.query.get_or_404(audit_id)
    if request.method == 'POST':
        populate_audit(audit_plan)
        if not audit_plan.title:
            flash('Audit title is required.', 'danger')
        else:
            db.session.commit()
            flash('Audit plan updated.', 'success')
            return redirect(url_for('audit.audit_detail', audit_id=audit_plan.id))
    return render_template('audit/audit_form.html', audit_plan=audit_plan, policies=AuditPolicy.query.order_by(AuditPolicy.title).all(), users=staff_options(), departments=Department.query.order_by(Department.name).all(), mode='edit')


def populate_audit(audit_plan):
    audit_plan.title = request.form.get('title', '').strip()
    audit_plan.audit_type = request.form.get('audit_type', 'internal')
    audit_plan.status = request.form.get('status', 'planned')
    audit_plan.policy_id = request.form.get('policy_id', type=int) or None
    audit_plan.auditor_id = request.form.get('auditor_id', type=int) or None
    audit_plan.department_id = request.form.get('department_id', type=int) or None
    audit_plan.scope = request.form.get('scope', '').strip() or None
    audit_plan.scheduled_date = parse_date(request.form.get('scheduled_date'))
    audit_plan.completed_date = parse_date(request.form.get('completed_date'))
    audit_plan.score = request.form.get('score', type=int)
    audit_plan.notes = request.form.get('notes', '').strip() or None


@audit.route('/audits/<int:audit_id>/findings/create', methods=['POST'])
@login_required
@audit_manager_required
def create_finding(audit_id):
    audit_plan = AuditPlan.query.get_or_404(audit_id)
    finding = AuditFinding(audit_id=audit_plan.id)
    populate_finding(finding)
    if not finding.title:
        flash('Finding title is required.', 'danger')
    else:
        db.session.add(finding)
        db.session.commit()
        flash('Finding added.', 'success')
    return redirect(url_for('audit.audit_detail', audit_id=audit_plan.id))


@audit.route('/findings/<int:finding_id>/update', methods=['POST'])
@login_required
@audit_manager_required
def update_finding(finding_id):
    finding = AuditFinding.query.get_or_404(finding_id)
    populate_finding(finding)
    if finding.status in ('closed', 'accepted') and not finding.closed_at:
        finding.closed_at = datetime.utcnow()
    if finding.status not in ('closed', 'accepted'):
        finding.closed_at = None
    db.session.commit()
    flash('Finding updated.', 'success')
    return redirect(url_for('audit.audit_detail', audit_id=finding.audit_id))


def populate_finding(finding):
    finding.title = request.form.get('title', '').strip()
    finding.policy_id = request.form.get('policy_id', type=int) or None
    finding.severity = request.form.get('severity', 'medium')
    finding.status = request.form.get('status', 'open')
    finding.owner_id = request.form.get('owner_id', type=int) or None
    finding.description = request.form.get('description', '').strip() or None
    finding.recommendation = request.form.get('recommendation', '').strip() or None
    finding.due_date = parse_date(request.form.get('due_date'))


@audit.route('/findings/<int:finding_id>/actions/create', methods=['POST'])
@login_required
@audit_manager_required
def create_action(finding_id):
    finding = AuditFinding.query.get_or_404(finding_id)
    action = AuditCorrectiveAction(finding_id=finding.id)
    populate_action(action)
    if not action.title:
        flash('Action title is required.', 'danger')
    else:
        db.session.add(action)
        db.session.commit()
        flash('Corrective action added.', 'success')
    return redirect(url_for('audit.audit_detail', audit_id=finding.audit_id))


@audit.route('/actions/<int:action_id>/update', methods=['POST'])
@login_required
def update_action(action_id):
    action = AuditCorrectiveAction.query.get_or_404(action_id)
    if not can_manage_audit() and action.owner_id != current_user.id:
        flash('Action access denied.', 'danger')
        return redirect(url_for('audit.index'))
    populate_action(action)
    if action.status == 'completed' and not action.completed_at:
        action.completed_at = datetime.utcnow()
    if action.status != 'completed':
        action.completed_at = None
    db.session.commit()
    flash('Corrective action updated.', 'success')
    return redirect(url_for('audit.audit_detail', audit_id=action.finding.audit_id))


def populate_action(action):
    action.title = request.form.get('title', '').strip()
    action.owner_id = request.form.get('owner_id', type=int) or None
    action.status = request.form.get('status', 'open')
    action.due_date = parse_date(request.form.get('due_date'))
    action.notes = request.form.get('notes', '').strip() or None
