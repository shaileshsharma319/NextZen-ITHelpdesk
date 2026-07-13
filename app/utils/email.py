from flask_mail import Message
import imaplib
import email
import re
import secrets
import os
import uuid
from urllib.parse import quote
from email.header import decode_header, make_header
from email.utils import parseaddr
from flask import current_app
from markupsafe import escape
from app import mail, db
from app.utils.formatting import email_content


def _get_config():
    from app.models.email_config import EmailConfig
    return EmailConfig.get()


def _apply_config(cfg):
    """Temporarily override Flask-Mail config with DB settings."""
    if not cfg:
        return
    app = current_app._get_current_object()
    app.config.update(
        MAIL_SERVER   = cfg.mail_server,
        MAIL_PORT     = cfg.mail_port,
        MAIL_USE_TLS  = cfg.mail_use_tls,
        MAIL_USE_SSL  = cfg.mail_use_ssl,
        MAIL_USERNAME = cfg.mail_username,
        MAIL_PASSWORD = cfg.mail_password,
        MAIL_DEFAULT_SENDER = (cfg.mail_from_name, cfg.mail_from),
        MAIL_DEBUG    = False,
    )
    mail.init_app(app)


def _build_msg(subject, recipients, body, cfg=None):
    sender = None
    if cfg:
        sender = (cfg.mail_from_name, cfg.mail_from)
    msg = Message(subject=subject, recipients=recipients, sender=sender)
    msg.body = body
    if cfg and cfg.notify_cc:
        msg.cc = [e.strip() for e in cfg.notify_cc.split(',') if e.strip()]
    return msg


def friendly_email_error(error):
    error_text = str(error)
    lowered = error_text.lower()
    if 'allow list' in lowered or 'allowlist' in lowered:
        return (
            'Email provider rejected this recipient because it is not on the SMTP account allow list. '
            'Add the requester email to the provider allow list, or use a production SMTP account such as Gmail, '
            'Hostinger, Microsoft 365, or Zoho.'
        )
    if 'authentication' in lowered or '535' in lowered:
        return 'SMTP login failed. Please check the email username and app password in Admin > Email Config.'
    if 'relay' in lowered or '554' in lowered:
        return 'SMTP relay was rejected by the email provider. Please check sender address, domain permissions, and SMTP account policy.'
    return error_text


DEFAULT_SIGNATURE_HTML = (
    '<div class="helpdesk-signature" data-helpdesk-signature="1">'
    '<p>Thanks &amp; Regards,<br><strong>IT Support Team</strong></p>'
    '<p><strong>Winsoft Technologies</strong><br>'
    '<a href="https://www.winsoftech.com">www.winsoftech.com</a></p>'
    '</div>'
)


def _user_signature_settings(user):
    if not user:
        return None
    try:
        from app.models.user_signature import UserSignature
        return UserSignature.query.filter_by(user_id=user.id).first()
    except Exception:
        return None


def _signature_html(cfg, user=None):
    user_signature = _user_signature_settings(user)
    if user_signature:
        if not user_signature.signature_enabled:
            return ''
        signature = (user_signature.signature_html or getattr(cfg, 'signature_html', None) or DEFAULT_SIGNATURE_HTML).strip()
    else:
        if cfg and not getattr(cfg, 'signature_enabled', True):
            return ''
        signature = (getattr(cfg, 'signature_html', None) or DEFAULT_SIGNATURE_HTML).strip()
    if 'data-helpdesk-signature' not in signature:
        signature = f'<div class="helpdesk-signature" data-helpdesk-signature="1">{signature}</div>'
    return str(email_content(signature))


def _append_signature_html(html, cfg, user=None):
    html = html or ''
    if 'data-helpdesk-signature' in html:
        return html
    signature = _signature_html(cfg, user)
    if not signature:
        return html
    return f'{html}<br>{signature}'


def _html_to_text(html):
    return _strip_html(html).replace('\xa0', ' ').strip()


