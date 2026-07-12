from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models.department import Department
from app.utils.departments import STANDARD_DEPARTMENTS, standard_department_map

departments = Blueprint('departments', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.can_manage_system:
            flash('System owner access required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


@departments.route('/')
@login_required
@admin_required
def list():
    all_departments = Department.query.order_by(Department.name).all()
    return render_template(
        'departments/list.html',
        departments=all_departments,
        standard_departments=standard_department_map(),
    )


@departments.route('/standardize', methods=['POST'])
@login_required
@admin_required
def standardize():
    existing = {department.name.strip().lower(): department for department in Department.query.all()}
    created = 0
    updated = 0
    for item in STANDARD_DEPARTMENTS:
        aliases = [alias.lower() for alias in item['aliases']]
        department = existing.get(item['name'].lower())
        if not department:
            department = next((existing.get(alias) for alias in aliases if existing.get(alias)), None)
        if not department:
            department = Department(name=item['name'])
            db.session.add(department)
            existing[item['name'].lower()] = department
            created += 1
        department.name = item['name']
        department.description = item['description']
        department.location = item['location']
        updated += 1
    db.session.commit()
    flash(f'Departments standardized. Created {created}, updated {updated}.', 'success')
    return redirect(url_for('departments.list'))


@departments.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    if request.method == 'POST':
        dept = Department(
            name=request.form.get('name', '').strip(),
            description=request.form.get('description', '').strip() or None,
            location=request.form.get('location', '').strip() or None
        )
        if not dept.name:
            flash('Department name is required.', 'danger')
            return render_template('departments/create.html')
        db.session.add(dept)
        db.session.commit()
        flash('Department created!', 'success')
        return redirect(url_for('departments.list'))
    return render_template('departments/create.html')


@departments.route('/<int:dept_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(dept_id):
    dept = Department.query.get_or_404(dept_id)
    if request.method == 'POST':
        dept.name = request.form.get('name', '').strip()
        dept.description = request.form.get('description', '').strip() or None
        dept.location = request.form.get('location', '').strip() or None
        if not dept.name:
            flash('Department name is required.', 'danger')
            return render_template('departments/edit.html', dept=dept)
        db.session.commit()
        flash('Department updated!', 'success')
        return redirect(url_for('departments.list'))
    return render_template('departments/edit.html', dept=dept)


@departments.route('/<int:dept_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(dept_id):
    dept = Department.query.get_or_404(dept_id)
    if dept.users or dept.assets:
        flash('Department has linked users or assets. Edit it instead of deleting.', 'danger')
        return redirect(url_for('departments.list'))
    db.session.delete(dept)
    db.session.commit()
    flash('Department deleted.', 'success')
    return redirect(url_for('departments.list'))
