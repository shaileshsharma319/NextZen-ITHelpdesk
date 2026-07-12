from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import date, datetime

from app import db
from app.models.asset import Asset
from app.models.audit import AuditCorrectiveAction, AuditFinding, AuditPolicy, AuditPolicyAcknowledgement
from app.models.knowledge import KnowledgeAcknowledgement, KnowledgeArticle
from app.models.ticket import Ticket
from app.models.user import User

dashboard = Blueprint('dashboard', __name__)


@dashboard.route('/')
@login_required
def index():
    now = datetime.utcnow()
    today = date.today()

    if current_user.can_view_all_tickets:
        ticket_query = Ticket.query
    else:
        ticket_query = Ticket.query.filter(db.or_(
            Ticket.user_id == current_user.id,
            Ticket.assigned_to == current_user.id,
        ))

    total_tickets = ticket_query.count()
    open_tickets = ticket_query.filter_by(status='open').count()
    in_progress = ticket_query.filter_by(status='in_progress').count()
    pending_tickets = ticket_query.filter_by(status='pending').count()
    resolved = ticket_query.filter_by(status='resolved').count()
    closed_tickets = ticket_query.filter_by(status='closed').count()
    overdue = ticket_query.filter(
        Ticket.sla_due.isnot(None),
        Ticket.sla_due < now,
        Ticket.status.notin_(['resolved', 'closed']),
    ).count()
    critical_tickets = ticket_query.filter_by(priority='critical').count()
    unassigned_tickets = ticket_query.filter(Ticket.assigned_to.is_(None)).count() if current_user.can_view_all_tickets else 0
    recent_tickets = ticket_query.order_by(Ticket.created_at.desc()).limit(8).all()

    employee_query = User.query if current_user.can_manage_users else User.query.filter_by(id=current_user.id)
    total_users = employee_query.count() if current_user.can_manage_users else None

    if current_user.can_manage_inventory:
        total_assets = Asset.query.count()
        available_assets = Asset.query.filter_by(status='available').count()
    else:
        total_assets = None
        available_assets = None

    kb_query = KnowledgeArticle.query.filter_by(is_published=True)
    if not current_user.can_manage_helpdesk:
        kb_query = kb_query.filter_by(visibility='all')
    knowledge_count = kb_query.count()
    featured_articles = kb_query.filter_by(is_featured=True).order_by(KnowledgeArticle.updated_at.desc()).limit(4).all()
    policies_requiring_ack = KnowledgeArticle.query.filter_by(
        is_published=True,
        visibility='all',
        requires_acknowledgement=True,
    ).all()
    acknowledged_article_ids = {
        row[0] for row in db.session.query(KnowledgeAcknowledgement.article_id)
        .filter_by(user_id=current_user.id)
        .all()
    }
    pending_policy_acknowledgements = [
        article for article in policies_requiring_ack
        if article.id not in acknowledged_article_ids
    ]
    review_due_count = 0
    if current_user.can_manage_helpdesk:
        review_due_count = KnowledgeArticle.query.filter(
            KnowledgeArticle.review_date.isnot(None),
            KnowledgeArticle.review_date <= today,
        ).count()

    audit_policies = AuditPolicy.query.filter_by(status='active').count()
    audit_findings_query = AuditFinding.query
    audit_actions_query = AuditCorrectiveAction.query
    if not current_user.can_manage_compliance:
        audit_findings_query = audit_findings_query.filter_by(owner_id=current_user.id)
        audit_actions_query = audit_actions_query.filter_by(owner_id=current_user.id)
    open_audit_findings = audit_findings_query.filter(AuditFinding.status.notin_(['closed', 'accepted'])).count()
    overdue_audit_actions = audit_actions_query.filter(
        AuditCorrectiveAction.status != 'completed',
        AuditCorrectiveAction.due_date.isnot(None),
        AuditCorrectiveAction.due_date < today,
    ).count()
    audit_policy_acknowledgements = AuditPolicy.query.filter_by(
        status='active',
        requires_acknowledgement=True,
    ).all()
    acknowledged_audit_policies = {
        acknowledgement.policy_id: acknowledgement
        for acknowledgement in AuditPolicyAcknowledgement.query
        .filter_by(user_id=current_user.id)
        .all()
    }
    pending_audit_policy_acknowledgements = [
        policy for policy in audit_policy_acknowledgements
        if not policy.acknowledgement_is_current(acknowledged_audit_policies.get(policy.id))
    ]

    quick_actions = [
        ('New Ticket', 'tickets.create', 'fa-plus-circle', 'bg-blue-600 hover:bg-blue-700 text-white'),
        ('Knowledge Base', 'knowledge.list', 'fa-book-open', 'border border-gray-300 text-gray-700 hover:bg-gray-50'),
        ('Audit Policies', 'audit.index', 'fa-scale-balanced', 'border border-gray-300 text-gray-700 hover:bg-gray-50'),
    ]
    if current_user.can_manage_helpdesk:
        quick_actions.append(('Reply Templates', 'admin.reply_templates', 'fa-message', 'border border-gray-300 text-gray-700 hover:bg-gray-50'))
    if current_user.can_manage_inventory:
        quick_actions.append(('Assets', 'assets.list', 'fa-laptop', 'border border-gray-300 text-gray-700 hover:bg-gray-50'))
    if current_user.can_manage_users:
        quick_actions.append(('Users', 'admin.users', 'fa-users-gear', 'border border-gray-300 text-gray-700 hover:bg-gray-50'))

    return render_template('dashboard/index.html',
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        in_progress=in_progress,
        pending_tickets=pending_tickets,
        resolved=resolved,
        closed_tickets=closed_tickets,
        overdue=overdue,
        critical_tickets=critical_tickets,
        unassigned_tickets=unassigned_tickets,
        total_users=total_users,
        total_assets=total_assets,
        available_assets=available_assets,
        recent_tickets=recent_tickets,
        knowledge_count=knowledge_count,
        featured_articles=featured_articles,
        pending_policy_acknowledgements=pending_policy_acknowledgements,
        review_due_count=review_due_count,
        audit_policies=audit_policies,
        open_audit_findings=open_audit_findings,
        overdue_audit_actions=overdue_audit_actions,
        pending_audit_policy_acknowledgements=pending_audit_policy_acknowledgements,
        quick_actions=quick_actions,
        now=now
    )
