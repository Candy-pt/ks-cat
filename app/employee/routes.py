# /app/employee/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from functools import wraps
from ..decorators import admin_required 
from .. import bcrypt
import pytz
from ..models import db, User, Attendance, Contract, Payroll

# Decorator kiểm tra quyền Admin
# để có thể tái sử dụng ở nhiều nơi mà không cần định nghĩa lại.

# KHỞI TẠO BLUEPRINT
employee_bp = Blueprint('employee', __name__, url_prefix='/admin')


@employee_bp.route('/add', methods=['GET', 'POST'])
@admin_required
def add_employee():
    """Trang thêm nhân viên mới."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Kiểm tra username đã tồn tại chưa
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash(f'Tên đăng nhập "{username}" đã tồn tại. Vui lòng chọn tên khác.', 'danger')
            return render_template('add_employee.html')

        if not password:
            flash('Mật khẩu không được để trống!', 'danger')
            return render_template('employee/add_employee.html')

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password=hashed_pw, role='employee')
        
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'Thêm nhân viên "{username}" thành công! Tiếp theo, hãy tạo hợp đồng cho họ.', 'success')
        return redirect(url_for('contract.add_contract', user_id=new_user.id))
        
    return render_template('employee/add_employee.html')

@employee_bp.route('/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_employee(user_id):
    """Trang chỉnh sửa thông tin nhân viên."""
    user_to_edit = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user_to_edit.username = request.form.get('username')
        
        # Chỉ cập nhật mật khẩu nếu người dùng nhập mật khẩu mới
        new_password = request.form.get('password')
        if new_password:
            user_to_edit.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        db.session.commit()
        flash(f'Cập nhật thông tin cho nhân viên "{user_to_edit.username}" thành công!', 'success')
        return redirect(url_for('attendance.dashboard'))
        
    return render_template('employee/edit_employee.html', user=user_to_edit)

@employee_bp.route('/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_employee(user_id):
    """Xử lý xóa nhân viên."""
    user_to_delete = User.query.get_or_404(user_id)
    
    # Biện pháp an toàn, không cho xóa admin
    if user_to_delete.role == 'admin':
        flash('Không thể xóa tài khoản Admin!', 'danger')
        return redirect(url_for('employee.admin_panel'))
    
    username = user_to_delete.username
    
    # Xóa tất cả các bản ghi liên quan trước khi xóa người dùng
    Attendance.query.filter_by(user_id=user_id).delete()
    Contract.query.filter_by(user_id=user_id).delete() 
    Payroll.query.filter_by(user_id=user_id).delete() 
    
    db.session.delete(user_to_delete)
    db.session.commit()
    
    flash(f'Đã xóa thành công nhân viên "{username}" và tất cả dữ liệu liên quan.', 'success')
    return redirect(url_for('attendance.dashboard'))

