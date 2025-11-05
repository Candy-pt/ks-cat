# /app/attendance/routes.py

import os
import time
from datetime import datetime
from functools import wraps
import pytz
from ..decorators import admin_required 
from flask import (Blueprint, render_template, redirect, url_for, session, 
                   request, flash, current_app)
from werkzeug.utils import secure_filename
from .. import bcrypt 
from ..models import *


def generate_qr_token(user_id):
    """Hàm giả lập tạo token QR, bạn sẽ thay thế bằng logic thực tế của mình."""
    secret = current_app.config.get('SECRET_KEY', 'default-secret')
    # Ví dụ một token đơn giản, bạn nên dùng thư viện JWT hoặc ItsDangerous cho an toàn
    token_base = f"{user_id}-{secret}-{int(time.time())}"
    return token_base[:16] 

# KHỞI TẠO BLUEPRINT
attendance_bp = Blueprint('attendance', __name__)

# CÁC ROUTE CHO NGƯỜI DÙNG THÔNG THƯỜNG
@attendance_bp.route('/')
def index():
    """Route gốc, chuyển hướng dựa trên trạng thái đăng nhập."""
    if 'user_id' in session:
        return redirect(url_for('attendance.dashboard'))
    return redirect(url_for('auth.login'))

@attendance_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    today = datetime.now(vn_tz).date()

    if session.get('role') == 'admin':
        users = User.query.filter(User.role != 'admin').all()
        total_employees = len(users)
        
        # 1. Tỷ lệ điểm danh hôm nay 
        attendance_rate = 0
        if total_employees > 0:
            employees_checked_in_today = Attendance.query.filter(
                Attendance.date == today,
                Attendance.check_in != None,
                Attendance.user_id.in_([user.id for user in users]) 
            ).count()
            attendance_rate = round((employees_checked_in_today / total_employees) * 100)

        # 2. Tổng lương tháng hiện tại 
        current_month = today.month
        current_year = today.year
        total_salary = db.session.query(db.func.sum(Payroll.net_salary)).filter(
            Payroll.month == current_month,
            Payroll.year == current_year
        ).scalar() or 0
        formatted_total_salary = f"{total_salary:,.0f}"

        # 3. Lấy đơn xin nghỉ (Giữ nguyên)
        pending_leaves = db.session.query(
            LeaveRequest, User.username
        ).join(
            User, LeaveRequest.user_id == User.id
        ).filter(
            LeaveRequest.status == 'pending'
        ).order_by(LeaveRequest.start_date.asc()).all()

        admin_user_id = session['user_id']
        
        admin_attendance_today = Attendance.query.filter_by(user_id=admin_user_id, 
                                                            date=today).first()

        # 5. Gửi tất cả dữ liệu đến template
        return render_template(
            'attendance/admin_dashboard.html', 
            users=users, 
            attendance_rate=attendance_rate,
            total_salary=formatted_total_salary,
            attendance=admin_attendance_today,  
            pending_leaves=pending_leaves     
        )

  
    else:
        user_id = session['user_id']
        
        # 1. Lấy bản ghi chấm công HÔM NAY (giống code cũ)
        attendance_today = Attendance.query.filter_by(user_id=user_id, date=today).first()
        
        # 2. LẤY THÊM: 7 ngày chấm công gần nhất
        recent_attendances = Attendance.query.filter(
            Attendance.user_id == user_id,
            Attendance.date <= today # Lấy từ hôm nay trở về trước
        ).order_by(
            Attendance.date.desc() # Sắp xếp: Mới nhất lên đầu
        ).limit(7).all() # Giới hạn 7 bản ghi
        
        # 3. Gửi CẢ HAI biến vào template
        return render_template(
            'employee/employee_dashboard.html', 
            attendance=attendance_today,     # Dùng cho thẻ check-in
            attendances=recent_attendances   # Dùng cho bảng lịch sử
        )


@attendance_bp.route('/check_in', methods=['POST'])
def check_in():
    """
    Xử lý check-in thủ công (Đã nâng cấp)
    - CHỈ cho phép check-in nếu không có ca làm nào khác đang mở.
    - Sửa lỗi 'date' (đã làm ở bước trước).
    """
    user_id = session['user_id']
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    check_time = datetime.now(vn_tz)
    today = check_time.date()
    
    # --- BƯỚC 1: KIỂM TRA CA LÀM "TREO" ---
    # Tìm xem có bất kỳ ca làm nào (bất kể ngày nào) chưa check-out không
    last_open_shift = Attendance.query.filter_by(
        user_id=user_id,
        check_out=None
    ).first()

    if last_open_shift:
        # Nếu có -> BÁO LỖI. Người dùng phải check-out ca cũ trước.
        flash(f"Lỗi: Bạn chưa check-out cho ca làm bắt đầu lúc {last_open_shift.check_in.astimezone(vn_tz).strftime('%H:%M ngày %d/%m')}. Vui lòng check-out trước!", 'danger')
        return redirect(url_for('attendance.dashboard'))

    # --- BƯỚC 2: TẠO CHECK-IN MỚI (Đã sửa lỗi) ---
    # (Nếu không có ca nào treo, chúng ta mới tạo ca mới)
    # Phần 'existing' này chỉ để đề phòng (về lý thuyết, Bước 1 đã bao gồm)
    existing_today = Attendance.query.filter_by(user_id=user_id, date=today).first()
    
    if existing_today and existing_today.check_in:
         flash('Bạn đã check-in hôm nay rồi (logic dự phòng).', 'warning')
         return redirect(url_for('attendance.dashboard'))
         
    # Tạo bản ghi mới VỚI NGÀY HÔM NAY
    attendance = Attendance(
        user_id=user_id, 
        check_in=check_time, 
        date=today  # <-- Dòng fix quan trọng từ lần trước
    )
    db.session.add(attendance)
    db.session.commit()
    flash(f'Check-in thành công lúc {check_time.strftime("%H:%M:%S")}', 'success')
        
    return redirect(url_for('attendance.dashboard'))


