from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models.asset import Asset
from app.models.user import User
from app.models.department import Department

assets = Blueprint('assets', __name__)

def staff_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.can_manage_inventory:
            flash('Access denied.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


def get_form_asset(form, asset=None):
    """Extract all asset fields from form."""
    data = dict(
        name               = form.get('name'),
        site_name          = form.get('site_name') or None,
        asset_tag          = form.get('asset_tag'),
        asset_type         = form.get('asset_type'),
        status             = form.get('status', 'available'),
        hostname           = form.get('hostname') or None,
        ip_address         = form.get('ip_address') or None,
        team_leader        = form.get('team_leader') or None,
        previous_users     = form.get('previous_users') or None,
        designation        = form.get('designation') or None,
        cpu_model          = form.get('cpu_model') or None,
        cpu_serial         = form.get('cpu_serial') or None,
        motherboard        = form.get('motherboard') or None,
        ssd_model          = form.get('ssd_model') or None,
        internal_hdd       = form.get('internal_hdd') or None,
        operating_system   = form.get('operating_system') or None,
        full_serial_number = form.get('full_serial_number') or None,
        ram_details        = form.get('ram_details') or None,
        ram_type           = form.get('ram_type') or None,
        monitor_model      = form.get('monitor_model') or None,
        mouse_model        = form.get('mouse_model') or None,
        keyboard_model     = form.get('keyboard_model') or None,
        remarks            = form.get('remarks') or None,
        brand              = form.get('brand') or None,
        model              = form.get('model') or None,
        serial_number      = form.get('serial_number') or None,
        purchase_date      = form.get('purchase_date') or None,
        warranty_expiry    = form.get('warranty_expiry') or None,
        notes              = form.get('notes') or None,
        department_id      = form.get('department_id') or None,
        assigned_user_id   = form.get('assigned_user_id') or None,
    )
    if asset:
        for k, v in data.items():
            setattr(asset, k, v)
    return data


@assets.route('/')
@login_required
@staff_required
def list():
    page       = request.args.get('page', 1, type=int)
    asset_type = request.args.get('type', '')
    status     = request.args.get('status', '')
    search     = request.args.get('search', '')

    query = Asset.query
    if asset_type:
        query = query.filter_by(asset_type=asset_type)
    if status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(Asset.name.ilike(f'%{search}%') | Asset.hostname.ilike(f'%{search}%') | Asset.ip_address.ilike(f'%{search}%'))

    assets_list = query.order_by(Asset.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('assets/list.html', assets=assets_list, asset_type=asset_type, status=status, search=search)


@assets.route('/create', methods=['GET', 'POST'])
@login_required
@staff_required
def create():
    departments = Department.query.order_by(Department.name).all()
    users       = User.query.filter_by(_is_active=True).order_by(User.name).all()
    if request.method == 'POST':
        asset = Asset(**get_form_asset(request.form))
        db.session.add(asset)
        db.session.commit()
        flash('Asset added successfully!', 'success')
        return redirect(url_for('assets.detail', asset_id=asset.id))
    return render_template('assets/create.html', departments=departments, users=users)


@assets.route('/<int:asset_id>')
@login_required
@staff_required
def detail(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    return render_template('assets/detail.html', asset=asset)


@assets.route('/<int:asset_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit(asset_id):
    asset       = Asset.query.get_or_404(asset_id)
    departments = Department.query.order_by(Department.name).all()
    users       = User.query.filter_by(_is_active=True).order_by(User.name).all()
    if request.method == 'POST':
        get_form_asset(request.form, asset)
        db.session.commit()
        flash('Asset updated!', 'success')
        return redirect(url_for('assets.detail', asset_id=asset.id))
    return render_template('assets/edit.html', asset=asset, departments=departments, users=users)


@assets.route('/<int:asset_id>/delete', methods=['POST'])
@login_required
def delete(asset_id):
    if not current_user.can_manage_inventory:
        flash('Access denied.', 'danger')
        return redirect(url_for('assets.list'))
    asset = Asset.query.get_or_404(asset_id)
    db.session.delete(asset)
    db.session.commit()
    flash('Asset deleted.', 'success')
    return redirect(url_for('assets.list'))