def _ticket_ref(ticket):
    return escape(ticket.ticket_number or f'HD-{ticket.id:05d}')


def _label(value):
    return escape(str(value or '').replace('_', ' ').title())


def _badge(text, bg, color):
    return (
        f'<span style="display:inline-block;padding:4px 10px;border-radius:999px;'
        f'background:{bg};color:{color};font-size:12px;font-weight:700;line-height:16px;">'
        f'{escape(text)}</span>'
    )


def _status_badge(status):
    colors = {
        'open': ('#dbeafe', '#1d4ed8'),
        'in_progress': ('#fef3c7', '#92400e'),
        'pending': ('#f3e8ff', '#7e22ce'),
        'resolved': ('#dcfce7', '#166534'),
        'closed': ('#e5e7eb', '#374151'),
    }
    bg, color = colors.get(status, ('#e5e7eb', '#374151'))
    return _badge(str(status or '').replace('_', ' ').title(), bg, color)


def _priority_badge(priority):
    colors = {
        'low': ('#ecfdf5', '#047857'),
        'medium': ('#eff6ff', '#1d4ed8'),
        'high': ('#fff7ed', '#c2410c'),
        'critical': ('#fef2f2', '#b91c1c'),
    }
    bg, color = colors.get(priority, ('#e5e7eb', '#374151'))
    return _badge(str(priority or '').upper(), bg, color)


def _detail_table(rows):
    cells = []
    for label, value in rows:
        cells.append(
            '<tr>'
            '<td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;'
            'color:#6b7280;font-size:13px;width:38%;vertical-align:top;">'
            f'{escape(label)}'
            '</td>'
            '<td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;'
            'color:#111827;font-size:13px;font-weight:600;vertical-align:top;">'
            f'{value}'
            '</td>'
            '</tr>'
        )
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="border-collapse:collapse;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">'
        + ''.join(cells) +
        '</table>'
    )


def _action_button(label, href='#'):
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:18px;">'
        '<tr><td style="background:#2563eb;border-radius:10px;">'
        f'<a href="{escape(href)}" style="display:inline-block;padding:11px 18px;'
        'font-size:14px;font-weight:700;color:#ffffff;text-decoration:none;">'
        f'{escape(label)}</a>'
        '</td></tr></table>'
    )


def _email_shell(preheader, title, eyebrow, intro, content, footer_note=None):
    footer_note = footer_note or 'This notification was sent by IT HelpDesk. Please keep the ticket reference in replies.'
    return f"""<!doctype html>
<html>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;color:#111827;">
  <div style="display:none;max-height:0;overflow:hidden;color:#f3f4f6;font-size:1px;line-height:1px;">
    {escape(preheader)}
  </div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:24px 0;">
    <tr>
      <td align="center" style="padding:0 12px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:680px;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid #e5e7eb;">
          <tr>
            <td style="background:#0f172a;padding:22px 26px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#93c5fd;font-weight:700;">{escape(eyebrow)}</div>
                    <div style="font-size:22px;line-height:30px;color:#ffffff;font-weight:800;margin-top:6px;">{escape(title)}</div>
                  </td>
                  <td align="right" style="font-size:13px;color:#cbd5e1;font-weight:700;">IT HelpDesk</td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:26px;">
              <p style="margin:0 0 18px 0;color:#374151;font-size:15px;line-height:23px;">{intro}</p>
              {content}
            </td>
          </tr>
          <tr>
            <td style="background:#f9fafb;border-top:1px solid #e5e7eb;padding:16px 26px;color:#6b7280;font-size:12px;line-height:18px;">
              {escape(footer_note)}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _ticket_summary(ticket, include_requester=False, include_description=False, requester_email=None, assignee=None):
    rows = [
        ('Ticket Number', f'<strong>{_ticket_ref(ticket)}</strong>'),
        ('Subject', escape(ticket.email_subject or ticket.title)),
        ('Status', _status_badge(ticket.status)),
        ('Priority', _priority_badge(ticket.priority)),
        ('Source', _label(ticket.source)),
    ]
    if include_requester:
        requester = requester_email or getattr(ticket, 'email_from', None) or (ticket.creator.email if ticket.creator else '')
        rows.append(('Requester', escape(requester or '-')))
    if assignee:
        rows.append(('Assignee', escape(assignee.name)))
    if getattr(ticket, 'category', None):
        category = ticket.category
        if getattr(ticket, 'sub_category', None):
            category = f'{category} / {ticket.sub_category}'
        rows.append(('Category', escape(category)))

    html = _detail_table(rows)
    if include_description:
        html += (
            '<div style="margin-top:18px;">'
            '<div style="font-size:13px;color:#6b7280;font-weight:700;margin-bottom:8px;">Description</div>'
            '<div style="border:1px solid #e5e7eb;border-radius:12px;padding:14px;color:#111827;font-size:14px;line-height:22px;">'
            f'{email_content(ticket.description)}'
            '</div></div>'
        )
    return html


def _set_html_body(msg, html, cfg, user=None):
    html = _append_signature_html(html, cfg, user)
    msg.html = html
    msg.body = _html_to_text(html)
    return msg


def send_ticket_created(ticket, user):
    cfg = _get_config()
    if cfg:
        if not cfg.notify_ticket_created:
            return
        _apply_config(cfg)
    # Skip obviously fake/placeholder emails
    if not user.email or user.email.endswith('@helpdesk.com'):
        raise Exception(f'User {user.name} has no real email address set ({user.email}). Please update it in Admin → Users.')
    html = f"""
