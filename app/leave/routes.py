# /app/leave/routes.py

from flask import (Blueprint, render_template, request, redirect, url_for, 
                   session, flash)
from datetime import datetime, date, time 
# SỬA: Import thêm các model và decorator cần thiết
from ..models import db, User, LeaveRequest, Notification
from ..decorators import admin_required, login_required # Đảm bảo bạn đã có login_required

leave_bp = Blueprint('leave', __name__, url_prefix='/leave')

# --- HÀM MỚI 1: Trang cho nhân viên xem đơn của mình ---
@leave_bp.route('/my_requests')
@login_required
def my_requests():
    """Trang cho nhân viên xem lịch sử đơn từ của họ."""
    user_id = session['user_id']
    
    # Lấy tất cả đơn từ của user này, sắp xếp mới nhất lên đầu
    requests = LeaveRequest.query.filter_by(user_id=user_id).order_by(LeaveRequest.id.desc()).all()
    
    return render_template('leave/my_requests.html', requests=requests)

# --- HÀM MỚI 2: Trang cho admin quản lý tất cả đơn từ ---
@leave_bp.route('/manage')
@admin_required
def manage_requests():
    """Trang cho admin xem, lọc, và xử lý tất cả đơn từ."""
    
    # Lấy bộ lọc trạng thái từ URL (ví dụ: /manage?status=pending)
    # Mặc định là 'pending' để admin thấy việc cần làm ngay
    status_filter = request.args.get('status', 'pending')

    query = LeaveRequest.query.join(User).order_by(LeaveRequest.id.desc())
    
    if status_filter != 'all':
        query = query.filter(LeaveRequest.status == status_filter)
        
    all_requests = query.all()
    
    return render_template('leave/manage_requests.html', 
                           requests=all_requests, 
                           current_status=status_filter)

# --- Code cũ của bạn (Giữ nguyên) ---

@leave_bp.route('/request', methods=['POST']) 
@login_required
def request_leave():
    """Xử lý đơn từ (nghỉ phép, đi trễ,về sớm, đổi ca)."""
    
    request_type = request.form.get('request_type')
    reason = request.form.get('reason')
    user_id = session['user_id']
    
    start_date = None
    end_date = None
    request_date = None
    request_time = None

    # --- Lấy dữ liệu theo loại đơn ---
    if request_type == 'leave':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        if not all([start_date_str, end_date_str, reason]):
            flash('Vui lòng điền đủ ngày bắt đầu, kết thúc và lý do.', 'danger')
            return redirect(url_for('attendance.dashboard'))
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        if end_date < start_date:
            flash('Ngày kết thúc không thể trước ngày bắt đầu.', 'danger')
            return redirect(url_for('attendance.dashboard'))

    elif request_type in ['late', 'early']:
        request_date_str = request.form.get('request_date')
        request_time_str = request.form.get('request_time') # Có thể rỗng
        if not all([request_date_str, reason]):
            flash('Vui lòng điền đủ ngày áp dụng và lý do.', 'danger')
            return redirect(url_for('attendance.dashboard'))
        request_date = datetime.strptime(request_date_str, '%Y-%m-%d').date()
        if request_time_str:
             try:
                 request_time = datetime.strptime(request_time_str, '%H:%M').time()
             except ValueError:
                 flash('Định dạng giờ không hợp lệ (HH:MM).', 'danger')
                 return redirect(url_for('attendance.dashboard'))

    elif request_type == 'shift_change':
        if not reason: # Chỉ cần lý do/chi tiết
            flash('Vui lòng điền chi tiết đổi ca.', 'danger')
            return redirect(url_for('attendance.dashboard'))
    
    else: # Loại không hợp lệ
        flash('Loại yêu cầu không hợp lệ.', 'danger')
        return redirect(url_for('attendance.dashboard'))

    # --- Tạo bản ghi LeaveRequest ---
    # (Giả sử model của bạn đã có cột 'request_type')
    new_request = LeaveRequest(
        user_id=user_id,
        request_type=request_type,
        start_date=start_date,
        end_date=end_date,
        request_date=request_date,
        request_time=request_time,
        reason=reason,
        status='pending'
    )
    
    db.session.add(new_request)
    db.session.commit()
    
    flash('Đã gửi yêu cầu thành công. Vui lòng chờ duyệt.', 'success')
    return redirect(url_for('attendance.dashboard')) 


@leave_bp.route('/process/<int:request_id>', methods=['POST'])
@admin_required
def process_request(request_id):
    """Route (chỉ admin) dùng để duyệt hoặc từ chối đơn."""
    
    leave_request = LeaveRequest.query.get_or_404(request_id)
    action = request.form.get('action') 

    if action in ['approved', 'rejected']:
        leave_request.status = action
        
        # --- Cập nhật thông báo ---
        type_vn = {
            'leave': 'nghỉ phép',
            'late': 'đi trễ',
            'early': 'về sớm',
            'shift_change': 'đổi ca'
        }.get(leave_request.request_type, 'yêu cầu')

        # (Giả sử bạn có property 'relevant_date' trong model)
        relevant_date_str = ""
        if leave_request.relevant_date: 
             relevant_date_str = f"(ngày {leave_request.relevant_date.strftime('%d/%m')})"

        status_vn = "ĐƯỢC DUYỆT" if action == 'approved' else "BỊ TỪ CHỐI"
        
        message = f"Đơn xin {type_vn} {relevant_date_str} của bạn đã được {status_vn}."
        
        new_notif = Notification(
            user_id=leave_request.user_id,
            message=message,
            leave_request_id=leave_request.id 
        )
        db.session.add(new_notif)
        
        db.session.commit()
        flash(f'Đã {status_vn} đơn {type_vn}.', 'success')
    else:
        flash('Hành động không hợp lệ.', 'danger')
    
    # SỬA: Chuyển hướng về trang quản lý
    return redirect(url_for('leave.manage_requests', status='pending'))