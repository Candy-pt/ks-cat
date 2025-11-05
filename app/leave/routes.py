#app/leave/routes.py
""" Quản lý đơn từ: 
        đơn xin nghỉ phép
        đơn xin đi trễ 
        đơn xin về sớm
        đơn xin đổi ca """


from flask import (Blueprint, render_template, request, redirect, url_for, 
                   session, flash)
# Thêm date, time
from datetime import datetime, date, time 
# Thêm Notification
from ..models import db, User, LeaveRequest, Notification
from ..decorators import admin_required, login_required

leave_bp = Blueprint('leave', __name__, url_prefix='/leave')


@leave_bp.route('/request', methods=['POST']) # Chỉ xử lý POST từ modal
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
@admin_required # Đảm bảo decorator này đúng
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
        }.get(leave_request.request_type, 'yêu cầu') # Lấy tên tiếng Việt

        # Xác định ngày liên quan để hiển thị
        relevant_date_str = ""
        if leave_request.relevant_date: # Dùng property đã tạo
             relevant_date_str = f"(ngày {leave_request.relevant_date.strftime('%d/%m')})"

        status_vn = "DUYỆT" if action == 'approved' else "TỪ CHỐI"
        
        message = f"Đơn xin {type_vn} {relevant_date_str} của bạn đã được {status_vn}."
        
        new_notif = Notification(
            user_id=leave_request.user_id,
            message=message,
            leave_request_id=leave_request.id 
        )
        db.session.add(new_notif)
        
        db.session.commit()
        flash(f'Đã {action} đơn {type_vn}.', 'success')
    else:
        flash('Hành động không hợp lệ.', 'danger')

    return redirect(url_for('attendance.dashboard'))