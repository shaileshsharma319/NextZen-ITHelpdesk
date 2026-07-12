from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
from app import db
from app.models.software import Software, SoftwareInstallation
from app.models.asset import Asset
from app.models.user import User

software = Blueprint('software', __name__)

def staff_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.can_manage_inventory:
            flash('Access denied.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


def license_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.can_manage_licenses:
            flash('License access denied.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


@software.route('/')
@login_required
@staff_required
def list():
    search   = request.args.get('search', '')
    category = request.args.get('category', '')
    edition  = request.args.get('edition', '')
    user_id  = request.args.get('user_id', '')

    query = Software.query

    if search:
        query = query.filter(Software.name.ilike(f'%{search}%'))
    if category:
        query = query.filter(Software.category == category)
    if edition:
        query = query.filter(Software.license_edition == edition)
    if user_id:
        query = query.filter(Software.installations.any(
            SoftwareInstallation.asset.has(Asset.assigned_user_id == int(user_id))
        ))

    software_list = query.order_by(Software.name).all()
    all_users = User.query.filter(User.assets.any()).order_by(User.name).all()

    return render_template('software/list.html',
        software_list=software_list,
        search=search,
        category=category,
        user_id=user_id,
        all_users=all_users
    )


@software.route('/api/assets')
@login_required
@staff_required
def api_assets():
    from flask import jsonify
    assets = Asset.query.order_by(Asset.name).all()
    return jsonify([{
        'id':           a.id,
        'name':         a.name,
        'asset_tag':    a.asset_tag,
        'asset_type':   a.asset_type,
        'brand':        a.brand or '',
        'model':        a.model or '',
        'serial_number':a.serial_number or '',
        'hostname':     a.hostname or '',
        'ip_address':   a.ip_address or '',
        'status':       a.status,
        'department':   a.department.name if a.department else '',
        'user_name':    a.assigned_user.name if a.assigned_user else '',
        'user_email':   a.assigned_user.email if a.assigned_user else '',
        'user_initial': a.assigned_user.name[0].upper() if a.assigned_user else '',
    } for a in assets])



@software.route('/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create():
    assets = Asset.query.order_by(Asset.name).all()
    today  = datetime.utcnow().date().strftime('%Y-%m-%d')

    if request.method == 'POST':
        # ── Save software ──
        sw = Software(
            name         = request.form.get('name'),
            version      = request.form.get('version'),
            vendor       = request.form.get('vendor'),
            category     = request.form.get('category', 'other'),
            license_type = request.form.get('license_type', 'commercial'),
            license_edition = request.form.get('license_edition') or None,
            license_key  = request.form.get('license_key') or None,
            license_seats= int(request.form.get('license_seats', 1)),
            license_expiry= request.form.get('license_expiry') or None,
            notes        = request.form.get('notes')
        )
        db.session.add(sw)
        db.session.commit()

        # ── Install on selected assets ──
        asset_ids      = request.form.getlist('asset_ids')
        installed_date = request.form.get('installed_date') or None
        for asset_id in asset_ids:
            if not SoftwareInstallation.query.filter_by(
                software_id=sw.id, asset_id=int(asset_id)
            ).first():
                db.session.add(SoftwareInstallation(
                    software_id    = sw.id,
                    asset_id       = int(asset_id),
                    installed_date = installed_date,
                    installed_by_id= current_user.id
                ))
        db.session.commit()
        flash(f'Software "{sw.name}" added successfully with {len(asset_ids)} asset(s) installed!', 'success')
        return redirect(url_for('software.list'))

    from sqlalchemy import func
    min_ids = db.session.query(func.min(Software.id)).group_by(Software.name, Software.version).scalar_subquery()
    all_software = Software.query.filter(Software.id.in_(min_ids)).order_by(Software.name, Software.version).all()
    return render_template('software/create.html', assets=assets, today=today, all_software=all_software)


@software.route('/<int:software_id>')
@login_required
@staff_required
def detail(software_id):
    sw     = Software.query.get_or_404(software_id)
    assets = Asset.query.order_by(Asset.name).all()
    today  = datetime.utcnow().date()
    return render_template('software/detail.html', sw=sw, assets=assets, today=today)


@software.route('/<int:software_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit(software_id):
    sw = Software.query.get_or_404(software_id)
    assets = Asset.query.order_by(Asset.name).all()
    installed_asset_ids = {inst.asset_id for inst in sw.installations}
    from sqlalchemy import func
    min_ids = db.session.query(func.min(Software.id)).group_by(Software.name, Software.version).scalar_subquery()
    all_software = Software.query.filter(Software.id.in_(min_ids)).order_by(Software.name, Software.version).all()

    if request.method == 'POST':
        sw.name          = request.form.get('name')
        sw.version       = request.form.get('version')
        sw.vendor        = request.form.get('vendor')
        sw.category      = request.form.get('category')
        sw.license_type  = request.form.get('license_type')
        sw.license_edition = request.form.get('license_edition') or None
        sw.license_key   = request.form.get('license_key') or None
        sw.license_seats = int(request.form.get('license_seats', 1))
        sw.license_expiry= request.form.get('license_expiry') or None
        sw.notes         = request.form.get('notes')

        selected_ids = set(int(i) for i in request.form.getlist('asset_ids'))

        # Add new installations
        for asset_id in selected_ids - installed_asset_ids:
            db.session.add(SoftwareInstallation(
                software_id     = sw.id,
                asset_id        = asset_id,
                installed_by_id = current_user.id
            ))
        # Remove unchecked installations
        for inst in sw.installations:
            if inst.asset_id not in selected_ids:
                db.session.delete(inst)

        db.session.commit()
        flash(f'Software "{sw.name}" updated successfully!', 'success')
        return redirect(url_for('software.list'))

    return render_template('software/edit.html', sw=sw, assets=assets, installed_asset_ids=installed_asset_ids, all_software=all_software)


@software.route('/<int:software_id>/delete', methods=['POST'])
@login_required
@staff_required
def delete(software_id):
    if not current_user.can_manage_inventory:
        flash('Access denied.', 'danger')
        return redirect(url_for('software.list'))
    sw = Software.query.get_or_404(software_id)
    db.session.delete(sw)
    db.session.commit()
    flash('Software deleted.', 'success')
    return redirect(url_for('software.list'))


@software.route('/<int:software_id>/install', methods=['POST'])
@login_required
@staff_required
def install(software_id):
    sw             = Software.query.get_or_404(software_id)
    asset_id       = request.form.get('asset_id')
    installed_date = request.form.get('installed_date') or None
    notes          = request.form.get('notes')

    if SoftwareInstallation.query.filter_by(software_id=sw.id, asset_id=asset_id).first():
        flash('Software already installed on this asset.', 'warning')
        return redirect(url_for('software.detail', software_id=sw.id))

    db.session.add(SoftwareInstallation(
        software_id    = sw.id,
        asset_id       = asset_id,
        installed_date = installed_date,
        installed_by_id= current_user.id,
        notes          = notes
    ))
    db.session.commit()
    flash('Software installed!', 'success')
    return redirect(url_for('software.detail', software_id=sw.id))


@software.route('/installation/<int:install_id>/remove', methods=['POST'])
@login_required
@staff_required
def uninstall(install_id):
    inst        = SoftwareInstallation.query.get_or_404(install_id)
    software_id = inst.software_id
    asset_name  = inst.asset.name
    db.session.delete(inst)
    db.session.commit()
    flash(f'Software removed from {asset_name}.', 'success')
    return redirect(request.referrer or url_for('software.list'))


@software.route('/by-user')
@login_required
@staff_required
def by_user():
    selected_user_id = request.args.get('user_id', '')
    all_users = User.query.order_by(User.name).all()
    selected_user = None
    asset_data = []

    if selected_user_id:
        selected_user = User.query.get(int(selected_user_id))
        if selected_user:
            for asset in selected_user.assets:
                installs = SoftwareInstallation.query.join(Software).filter(
                    SoftwareInstallation.asset_id == asset.id
                ).order_by(Software.name).all()
                asset_data.append({'asset': asset, 'installations': installs})

    return render_template('software/by_user.html',
        all_users        = all_users,
        selected_user    = selected_user,
        selected_user_id = selected_user_id,
        asset_data       = asset_data,
        all_software     = Software.query.order_by(Software.name).all(),
        today            = datetime.utcnow().date().strftime('%Y-%m-%d')
    )


# ── License category pages ──
LICENSE_FILTERS = {
    'windows':        {'label': 'Windows',        'icon': 'fa-windows',       'fab': True,  'keywords': ['windows 10', 'windows 11', 'windows 7', 'windows 8', 'windows xp', 'windows vista'], 'exclude': ['windows server']},
    'mssql':          {'label': 'MS SQL Server',   'icon': 'fa-database',      'fab': False, 'keywords': ['sql server', 'sql  2017', 'sql  2019']},
    'server':         {'label': 'Server OS',       'icon': 'fa-server',        'fab': False, 'keywords': ['windows server', 'ubuntu', 'centos', 'freebsd']},
    'visualstudio':   {'label': 'Visual Studio',   'icon': 'fa-code',          'fab': False, 'keywords': ['visual studio']},
    'msoffice':       {'label': 'MS Office',       'icon': 'fa-file-word',     'fab': False, 'keywords': ['microsoft office', 'ms project', 'ms visio', 'office 365']},
}

@software.route('/license/<string:slug>')
@login_required
@license_required
def license_page(slug):
    if slug not in LICENSE_FILTERS:
        flash('Unknown license category.', 'danger')
        return redirect(url_for('software.list'))

    cfg = LICENSE_FILTERS[slug]
    from sqlalchemy import or_, and_
    conditions = [Software.name.ilike(f'%{kw}%') for kw in cfg['keywords']]
    query = Software.query.filter(or_(*conditions))
    if cfg.get('exclude'):
        query = query.filter(and_(*[~Software.name.ilike(f'%{ex}%') for ex in cfg['exclude']]))
    # Deduplicate by keeping the lowest id per unique name+version
    from sqlalchemy import func
    min_ids = db.session.query(func.min(Software.id)).group_by(Software.name, Software.version).scalar_subquery()
    sw_list = query.filter(Software.id.in_(min_ids)).order_by(Software.name, Software.version).all()

    # For each software, collect all installations with user info
    rows = []
    for sw in sw_list:
        installs = (
            SoftwareInstallation.query
            .filter_by(software_id=sw.id)
            .join(Asset, SoftwareInstallation.asset_id == Asset.id)
            .order_by(Asset.hostname)
            .all()
        )
        rows.append({'sw': sw, 'installs': installs})

    return render_template('software/license_page.html',
        slug     = slug,
        cfg      = cfg,
        rows     = rows,
        sw_count = len(sw_list),
        inst_count = sum(len(r['installs']) for r in rows),
    )


@software.route('/by-user/<int:user_id>/install', methods=['POST'])
@login_required
@staff_required
def install_for_user(user_id):
    user           = User.query.get_or_404(user_id)
    asset_id       = request.form.get('asset_id')
    software_id    = request.form.get('software_id')
    installed_date = request.form.get('installed_date') or None

    if SoftwareInstallation.query.filter_by(software_id=software_id, asset_id=asset_id).first():
        flash('Software already installed on this asset.', 'warning')
        return redirect(url_for('software.by_user', user_id=user_id))

    db.session.add(SoftwareInstallation(
        software_id    = software_id,
        asset_id       = asset_id,
        installed_date = installed_date,
        installed_by_id= current_user.id
    ))
    db.session.commit()
    flash(f'Software installed for {user.name}!', 'success')
    return redirect(url_for('software.by_user', user_id=user_id))