<p>Hello {escape(user.name)},</p>
<p>Your ticket has been successfully submitted.</p>
<table cellpadding="4" cellspacing="0">
    <tr><td><strong>Ticket ID</strong></td><td>#{ticket.id}</td></tr>
    <tr><td><strong>Title</strong></td><td>{escape(ticket.title)}</td></tr>
    <tr><td><strong>Priority</strong></td><td>{escape(ticket.priority.upper())}</td></tr>
    <tr><td><strong>Status</strong></td><td>{escape(ticket.status.replace('_', ' ').title())}</td></tr>
</table>
<p><strong>Description</strong></p>
{email_content(ticket.description)}
<p>We will get back to you as soon as possible.</p>
"""
    msg = _build_msg(
        subject    = f'[Ticket #{ticket.id}] New Ticket: {ticket.title}',
        recipients = [user.email],
        body       = _html_to_text(html),
        cfg=cfg,
    )
    _set_html_body(msg, html, cfg, user)
    mail.send(msg)


def send_ticket_updated(ticket, user):
    cfg = _get_config()
    if cfg:
        if not cfg.notify_ticket_updated:
            return
        _apply_config(cfg)
    msg = _build_msg(
        subject    = f'[Ticket #{ticket.id}] Status Update: {ticket.status.replace("_", " ").title()}',
        recipients = [user.email],
        body       = f"""Hello {user.name},

Your ticket has been updated.

Ticket ID : #{ticket.id}
Title     : {ticket.title}
Priority  : {ticket.priority.upper()}
Status    : {ticket.status.replace('_', ' ').title()}

Login to view more details.

IT HelpDesk Team""",
        cfg=cfg,
    )
    mail.send(msg)


def send_ticket_assigned(ticket, assignee):
    cfg = _get_config()
    if cfg:
        if not cfg.notify_ticket_assigned:
            return
        _apply_config(cfg)
    msg = _build_msg(
        subject    = f'[Ticket #{ticket.id}] Assigned to You: {ticket.title}',
        recipients = [assignee.email],
        body       = f"""Hello {assignee.name},

A ticket has been assigned to you.

Ticket ID   : #{ticket.id}
Title       : {ticket.title}
Priority    : {ticket.priority.upper()}
Status      : {ticket.status.replace('_', ' ').title()}
Description : {ticket.description}

Please login to handle this ticket.

