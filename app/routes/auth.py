from urllib.parse import urlparse, urljoin

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app import db
from app.utils.two_factor import (
    generate_backup_codes,
    generate_totp_secret,
    hash_backup_codes,
    provisioning_uri,
    verify_backup_code,
    verify_totp,
)

auth = Blueprint('auth', __name__)


def is_safe_redirect(target):
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def render_login(**context):
    return render_template('auth/login.html', **context)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    next_url = request.args.get('next') or request.form.get('next')
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account is inactive. Please contact your administrator.', 'warning')
                return render_login(email=email, next_url=next_url)
            if not user.department_id:
                flash('Department is not assigned to your account. Please contact your administrator.', 'danger')
                return render_login(email=email, next_url=next_url)
            if not user.company_domain:
                flash('Company / Domain is not assigned to your account. Please contact your administrator.', 'danger')
                return render_login(email=email, next_url=next_url)
            if user.two_factor_enabled:
                session['two_factor_user_id'] = user.id
                session['two_factor_remember'] = remember
                session['two_factor_next'] = next_url if is_safe_redirect(next_url) else ''
                return redirect(url_for('auth.two_factor'))
            if user.two_factor_required:
                session['two_factor_setup_user_id'] = user.id
                session['two_factor_setup_remember'] = remember
                session['two_factor_setup_next'] = next_url if is_safe_redirect(next_url) else ''
                return redirect(url_for('auth.two_factor_setup'))
            login_user(user, remember=remember)
            if is_safe_redirect(next_url):
                return redirect(next_url)
            return redirect(url_for('dashboard.index'))
        flash('Invalid email or password.', 'danger')
    return render_login(email=request.args.get('email', ''), next_url=next_url)


@auth.route('/two-factor', methods=['GET', 'POST'])
def two_factor():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    user_id = session.get('two_factor_user_id')
    if not user_id:
        flash('Please sign in again.', 'warning')
        return redirect(url_for('auth.login'))
    user = User.query.get(user_id)
    if not user or not user.two_factor_enabled:
        session.pop('two_factor_user_id', None)
        session.pop('two_factor_remember', None)
        session.pop('two_factor_next', None)
        flash('Please sign in again.', 'warning')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        verified = verify_totp(user.two_factor_secret, code)
        if not verified:
            verified = verify_backup_code(user, code)
            if verified:
                db.session.commit()
        if verified:
            remember = bool(session.pop('two_factor_remember', False))
            next_url = session.pop('two_factor_next', '')
            session.pop('two_factor_user_id', None)
            login_user(user, remember=remember)
            if is_safe_redirect(next_url):
                return redirect(next_url)
            return redirect(url_for('dashboard.index'))
        flash('Invalid authentication code.', 'danger')

    return render_template('auth/two_factor.html', user=user)


@auth.route('/two-factor/setup', methods=['GET', 'POST'])
def two_factor_setup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    user_id = session.get('two_factor_setup_user_id')
    if not user_id:
        flash('Please sign in again.', 'warning')
        return redirect(url_for('auth.login'))
    user = User.query.get(user_id)
    if not user:
        session.pop('two_factor_setup_user_id', None)
        session.pop('two_factor_setup_remember', None)
        session.pop('two_factor_setup_next', None)
        flash('Please sign in again.', 'warning')
        return redirect(url_for('auth.login'))

    setup_secret = request.form.get('setup_secret', '').strip().replace(' ', '') if request.method == 'POST' else ''
    if not setup_secret:
        setup_secret = generate_totp_secret()

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if verify_totp(setup_secret, code):
            backup_codes = generate_backup_codes()
            user.two_factor_secret = setup_secret
            user.two_factor_enabled = True
            user.two_factor_required = False
            user.two_factor_backup_codes = hash_backup_codes(backup_codes)
            db.session.commit()

            remember = bool(session.pop('two_factor_setup_remember', False))
            next_url = session.pop('two_factor_setup_next', '')
            session.pop('two_factor_setup_user_id', None)
            login_user(user, remember=remember)
            return render_template('auth/two_factor_setup.html', user=user, backup_codes=backup_codes, setup_complete=True, next_url=next_url)
        flash('Invalid authenticator code. Please try again.', 'danger')

    return render_template(
        'auth/two_factor_setup.html',
        user=user,
        setup_secret=setup_secret,
        provisioning_uri=provisioning_uri(user, setup_secret),
        setup_complete=False,
    )

@auth.route('/logout')
@login_required
def logout():
    session.pop('two_factor_user_id', None)
    session.pop('two_factor_remember', None)
    session.pop('two_factor_next', None)
    session.pop('two_factor_setup_user_id', None)
    session.pop('two_factor_setup_remember', None)
    session.pop('two_factor_setup_next', None)
    logout_user()
    return redirect(url_for('auth.login'))
