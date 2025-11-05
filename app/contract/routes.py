# /app/contract/routes.py (File mới)

from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime, date
from ..models import db, User, Contract
from ..decorators import admin_required

contract_bp = Blueprint('contract', __name__, url_prefix='/admin/contract')

@contract_bp.route('/<int:user_id>')
@admin_required
def list_contracts(user_id):
    user = User.query.get_or_404(user_id)
    contracts = user.contracts  # Lấy danh sách hợp đồng
    today = date.today()

    # Xử lý trước dữ liệu để thêm trạng thái 'is_active'
    contracts_with_status = []
    for contract in contracts:
        # Luôn chuyển đổi ngày của hợp đồng về dạng date() để so sánh an toàn
        start_date = contract.start_date.date() if isinstance(contract.start_date, datetime) else contract.start_date
        end_date = contract.end_date.date() if isinstance(contract.end_date, datetime) else contract.end_date

        is_active = start_date <= today and (not end_date or end_date >= today)
        contracts_with_status.append({
            'contract': contract,
            'is_active': is_active
        })

    # Truyền danh sách đã xử lý vào template
    return render_template('contract/list.html', user=user, contracts_data=contracts_with_status)

@contract_bp.route('/add/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def add_contract(user_id):
    """Trang thêm hợp đồng mới cho nhân viên."""
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        pay_rate = request.form.get('pay_rate', type=float)
        pay_unit = request.form.get('pay_unit')
        start_date_str = request.form.get('start_date')
        
        if not all([pay_rate, pay_unit, start_date_str]):
            flash('Vui lòng điền đầy đủ thông tin.', 'danger')
            return render_template('contract/add.html', user=user)

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        
        new_contract = Contract(user_id=user.id, start_date=start_date, pay_rate=pay_rate, pay_unit=pay_unit)
        db.session.add(new_contract)
        db.session.commit()
        
        flash(f'Đã thêm hợp đồng mới cho {user.username}.', 'success')
        return redirect(url_for('contract.list_contracts', user_id=user.id))

    return render_template('contract/add.html', user=user)

@contract_bp.route('/edit/<int:contract_id>', methods=['GET', 'POST'])
@admin_required
def edit_contract(contract_id):
    contract_to_edit = Contract.query.get_or_404(contract_id)
    user = contract_to_edit.user

    if request.method == 'POST':
        pay_rate = request.form.get('pay_rate', type=float)
        pay_unit = request.form.get('pay_unit')
        start_date_str = request.form.get('start_date')

        # MỚI: Lấy end_date từ form
        end_date_str = request.form.get('end_date')

        if not all([pay_rate, pay_unit, start_date_str]):
            flash('Vui lòng điền đầy đủ thông tin bắt buộc.', 'danger')
            return render_template('contract/edit.html', user=user, contract=contract_to_edit)

        # Cập nhật các giá trị
        contract_to_edit.pay_rate = pay_rate
        contract_to_edit.pay_unit = pay_unit
        contract_to_edit.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

        # MỚI: Xử lý logic cho end_date
        if end_date_str:
            # Nếu người dùng nhập ngày kết thúc, chuyển đổi và lưu lại
            contract_to_edit.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            # Nếu người dùng để trống, lưu giá trị là None (vô thời hạn)
            contract_to_edit.end_date = None

        db.session.commit()

        flash(f'Đã cập nhật hợp đồng cho {user.username}.', 'success')
        return redirect(url_for('contract.list_contracts', user_id=user.id))

    return render_template('contract/edit.html', user=user, contract=contract_to_edit)