IT HelpDesk Team""",
        cfg=cfg,
    )
    mail.send(msg)


def send_email_ticket_notification(ticket, sender_email):
    """Notify helpdesk staff that a ticket was created from an inbound email."""
    cfg = _get_config()
    if not cfg or not cfg.notify_email_ticket:
        return
    _apply_config(cfg)
    from app.models.user import User
    admins_staff = User.query.filter(
        User.role.in_(['master_admin', 'admin_staff']), User._is_active == True
    ).all()
    recipients = [u.email for u in admins_staff]
    if not recipients:
        return
    msg = _build_msg(
        subject    = f'[Email Ticket #{ticket.id}] {ticket.title}',
        recipients = recipients,
        body       = f"""New ticket created from inbound email.

Ticket ID   : #{ticket.id}
Title       : {ticket.title}
Priority    : {ticket.priority.upper()}
From Email  : {sender_email}
Description :
{ticket.description}

Login to assign and handle this ticket.

IT HelpDesk Team""",
        cfg=cfg,
    )
    mail.send(msg)


def send_welcome_email(user, plain_password):
    cfg = _get_config()
    if cfg:
        _apply_config(cfg)
    msg = _build_msg(
        subject    = 'Welcome to IT HelpDesk - Your Account Details',
        recipients = [user.email],
        body       = f"""Hello {user.name},

Your IT HelpDesk account has been created by an administrator.

Email    : {user.email}
Password : {plain_password}
Role     : {user.role.title()}

Please login and change your password immediately.

