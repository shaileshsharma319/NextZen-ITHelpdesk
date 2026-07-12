import os
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from uuid import uuid4

from app import create_app, db
from app.models.audit import AuditPolicy, AuditPolicyAttachment
from app.models.user import User


SOURCE_DOCX = r'C:\Users\God\Downloads\Permission Access.docx'
POLICY_CODE = 'IT-PERM-001'


def extract_headings(docx_path):
    namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with zipfile.ZipFile(docx_path) as package:
        root = ET.fromstring(package.read('word/document.xml'))
    headings = []
    for paragraph in root.findall('.//w:p', namespace):
        text = ''.join(node.text or '' for node in paragraph.findall('.//w:t', namespace)).strip()
        if text:
            headings.append(text)
    return headings


def upload_folder(policy_id):
    folder = os.path.join(os.getcwd(), 'app', 'static', 'uploads', 'audit_policies', str(policy_id))
    os.makedirs(folder, exist_ok=True)
    return folder


def seed():
    app = create_app()
    with app.app_context():
        owner = User.query.filter_by(role='master_admin').first() or User.query.first()
        headings = extract_headings(SOURCE_DOCX)
        today = date.today()

        policy = AuditPolicy.query.filter_by(code=POLICY_CODE).first()
        if not policy:
            policy = AuditPolicy(code=POLICY_CODE, created_by=owner.id if owner else None)
            db.session.add(policy)

        policy.title = 'Permission Access Policy'
        policy.category = 'Access Control'
        policy.risk_level = 'high'
        policy.status = 'active'
        policy.version = '1.0'
        policy.owner_id = owner.id if owner else None
        policy.effective_date = today
        policy.review_date = today + timedelta(days=180)
        policy.requires_acknowledgement = True
        policy.description = (
            'Defines approval, documentation, review, and evidence requirements for granting '
            'repository, source control, domain control panel, and user access permissions.'
        )
        policy.scope = (
            'Applies to Git, SVN, domain/user control panels, application repositories, '
            'administrator portals, project access, and any user permission changes managed by IT.'
        )
        policy.controls = '\n'.join(headings) + '\n\n' + '\n'.join([
            'Access must be granted only after approval from the reporting manager, project owner, or authorized administrator.',
            'Permission level must follow least privilege and must match the user role.',
            'Admin, developer, guest, read/write, and denied permissions must be documented.',
            'Screenshots or system evidence must be attached for audit proof.',
            'Access changes must be reviewed periodically and removed when no longer required.',
            'All permission changes must be traceable through ticket, audit, or approved request record.',
        ])

        db.session.commit()

        # Replace previous imported evidence for this seeded policy to keep reruns clean.
        for attachment in list(policy.attachments):
            if attachment.original_filename.startswith('permission-access-'):
                path = os.path.join(upload_folder(policy.id), attachment.stored_filename)
                if os.path.exists(path):
                    os.remove(path)
                db.session.delete(attachment)
        db.session.commit()

        created_files = 0
        with zipfile.ZipFile(SOURCE_DOCX) as package:
            media_names = sorted(name for name in package.namelist() if name.startswith('word/media/'))
            for index, media_name in enumerate(media_names, start=1):
                ext = media_name.rsplit('.', 1)[-1].lower()
                original = f'permission-access-screenshot-{index}.{ext}'
                stored = f'{uuid4().hex}.{ext}'
                target = os.path.join(upload_folder(policy.id), stored)
                with open(target, 'wb') as output:
                    output.write(package.read(media_name))
                content_type = 'image/png' if ext == 'png' else f'image/{ext}'
                db.session.add(AuditPolicyAttachment(
                    policy_id=policy.id,
                    original_filename=original,
                    stored_filename=stored,
                    content_type=content_type,
                    file_size=os.path.getsize(target),
                    uploaded_by=owner.id if owner else None,
                ))
                created_files += 1

        db.session.commit()
        print(f'Policy ready: {policy.id} {policy.code} with {created_files} screenshot(s)')


if __name__ == '__main__':
    seed()
