import os
from flask import (Blueprint, render_template, request, redirect, url_for, 
                   session, flash, current_app)
from werkzeug.utils import secure_filename # Rất quan trọng cho file upload
from ..models import db, User
from ..decorators import login_required
from .. import bcrypt # Import bcrypt từ app/__init__.py của bạn

user_bp = Blueprint('user', __name__, url_prefix='/user')

# Định nghĩa các đuôi file ảnh cho phép
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get_or_404(session['user_id'])
    
    if request.method == 'POST':
        # --- 1. Xử lý dữ liệu văn bản ---
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.full_name = request.form.get('full_name')
        user.gender = request.form.get('gender')
        
        # --- 2. Xử lý Mật khẩu (Chỉ cập nhật nếu người dùng nhập) ---
        new_password = request.form.get('password')
        if new_password:
            # Mã hóa mật khẩu mới
            user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')

        # --- 3. Xử lý Upload Avatar ---
        if 'avatar' in request.files:
            file = request.files['avatar']
            
            # Nếu người dùng chọn file và file hợp lệ
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                
                # Lưu file
                # (Bạn cần định nghĩa 'UPLOAD_FOLDER' trong config của app)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Cập nhật CSDL
                user.avatar_image = filename

        # --- 4. Lưu tất cả thay đổi ---
        try:
            db.session.commit()
            session['avatar_image'] = user.avatar_image
            flash('Cập nhật thông tin thành công!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi! Tên tài khoản hoặc email có thể đã tồn tại. ({e})', 'danger')

        return redirect(url_for('user.profile'))

    # --- Yêu cầu GET (Hiển thị trang) ---
    return render_template('auth/profile.html', user=user)