IT HelpDesk Team""",
        cfg=cfg,
    )
    mail.send(msg)


def test_email_config(cfg, test_recipient=None):
    """Send a test email using provided config. Returns (success, error_msg)."""
    try:
        _apply_config(cfg)
        recipient = test_recipient or cfg.mail_username
        msg = Message(
            subject    = 'IT HelpDesk — Email Config Test',
            recipients = [recipient],
            sender     = (cfg.mail_from_name, cfg.mail_from),
            body       = 'This is a test email from IT HelpDesk. Your email configuration is working correctly.',
        )
        _set_html_body(
            msg,
            '<p>This is a test email from IT HelpDesk. Your email configuration is working correctly.</p>',
            cfg,
            None,
        )
        mail.send(msg)
        return True, None
    except Exception as e:
        return False, str(e)



def _strip_html(value):
    value = value or ''
    value = re.sub(r'<br\s*/?>', '\n', value, flags=re.I)
    value = re.sub(r'</p\s*>', '\n', value, flags=re.I)
    value = re.sub(r'<[^>]+>', '', value)
    return value.strip()


def send_ticket_created(ticket, user):
    cfg = _get_config()
    if cfg:
        if not cfg.notify_ticket_created:
            return
        _apply_config(cfg)
    if not user.email or user.email.endswith('@helpdesk.com'):
        raise Exception(f'User {user.name} has no real email address set ({user.email}). Please update it in Admin > Users.')

    html = _email_shell(
        preheader=f'Your ticket {_ticket_ref(ticket)} has been created.',
        title='Ticket Created',
        eyebrow='Request received',
        intro=f'Hello {escape(user.name)}, your request has been successfully submitted. Our support team will review it and respond as soon as possible.',
        content=_ticket_summary(ticket, include_description=True) + _action_button('View Ticket'),
    )
    msg = _build_msg(
        subject=f'[{ticket.ticket_number or ticket.id}] Ticket Created: {ticket.title}',
        recipients=[user.email],
        body=_html_to_text(html),
        cfg=cfg,
    )
    _set_html_body(msg, html, cfg, user)
    mail.send(msg)


def send_ticket_updated(ticket, user):
    cfg = _get_config()
    if cfg:
        if not cfg.notify_ticket_updated:
            return
        _apply_config(cfg)

    html = _email_shell(
        preheader=f'Ticket {_ticket_ref(ticket)} status is now {ticket.status.replace("_", " ").title()}.',
        title='Ticket Updated',
        eyebrow='Status change',
        intro=f'Hello {escape(user.name)}, your ticket has been updated. Please review the latest status below.',
        content=_ticket_summary(ticket) + _action_button('View Ticket'),
    )
    msg = _build_msg(
        subject=f'[{ticket.ticket_number or ticket.id}] Status Update: {ticket.status.replace("_", " ").title()}',
        recipients=[user.email],
        body=_html_to_text(html),
        cfg=cfg,
    )
    _set_html_body(msg, html, cfg, user)
    mail.send(msg)


def send_ticket_assigned(ticket, assignee):
    cfg = _get_config()
    if cfg:
        if not cfg.notify_ticket_assigned:
            return
        _apply_config(cfg)

    html = _email_shell(
        preheader=f'Ticket {_ticket_ref(ticket)} has been assigned to you.',
        title='Ticket Assigned',
        eyebrow='Action required',
        intro=f'Hello {escape(assignee.name)}, a ticket has been assigned to you. Please review and take ownership.',
        content=_ticket_summary(ticket, include_requester=True, include_description=True, assignee=assignee) + _action_button('Open Ticket'),
    )
    msg = _build_msg(
        subject=f'[{ticket.ticket_number or ticket.id}] Assigned to You: {ticket.title}',
        recipients=[assignee.email],
        body=_html_to_text(html),
        cfg=cfg,
    )
    _set_html_body(msg, html, cfg, assignee)
    mail.send(msg)


def send_email_ticket_notification(ticket, sender_email):
    cfg = _get_config()
    if not cfg or not cfg.notify_email_ticket:
        return
    _apply_config(cfg)
    from app.models.user import User

    admins_staff = User.query.filter(
        User.role.in_(['master_admin', 'admin_staff']), User._is_active == True
    ).all()
    recipients = [u.email for u in admins_staff if u.email]
    if not recipients:
        return

    html = _email_shell(
        preheader=f'New inbound email ticket {_ticket_ref(ticket)} from {sender_email}.',
        title='New Email Ticket',
        eyebrow='Inbound email',
        intro='A new ticket was automatically created from an inbound email. Please assign and handle it from the helpdesk queue.',
        content=_ticket_summary(ticket, include_requester=True, include_description=True, requester_email=sender_email) + _action_button('Review Ticket'),
    )
    msg = _build_msg(
        subject=f'[{ticket.ticket_number or ticket.id}] Email Ticket: {ticket.title}',
        recipients=recipients,
        body=_html_to_text(html),
        cfg=cfg,
    )
    _set_html_body(msg, html, cfg, None)
    mail.send(msg)


def send_welcome_email(user, plain_password):
    cfg = _get_config()
    if cfg:
        _apply_config(cfg)

    html = _email_shell(
        preheader='Your IT HelpDesk account has been created.',
        title='Welcome to IT HelpDesk',
        eyebrow='Account created',
        intro=f'Hello {escape(user.name)}, your IT HelpDesk account has been created by an administrator. Please sign in and change your password immediately.',
        content=_detail_table([
            ('Name', escape(user.name)),
            ('Email', escape(user.email)),
            ('Temporary Password', f'<code style="font-weight:700;color:#111827;">{escape(plain_password)}</code>'),
            ('Role', escape(user.role_label if hasattr(user, 'role_label') else user.role.title())),
        ]) + _action_button('Open HelpDesk'),
        footer_note='For security, change your temporary password after first login and set up MFA if requested.',
    )
    msg = _build_msg(
        subject='Welcome to IT HelpDesk - Your Account Details',
        recipients=[user.email],
        body=_html_to_text(html),
        cfg=cfg,
    )
    _set_html_body(msg, html, cfg, None)
    mail.send(msg)


def test_email_config(cfg, test_recipient=None):
    try:
        _apply_config(cfg)
        recipient = test_recipient or cfg.mail_username
        html = _email_shell(
            preheader='Your IT HelpDesk email configuration is working.',
            title='Email Config Test',
            eyebrow='SMTP verified',
            intro='This is a test email from IT HelpDesk. Your email configuration is working correctly.',
            content=_detail_table([
                ('SMTP Host', escape(cfg.mail_server)),
                ('Sender', escape(cfg.mail_from)),
                ('Port', escape(cfg.mail_port)),
                ('TLS', escape('Enabled' if cfg.mail_use_tls else 'Disabled')),
            ]),
            footer_note='If this email appears correctly in Outlook, Zoho, Hostinger, and webmail, notifications are ready.',
        )
        msg = Message(
            subject='IT HelpDesk - Email Config Test',
            recipients=[recipient],
            sender=(cfg.mail_from_name, cfg.mail_from),
            body=_html_to_text(html),
        )
        _set_html_body(msg, html, cfg, None)
        mail.send(msg)
        return True, None
    except Exception as e:
        return False, str(e)


def _ticket_reply_recipient(ticket):
    if getattr(ticket, 'email_from', None):
        return ticket.email_from
    if ticket.creator and ticket.creator.email:
        return ticket.creator.email
    return None


def send_ticket_reply(ticket, reply, attachments=None):
    """Send a public/email reply to the original requester or inbound email sender."""
    cfg = _get_config()
    if not cfg:
        raise Exception('Email configuration is not set.')
    recipient = _ticket_reply_recipient(ticket)
    if not recipient:
        raise Exception('Ticket has no requester email address.')
    if recipient.endswith('@helpdesk.com') and not getattr(ticket, 'email_from', None):
        raise Exception(f'Requester has placeholder email address ({recipient}).')

    _apply_config(cfg)
    subject = f'Re: {ticket.email_subject or ticket.title} [{ticket.ticket_number or ticket.id}]'
    html = f"""
