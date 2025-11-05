# /app/decorators.py

from functools import wraps
from flask import session, flash, redirect, url_for


def admin_required(f):
    """
    Decorator kiểm tra xem người dùng đã đăng nhập và có vai trò là 'admin' hay không.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Kiểm tra nếu chưa đăng nhập hoặc vai trò không phải admin
        if 'role' not in session or session.get('role') != 'admin':
            flash('Bạn không có quyền truy cập vào chức năng này!', 'danger')
            # Chuyển hướng về trang dashboard chính
            return redirect(url_for('attendance.dashboard'))
        # Nếu đúng là admin, cho phép thực thi hàm gốc
        return f(*args, **kwargs)
    return decorated_function


def login_required(f):
    """
    Decorator để đảm bảo người dùng đã đăng nhập.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Kiểm tra xem 'user_id' (hoặc 'username') có trong session không
        if 'user_id' not in session:
            flash('Vui lòng đăng nhập để truy cập trang này.', 'warning')
            return redirect(url_for('auth.login')) # Chuyển đến trang đăng nhập
        return f(*args, **kwargs)
    return decorated_function