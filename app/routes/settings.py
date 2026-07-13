from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.user_signature import UserSignature
from app.utils.signatures import DEFAULT_SIGNATURE_HTML, normalize_signature_html, save_inline_signature_images
from app.utils.two_factor import (
    backup_code_count,
    generate_backup_codes,
    generate_totp_secret,
    hash_backup_codes,
    provisioning_uri,
    qr_code_data_uri,
    verify_totp,
)

settings = Blueprint('settings', __name__)


@settings.route('/')
@login_required
def index():
    return render_template('settings/index.html')


@settings.route('/profile')
@login_required
def profile():
    return render_template('settings/profile.html')


@settings.route('/security', methods=['GET', 'POST'])
@login_required
def security():
    setup_secret = current_user.two_factor_secret or generate_totp_secret()
    backup_codes = None

    if request.method == 'POST':
        if not current_user.can_manage_user_accounts:
            flash('Only an administrator can enable or disable MFA.', 'danger')
            return redirect(url_for('settings.security'))
        action = request.form.get('action')
        if action == 'enable':
            setup_secret = request.form.get('setup_secret', '').strip().replace(' ', '')
            code = request.form.get('code', '').strip()
            if not verify_totp(setup_secret, code):
                flash('Invalid authenticator code. Please scan/add the secret and try again.', 'danger')
            else:
                backup_codes = generate_backup_codes()
                current_user.two_factor_secret = setup_secret
                current_user.two_factor_enabled = True
                current_user.two_factor_required = False
                current_user.two_factor_backup_codes = hash_backup_codes(backup_codes)
                db.session.commit()
                flash('Two-factor authentication enabled.', 'success')
        elif action == 'disable':
            password = request.form.get('password', '')
            if not current_user.check_password(password):
                flash('Password is incorrect.', 'danger')
            else:
                current_user.two_factor_enabled = False
                current_user.two_factor_required = False
                current_user.two_factor_secret = None
                current_user.two_factor_backup_codes = None
                db.session.commit()
                flash('Two-factor authentication disabled.', 'success')
                return redirect(url_for('settings.security'))
        elif action == 'regenerate_backup':
            password = request.form.get('password', '')
            if not current_user.check_password(password):
                flash('Password is incorrect.', 'danger')
            elif not current_user.two_factor_enabled:
                flash('Enable two-factor authentication first.', 'warning')
            else:
                backup_codes = generate_backup_codes()
                current_user.two_factor_backup_codes = hash_backup_codes(backup_codes)
                db.session.commit()
                flash('New backup codes generated.', 'success')

    setup_uri = provisioning_uri(current_user, setup_secret)
    return render_template(
        'settings/security.html',
        setup_secret=setup_secret,
        provisioning_uri=setup_uri,
        qr_code_data_uri=qr_code_data_uri(setup_uri),
        backup_codes=backup_codes,
        backup_code_count=backup_code_count(current_user),
        can_manage_mfa=current_user.can_manage_user_accounts,
    )


@settings.route('/signature', methods=['GET', 'POST'])
@settings.route('/signature/<int:user_id>', methods=['GET', 'POST'])
@login_required
def signature(user_id=None):
    from app.models.user import User

    target_user = current_user
    if user_id:
        if not current_user.can_manage_system:
            flash('System owner access required.', 'danger')
            return redirect(url_for('settings.signature'))
        target_user = User.query.get_or_404(user_id)

    signature = UserSignature.for_user(target_user)

    if request.method == 'POST':
        signature.signature_enabled = request.form.get('signature_enabled') == 'on'
        signature.auto_insert_signature = request.form.get('auto_insert_signature') == 'on'
        signature_html = normalize_signature_html(request.form.get('signature_html', '').strip())
        signature.signature_html = save_inline_signature_images(signature_html, target_user.id) if signature_html else None
        db.session.commit()
        flash('Signature settings saved.', 'success')
        if current_user.can_manage_system and request.form.get('admin_return') == '1':
            return redirect(url_for('admin.signature'))
        return redirect(url_for('settings.signature', user_id=user_id) if user_id else url_for('settings.signature'))

    return render_template(
        'settings/signature.html',
        signature=signature,
        target_user=target_user,
        default_signature=DEFAULT_SIGNATURE_HTML,
        admin_mode=False,
    )
