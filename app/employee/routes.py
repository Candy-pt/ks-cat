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
    """
    Trang thêm người dùng mới (Nhân viên hoặc Admin).
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # CHỈNH SỬA 1: Đọc giá trị 'role' từ form
        role = request.form.get('role')
        
        # Kiểm tra username đã tồn tại chưa
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash(f'Tên đăng nhập "{username}" đã tồn tại. Vui lòng chọn tên khác.', 'danger')
            # Lưu ý: render lại template 'employee/add_employee.html'
            return render_template('employee/add_employee.html')

        if not password:
            flash('Mật khẩu không được để trống!', 'danger')
            return render_template('employee/add_employee.html')

        # CHỈNH SỬA 2: Thêm một bước kiểm tra vai trò hợp lệ
        if role not in ['employee', 'admin']:
            flash(f'Vai trò "{role}" không hợp lệ.', 'danger')
            return render_template('employee/add_employee.html')

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # CHỈNH SỬA 3: Sử dụng biến 'role' thay vì code cứng 'employee'
        new_user = User(username=username, password=hashed_pw, role=role)
        
        db.session.add(new_user)
        db.session.commit()
        
        # CHỈNH SỬA 4: Cập nhật thông báo flash cho rõ ràng
        flash(f'Tạo tài khoản "{username}" (vai trò: {role}) thành công!', 'success')
        
        # Nếu là nhân viên, chuyển qua trang tạo hợp đồng
        if new_user.role == 'employee':
            return redirect(url_for('contract.add_contract', user_id=new_user.id))
        
        # Nếu là admin, quay về dashboard (hoặc trang quản lý user)
        return redirect(url_for('attendance.dashboard'))
        
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
        
        # (Chưa có chức năng sửa vai trò ở đây, xem ghi chú)
        
        db.session.commit()
        flash(f'Cập nhật thông tin cho "{user_to_edit.username}" thành công!', 'success')
        return redirect(url_for('attendance.dashboard'))
        
    return render_template('employee/edit_employee.html', user=user_to_edit)

@employee_bp.route('/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_employee(user_id):
    """Xử lý xóa nhân viên."""
    user_to_delete = User.query.get_or_404(user_id)
    
    # Biện pháp an toàn, không cho xóa admin (Rất tốt!)
    if user_to_delete.role == 'admin':
        flash('Không thể xóa tài khoản Admin!', 'danger')
        # Chuyển hướng về trang dashboard (admin_panel có thể chưa tồn tại)
        return redirect(url_for('attendance.dashboard'))
    
    username = user_to_delete.username
    
    # Xóa tất cả các bản ghi liên quan trước khi xóa người dùng
    Attendance.query.filter_by(user_id=user_id).delete()
    Contract.query.filter_by(user_id=user_id).delete() 
    Payroll.query.filter_by(user_id=user_id).delete() 
    
    db.session.delete(user_to_delete)
    db.session.commit()
    
    flash(f'Đã xóa thành công nhân viên "{username}" và tất cả dữ liệu liên quan.', 'success')
    return redirect(url_for('attendance.dashboard'))