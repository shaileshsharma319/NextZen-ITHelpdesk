from datetime import date, timedelta

from app import create_app, db
from app.models.audit import AuditPolicy
from app.models.user import User


STARTER_POLICIES = [
    {
        'code': 'IT-POL-001',
        'title': 'Password and Account Security Policy',
        'category': 'IT Security',
        'risk_level': 'high',
        'description': 'Defines password, MFA, account lockout, privileged access, and account review requirements for all company systems.',
        'scope': 'Applies to all employees, contractors, administrators, service accounts, cloud accounts, email accounts, VPN, and business applications.',
        'controls': '''1. Passwords must be unique and must not be shared.
2. MFA is required for email, VPN, cloud, admin, and remote access.
3. Privileged accounts must be separate from daily-use accounts.
4. User access must be reviewed at least quarterly.
5. Inactive accounts must be disabled promptly after exit or role change.
6. Passwords must not be stored in plain text files, chats, or tickets.''',
    },
    {
        'code': 'IT-POL-002',
        'title': 'Acceptable Use of IT Assets Policy',
        'category': 'Asset Management',
        'risk_level': 'medium',
        'description': 'Sets rules for responsible use of company laptops, desktops, software, internet, email, and removable media.',
        'scope': 'Applies to company-owned and company-managed devices, software, networks, and accounts used by employees and third parties.',
        'controls': '''1. Company devices must be used for business-approved activity.
2. Unauthorized software installation is not allowed.
3. Users must not disable antivirus, firewall, encryption, or endpoint controls.
4. Lost or stolen assets must be reported immediately.
5. Assets must be returned during exit or role transfer.
6. Sensitive data must not be copied to unmanaged USB or personal cloud storage.''',
    },
    {
        'code': 'IT-POL-003',
        'title': 'Email and Phishing Protection Policy',
        'category': 'IT Security',
        'risk_level': 'high',
        'description': 'Defines rules for email security, phishing reporting, attachments, links, and business communication safety.',
        'scope': 'Applies to all email users, shared mailboxes, distribution groups, and mail-enabled business systems.',
        'controls': '''1. Suspicious emails must be reported to IT without forwarding to other users.
2. Users must verify payment, bank, password, and urgent change requests through an approved second channel.
3. Executable attachments and unknown links must not be opened.
4. Auto-forwarding to personal email is prohibited unless approved.
5. Email signatures must follow approved company format.
6. Sensitive data must be encrypted or shared through approved platforms.''',
    },
    {
        'code': 'IT-POL-004',
        'title': 'Data Protection and Privacy Policy',
        'category': 'Data Privacy',
        'risk_level': 'critical',
        'description': 'Defines how company, customer, employee, and confidential data must be classified, handled, stored, shared, and disposed.',
        'scope': 'Applies to all structured and unstructured data handled by the company, including documents, databases, backups, emails, tickets, HR records, and reports.',
        'controls': '''1. Confidential data must be shared only with authorized users.
2. Access must follow least privilege and business need.
3. Personal and customer data must not be stored on unmanaged devices.
4. Data exports must be approved for sensitive systems.
5. Backups must be protected from unauthorized access.
6. Data disposal must follow approved retention and destruction rules.''',
    },
    {
        'code': 'IT-POL-005',
        'title': 'Incident Reporting and Response Policy',
        'category': 'Business Continuity',
        'risk_level': 'critical',
        'description': 'Defines how security incidents, service disruptions, data leakage, malware, unauthorized access, and asset loss are reported and managed.',
        'scope': 'Applies to all employees, support teams, administrators, vendors, applications, infrastructure, endpoints, and business services.',
        'controls': '''1. Incidents must be logged as tickets immediately after discovery.
2. Critical incidents must be escalated to IT management without delay.
3. Evidence must be preserved for security and audit review.
4. Affected accounts or devices may be isolated during investigation.
5. Root cause and corrective actions must be documented.
6. Post-incident review must be completed for critical incidents.''',
    },
    {
        'code': 'HR-POL-001',
        'title': 'Employee Attendance and Leave Policy',
        'category': 'HR Policy',
        'risk_level': 'medium',
        'description': 'Defines attendance expectations, leave application rules, approval flow, holiday handling, and absence reporting.',
        'scope': 'Applies to all employees, reporting managers, HR staff, and department heads.',
        'controls': '''1. Attendance must be recorded through the approved HRMS process.
2. Leave should be requested before planned absence.
3. Emergency leave must be informed to the reporting manager as early as possible.
4. Managers must approve or reject leave requests in a timely manner.
5. Unauthorized absence may be escalated to HR.
6. Holiday calendars must be maintained by HR/admin.''',
    },
]


def seed():
    app = create_app()
    with app.app_context():
        owner = User.query.filter_by(role='master_admin').first() or User.query.first()
        today = date.today()
        review_date = today + timedelta(days=180)
        created = 0
        updated = 0

        for item in STARTER_POLICIES:
            policy = AuditPolicy.query.filter_by(code=item['code']).first()
            if policy:
                updated += 1
            else:
                policy = AuditPolicy(code=item['code'], created_by=owner.id if owner else None)
                db.session.add(policy)
                created += 1

            policy.title = item['title']
            policy.category = item['category']
            policy.risk_level = item['risk_level']
            policy.status = 'active'
            policy.version = '1.0'
            policy.owner_id = owner.id if owner else None
            policy.description = item['description']
            policy.scope = item['scope']
            policy.controls = item['controls']
            policy.effective_date = today
            policy.review_date = review_date
            policy.requires_acknowledgement = True

        db.session.commit()
        print(f'Audit policies ready. Created: {created}, Updated: {updated}')


if __name__ == '__main__':
    seed()
