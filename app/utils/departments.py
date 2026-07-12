STANDARD_DEPARTMENTS = [
    {
        'name': 'Human Resources',
        'description': 'People administration and user account coordination',
        'location': 'Floor 2',
        'access_summary': 'Admin: user account management. Basic: create/view own tickets and basic helpdesk.',
        'aliases': ['human resources', 'hr', 'hr department', 'hrms'],
    },
    {
        'name': 'IT Department',
        'description': 'Helpdesk, inventory, software licenses, compliance, systems, and infrastructure',
        'location': 'Floor 1',
        'access_summary': 'Admin: full ticket queue, assignment, email fetch, inventory, compliance, and licenses. Basic: create/view own tickets.',
        'aliases': ['it department', 'information technology', 'it', 'technical'],
    },
    {
        'name': 'IT Support',
        'description': 'Helpdesk support group for ticket assignment, escalation, and service desk work',
        'location': 'Service Desk',
        'access_summary': 'Admin: full helpdesk agent access. Basic: create/view own tickets.',
        'aliases': ['it support', 'support', 'service desk'],
    },
    {
        'name': 'Account Department',
        'description': 'Accounting, invoices, billing, vouchers, ledgers, and payment records',
        'location': 'Floor 3',
        'access_summary': 'Admin: department operations. Basic: create/view own tickets.',
        'aliases': ['account department', 'accounts', 'account', 'accounting'],
    },
    {
        'name': 'Finance',
        'description': 'Budgeting, financial planning, salary approvals, taxes, and statutory finance',
        'location': 'Floor 3',
        'access_summary': 'Admin: finance records and reports. Basic: create/view own tickets.',
        'aliases': ['finance', 'finence', 'finance department', 'finence department'],
    },
    {
        'name': 'Sales Department',
        'description': 'Sales, customer relationships, proposals, follow-ups, and business development',
        'location': 'Sales Office',
        'access_summary': 'Admin: sales operations. Basic: create/view own tickets.',
        'aliases': ['sales', 'sales department', 'business development'],
    },
    {
        'name': 'Office Admin',
        'description': 'Office administration, facilities, stationery, vendors, and general operations',
        'location': 'Admin Office',
        'access_summary': 'Admin: office operations. Basic: create/view own tickets.',
        'aliases': ['office admin', 'administration', 'admin office', 'admin'],
    },
    {
        'name': 'Operations',
        'description': 'Operations, logistics, coordination, delivery support, and daily business execution',
        'location': 'Floor 4',
        'access_summary': 'Admin: operations work. Basic: create/view own tickets.',
        'aliases': ['operations', 'operation', 'logistics'],
    },
]


def standard_department_map():
    return {item['name']: item for item in STANDARD_DEPARTMENTS}


def standard_department_names():
    return [item['name'] for item in STANDARD_DEPARTMENTS]