@attendance_bp.route('/check_out', methods=['POST'])
def check_out():
    """
    Xử lý check-out thủ công (Đã nâng cấp)
    - Sẽ tìm ca làm GẦN NHẤT chưa check-out và đóng nó lại.
    """
    user_id = session['user_id']
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    check_time = datetime.now(vn_tz)
    
    # --- BƯỚC 1: TÌM CA LÀM "TREO" GẦN NHẤT ---
    # (Sắp xếp theo check_in giảm dần để lấy ca mới nhất)
    attendance_to_close = Attendance.query.filter_by(
        user_id=user_id,
        check_out=None
    ).order_by(Attendance.check_in.desc()).first()

    # --- BƯỚC 2: XỬ LÝ ---
    if attendance_to_close:
        # NẾU TÌM THẤY -> Cập nhật check-out cho bản ghi đó
        attendance_to_close.check_out = check_time
        db.session.commit()
        
        flash(f'Check-out thành công lúc {check_time.strftime("%H:%M:%S")}', 'success')
        
        # (Logic tùy chọn: kiểm tra xem ca làm có quá dài không, 
        #  ví dụ: 20 tiếng, và cảnh báo nếu có)
        
    else:
        # NẾU KHÔNG TÌM THẤY (họ chưa check-in, hoặc đã check-out rồi)
        flash('Bạn chưa check-in (hoặc đã check-out rồi)!', 'warning')
            
    return redirect(url_for('attendance.dashboard'))

@attendance_bp.route('/history')
def history():
    """Trang xem lịch sử chấm công của cá nhân."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    attendances = Attendance.query.filter_by(user_id=session['user_id']).order_by(Attendance.date.desc()).all()
    return render_template('attendance/history.html', attendances=attendances)

@attendance_bp.route('/qr_scan', methods=['GET', 'POST'])
def qr_scan():
    """Trang quét và xử lý chấm công bằng QR code."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        # ... Toàn bộ logic xử lý QR code, GPS, và ảnh của bạn ...
        # Ví dụ:
        # qr_code = request.form.get('qr_code')
        # if not qr_code or not qr_code.startswith('OFFICE_QR_'):
        #     flash('Mã QR không hợp lệ!', 'danger')
        #     return render_template('qr_scan.html')
        
        # ... các bước xác thực khác ...

        # Lưu ảnh
        # image_file = request.files.get('image')
        # filename = secure_filename(f"{session['user_id']}_{datetime.now().strftime('%Y%m%d')}.jpg")
        # image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        # image_file.save(image_path)
        
        flash('Check-in bằng QR thành công!', 'success')
        return redirect(url_for('attendance.dashboard'))
    
    return render_template('attendance/qr_scan.html')


@attendance_bp.route('/all_history')
def all_history():
    """Trang xem toàn bộ lịch sử chấm công (chỉ admin) - CÓ PHÂN TRANG."""
    
    page = request.args.get('page', 1, type=int)
    RECORDS_PER_PAGE = 12

    attendances_query = db.session.query(
        Attendance, User.username
    ).join(User, Attendance.user_id == User.id).order_by(Attendance.date.desc(), User.username)
    
    pagination = attendances_query.paginate(
        page=page, 
        per_page=RECORDS_PER_PAGE, 
        error_out=False
    )
    
    attendances_on_page = pagination.items
    
    # 2. === THÊM DÒNG NÀY ===
    # Định nghĩa múi giờ
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

    # 3. Gửi vn_tz vào template
    return render_template(
        'attendance/all_history.html', 
        attendances_with_users=attendances_on_page,
        pagination=pagination,
        vn_tz=vn_tz  # === THÊM BIẾN NÀY ===
    )




@attendance_bp.route('/edit_attendance/<int:att_id>', methods=['GET', 'POST'])
def edit_attendance(att_id):
    """Trang chỉnh sửa một lượt chấm công (chỉ admin)."""
    attendance = Attendance.query.get_or_404(att_id)
    user = User.query.get(attendance.user_id)

    if request.method == 'POST':
        check_in_str = request.form.get('check_in')
        check_out_str = request.form.get('check_out')
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        
        try:
            if check_in_str:
                attendance.check_in = vn_tz.localize(datetime.fromisoformat(check_in_str))
                attendance.date = attendance.check_in.date()
            else:
                attendance.check_in = None

            if check_out_str:
                attendance.check_out = vn_tz.localize(datetime.fromisoformat(check_out_str))
            else:
                attendance.check_out = None
            
            db.session.commit()
            flash('Cập nhật chấm công thành công!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: định dạng thời gian không hợp lệ. Vui lòng dùng YYYY-MM-DDTHH:MM. Lỗi chi tiết: {e}', 'danger')
            
        return redirect(url_for('attendance.all_history'))
    
    # Truyền cả attendance và user vào template để hiển thị tên
    return render_template('attendance/edit_attendance.html', attendance=attendance, user=user)