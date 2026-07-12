from app import db
from app.models.assignment_rule import AssignmentRule
from app.models.reply import TicketActivity
from datetime import datetime, timedelta

SLA_HOURS = {'low': 72, 'medium': 24, 'high': 8, 'critical': 4}


def _same(value, expected):
    return not expected or (value or '').lower() == expected.lower()


def _keywords_match(ticket, keywords):
    if not keywords:
        return True
    haystack = f'{ticket.title or ""} {ticket.description or ""}'.lower()
    terms = [term.strip().lower() for term in keywords.replace('\n', ',').split(',') if term.strip()]
    return any(term in haystack for term in terms) if terms else True


def _rule_matches(ticket, rule):
    return (
        _same(ticket.source, rule.match_source)
        and _same(ticket.ticket_type, rule.match_ticket_type)
        and _same(ticket.priority, rule.match_priority)
        and _same(ticket.category, rule.match_category)
        and _same(ticket.support_group, rule.match_support_group)
        and _keywords_match(ticket, rule.keywords)
    )


def _find_department_name(candidates):
    from app.models.department import Department
    departments = Department.query.order_by(Department.name).all()
    for candidate in candidates:
        candidate_key = candidate.lower()
        for department in departments:
            name = (department.name or '').strip()
            lower_name = name.lower()
            if lower_name == candidate_key or candidate_key in lower_name:
                return name
    return None


def _fallback_group_for_category(category):
    category_key = (category or '').strip().lower()
    if not category_key:
        return None
    category_groups = {
        'hardware': ['IT Support', 'IT Department'],
        'software': ['IT Support', 'IT Department'],
        'software installation': ['IT Support', 'IT Department'],
        'network': ['IT Support', 'IT Department'],
        'internet & isp': ['IT Support', 'IT Department'],
        'email': ['IT Support', 'IT Department'],
        'access & permissions': ['IT Support', 'IT Department'],
        'data & file share': ['IT Support', 'IT Department'],
        'endpoint management': ['IT Support', 'IT Department'],
        'security': ['IT Support', 'IT Department'],
        'compliance / audit': ['IT Department', 'Office Admin', 'IT Support'],
        'server': ['IT Department', 'IT Support'],
        'database': ['IT Department', 'IT Support'],
        'backup & recovery': ['IT Department', 'IT Support'],
        'cloud / saas': ['IT Department', 'IT Support'],
        'website / domain': ['IT Department', 'IT Support'],
        'telephony': ['IT Support', 'Office Admin', 'IT Department'],
        'meeting room / av': ['Office Admin', 'IT Support', 'IT Department'],
        'remote work': ['IT Support', 'IT Department'],
        'vendor / procurement': ['Office Admin', 'IT Department', 'IT Support'],
        'facilities it': ['Office Admin', 'IT Support', 'IT Department'],
        'asset request': ['IT Department', 'Office Admin', 'IT Support'],
        'onboarding / offboarding': ['IT Department', 'Human Resources', 'Office Admin'],
        'training / how-to': ['IT Support', 'IT Department'],
    }
    return _find_department_name(category_groups.get(category_key, ['IT Support', 'IT Department']))


def _first_owner_for_group(group_name):
    if not group_name:
        return None
    from app.models.user import User
    users = User.query.filter(User._is_active.is_(True)).order_by(User.role, User.name).all()
    for user in users:
        department_name = user.department.name if user.department else ''
        if department_name == group_name and user.can_manage_helpdesk:
            return user
    for user in users:
        if user.can_manage_helpdesk:
            return user
    return None


def apply_auto_assignment(ticket, actor_id=None):
    rules = AssignmentRule.query.filter_by(is_active=True).order_by(
        AssignmentRule.priority_order.asc(),
        AssignmentRule.id.asc(),
    ).all()

    for rule in rules:
        if not _rule_matches(ticket, rule):
            continue

        changes = []
        if rule.assign_to and not ticket.assigned_to:
            ticket.assigned_to = rule.assign_to
            changes.append(f'owner set to {rule.assignee.name if rule.assignee else "configured user"}')
        if rule.set_support_group and not ticket.support_group:
            ticket.support_group = rule.set_support_group
            changes.append(f'support group set to {rule.set_support_group}')
        if rule.set_priority and ticket.priority != rule.set_priority:
            old_priority = ticket.priority
            ticket.priority = rule.set_priority
            if rule.set_priority in SLA_HOURS:
                ticket.sla_due = datetime.utcnow() + timedelta(hours=SLA_HOURS[rule.set_priority])
            changes.append(f'priority changed from {old_priority.title()} to {rule.set_priority.title()}')
        if rule.set_status and ticket.status != rule.set_status:
            old_status = ticket.status
            ticket.status = rule.set_status
            changes.append(f'status changed from {old_status.replace("_", " ").title()} to {rule.set_status.replace("_", " ").title()}')

        if changes:
            db.session.add(TicketActivity(
                ticket_id=ticket.id,
                activity_type='assignment_rule',
                description=f'Auto assignment rule "{rule.name}" applied: {", ".join(changes)}.',
                user_id=actor_id,
            ))
        return rule

    fallback_changes = []
    if ticket.category:
        fallback_group = _fallback_group_for_category(ticket.category)
        if fallback_group and not ticket.support_group:
            ticket.support_group = fallback_group
            fallback_changes.append(f'support group set to {fallback_group}')
        if not ticket.assigned_to:
            owner = _first_owner_for_group(ticket.support_group or fallback_group)
            if owner:
                ticket.assigned_to = owner.id
                fallback_changes.append(f'owner set to {owner.name}')

    if fallback_changes:
        db.session.add(TicketActivity(
            ticket_id=ticket.id,
            activity_type='assignment_rule',
            description=f'Category fallback routing applied: {", ".join(fallback_changes)}.',
            user_id=actor_id,
        ))

    return None