<p>Hello,</p>
{email_content(reply.message)}
<hr>
<p style="font-size:12px;color:#6b7280">
Ticket: {escape(ticket.ticket_number or ('#' + str(ticket.id)))}<br>
Status: {escape(ticket.status.replace('_', ' ').title())}
</p>
"""
    msg = _build_msg(subject=subject, recipients=[recipient], body=_html_to_text(html), cfg=cfg)
    _set_html_body(msg, html, cfg, reply.author)
    if ticket.email_message_id:
        msg.extra_headers = {
            'In-Reply-To': ticket.email_message_id,
            'References': ticket.email_message_id,
        }
    for attachment in attachments or []:
        try:
            from flask import current_app
            import os
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'tickets', str(ticket.id), attachment.stored_filename)
            with open(path, 'rb') as fp:
                msg.attach(attachment.original_filename, attachment.content_type or 'application/octet-stream', fp.read())
        except Exception:
            pass
    mail.send(msg)


def send_ticket_reply(ticket, reply, attachments=None):
    """Send a public/email reply with an Outlook-safe modern format."""
    cfg = _get_config()
    if not cfg:
        raise Exception('Email configuration is not set.')
    recipient = _ticket_reply_recipient(ticket)
    if not recipient:
        raise Exception('Ticket has no requester email address.')
    if recipient.endswith('@helpdesk.com') and not getattr(ticket, 'email_from', None):
        raise Exception(f'Requester has placeholder email address ({recipient}).')

    _apply_config(cfg)
    subject = f'Re: {ticket.email_subject or ticket.title} [{ticket.ticket_number or ticket.id}]'
    reply_body = (
        '<div style="border:1px solid #e5e7eb;border-radius:12px;padding:14px;'
        'color:#111827;font-size:14px;line-height:22px;">'
        f'{email_content(reply.message)}'
        '</div>'
    )
    html = _email_shell(
        preheader=f'New reply on ticket {_ticket_ref(ticket)}.',
        title='Support Reply',
        eyebrow='Ticket response',
        intro='Hello, our support team has replied to your ticket. Please review the response below.',
        content=reply_body + '<div style="height:16px;line-height:16px;">&nbsp;</div>' + _ticket_summary(ticket),
        footer_note='You can reply to this email to continue the conversation. Keep the ticket reference in the subject.',
    )
    msg = _build_msg(subject=subject, recipients=[recipient], body=_html_to_text(html), cfg=cfg)
    _set_html_body(msg, html, cfg, reply.author)
    if ticket.email_message_id:
        msg.extra_headers = {
            'In-Reply-To': ticket.email_message_id,
            'References': ticket.email_message_id,
        }
    for attachment in attachments or []:
        try:
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'tickets', str(ticket.id), attachment.stored_filename)
            with open(path, 'rb') as fp:
                msg.attach(attachment.original_filename, attachment.content_type or 'application/octet-stream', fp.read())
        except Exception:
            pass
    mail.send(msg)


def _content_id(part):
    cid = part.get('Content-ID') or part.get('X-Attachment-Id') or ''
    return cid.strip().strip('<>').strip()


def _inline_image_keys(part):
    keys = []
    for value in (
        part.get('Content-ID'),
        part.get('X-Attachment-Id'),
        part.get('Content-Location'),
        part.get_filename(),
    ):
        value = (value or '').strip().strip('<>').strip()
        if value and value not in keys:
            keys.append(value)
    return keys


def _safe_inline_ext(content_type, filename):
    allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    if filename and '.' in filename:
        ext = filename.rsplit('.', 1)[1].lower()
        if ext in allowed:
            return ext
    return {
        'image/png': 'png',
        'image/jpeg': 'jpg',
        'image/gif': 'gif',
        'image/webp': 'webp',
    }.get(content_type, 'bin')


def _save_inline_email_images(msg, ticket, uploaded_by):
    """Save Outlook/Gmail cid: inline images and return {cid: static_url}."""
    from app.models.reply import TicketAttachment
    cid_map = {}
    if not msg.is_multipart():
        return cid_map

    upload_root = current_app.config['UPLOAD_FOLDER']
    folder = os.path.join(upload_root, 'tickets', str(ticket.id))
    os.makedirs(folder, exist_ok=True)

    for part in msg.walk():
        content_type = part.get_content_type()
        image_keys = _inline_image_keys(part)
        if not image_keys or not content_type.startswith('image/'):
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        filename = part.get_filename() or f'{cid}'
        ext = _safe_inline_ext(content_type, filename)
        if ext == 'bin':
            continue
        stored = f'{uuid.uuid4().hex}.{ext}'
        path = os.path.join(folder, stored)
        with open(path, 'wb') as handle:
            handle.write(payload)
        original = filename if '.' in filename else f'{filename}.{ext}'
        attachment = TicketAttachment(
            ticket_id=ticket.id,
            reply_id=None,
            original_filename=original[:255],
            stored_filename=stored,
            content_type=content_type,
            file_size=len(payload),
            uploaded_by=uploaded_by,
        )
        db.session.add(attachment)
        url = f'/static/uploads/tickets/{ticket.id}/{stored}'
        for key in image_keys:
            cid_map[key] = url
    return cid_map


def _replace_cid_sources(body, cid_map):
    if not body or not cid_map:
        return body
    for cid, url in cid_map.items():
        variants = {cid, quote(cid), quote(cid, safe='@.-_')}
        for variant in variants:
            body = re.sub(rf'cid:{re.escape(variant)}', url, body, flags=re.I)
    return body


def _decode(value):
    if not value:
        return ''
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _message_body(msg):
    html_body = None
    text_body = None
    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = part.get('Content-Disposition', '') or ''
            if 'attachment' in content_disposition.lower():
                continue
            content_type = part.get_content_type()
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or 'utf-8'
            try:
                decoded = payload.decode(charset, errors='replace')
            except Exception:
                decoded = payload.decode('utf-8', errors='replace')
            if content_type == 'text/plain' and not text_body:
                text_body = decoded
            elif content_type == 'text/html' and not html_body:
                html_body = decoded
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or 'utf-8'
            text_body = payload.decode(charset, errors='replace')
    return (html_body or text_body or '').strip()


def _resolve_email_requester_user(sender_name, sender_email):
    from app.models.user import User
    user = User.query.filter_by(email=sender_email).first()
    if user:
        return user

    system_email = 'email-requester@helpdesk.local'
    user = User.query.filter_by(username='system_email_requester').first()
    if user:
        return user

    user = User(
        name='Email Requester',
        email=system_email,
        role='user',
        username='system_email_requester',
    )
    user._is_active = False
    user.set_password(secrets.token_urlsafe(12))
    db.session.add(user)
    db.session.flush()
    return user


def fetch_inbound_email_tickets(limit=25):
    """Fetch unread IMAP mail and convert each message into a ticket."""
    cfg = _get_config()
    if not cfg or not getattr(cfg, 'inbound_enabled', False):
        return 0, 'Inbound email is not enabled.'
    if not cfg.imap_server or not cfg.imap_username or not cfg.imap_password:
        return 0, 'IMAP settings are incomplete.'

    from app.models.ticket import Ticket
    from app.models.reply import TicketActivity
    from app.routes.tickets import generate_ticket_number, SLA_HOURS
    from datetime import datetime, timedelta

    mailbox = imaplib.IMAP4_SSL(cfg.imap_server, cfg.imap_port or 993) if cfg.imap_use_ssl else imaplib.IMAP4(cfg.imap_server, cfg.imap_port or 143)
    created = 0
    try:
        mailbox.login(cfg.imap_username, cfg.imap_password)
        mailbox.select(cfg.imap_folder or 'INBOX')
        status, data = mailbox.uid('search', None, 'UNSEEN')
        if status != 'OK':
            return 0, 'Unable to search mailbox.'
        uids = data[0].split()[:limit]
        for uid in uids:
            status, msg_data = mailbox.uid('fetch', uid, '(RFC822)')
            if status != 'OK' or not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            subject = _decode(msg.get('Subject')) or '(No subject)'
            sender_name, sender_email = parseaddr(_decode(msg.get('From')))
            sender_email = (sender_email or '').strip().lower()
            if not sender_email:
                continue
            message_id = msg.get('Message-ID')
            if message_id and Ticket.query.filter_by(email_message_id=message_id).first():
                mailbox.uid('store', uid, '+FLAGS', '(\\Seen)')
                continue
            body = _message_body(msg) or '(No message body)'
            requester = _resolve_email_requester_user(sender_name, sender_email)
            is_external_requester = getattr(requester, 'username', None) == 'system_email_requester'
            ticket = Ticket(
                ticket_number=generate_ticket_number('email', requester, location_code='EXT' if is_external_requester else None),
                title=subject[:200],
                description=body,
                ticket_type='incident',
                priority='medium',
                status='open',
                source='email',
                tags='email',
                impact='medium',
                urgency='medium',
                user_id=requester.id,
                sla_due=datetime.utcnow() + timedelta(hours=SLA_HOURS['medium']),
                email_message_id=message_id,
                email_from=sender_email,
                email_to=cfg.mail_from,
                email_cc=msg.get('Cc'),
                email_subject=subject,
                is_auto_generated=True,
            )
            db.session.add(ticket)
            db.session.flush()
            from app.utils.assignment import apply_auto_assignment
            apply_auto_assignment(ticket)
            cid_map = _save_inline_email_images(msg, ticket, requester.id)
            ticket.description = _replace_cid_sources(body, cid_map)
            db.session.add(TicketActivity(ticket_id=ticket.id, activity_type='email_import', description=f'Inbound email imported from {sender_email}', user_id=None))
            mailbox.uid('store', uid, '+FLAGS', '(\\Seen)')
            created += 1
        db.session.commit()
        return created, None
    except Exception as exc:
        db.session.rollback()
        return created, str(exc)
    finally:
        try:
            mailbox.logout()
        except Exception:
            pass
