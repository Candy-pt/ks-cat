# /app/attendance/routes.py

import os
import time
from datetime import datetime, timedelta
from functools import wraps
import pytz
from ..decorators import admin_required
from flask import (Blueprint, render_template, redirect, url_for, session,
                   request, flash, current_app)
from werkzeug.utils import secure_filename
from .. import bcrypt
from ..models import *

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

        # === THÊM DỮ LIỆU CHO BIỂU ĐỒ ===

        # 1. Biểu đồ xu hướng tỷ lệ điểm danh theo tháng (6 tháng gần nhất)
        attendance_trend = []
        for i in range(5, -1, -1):  # Từ 5 tháng trước đến tháng hiện tại
            month_date = today.replace(day=1) - timedelta(days=i*30)
            month_start = month_date.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            total_days = (month_end - month_start).days + 1
            working_days = sum(1 for d in range(total_days) if (month_start + timedelta(days=d)).weekday() < 5)

            if working_days > 0:
                checked_in_days = db.session.query(db.func.count(db.func.distinct(Attendance.date))).filter(
                    Attendance.date.between(month_start, month_end),
                    Attendance.check_in.isnot(None),
                    Attendance.user_id.in_([u.id for u in users])
                ).scalar() or 0

                rate = round((checked_in_days / working_days) * 100, 1)
                attendance_trend.append({
                    'month': month_date.strftime('%m/%Y'),
                    'rate': rate
                })

        # 2. Biểu đồ phân bố trạng thái điểm danh hôm nay
        checked_in_today = Attendance.query.filter(
            Attendance.date == today,
            Attendance.check_in.isnot(None),
            Attendance.user_id.in_([u.id for u in users])
        ).count()

        checked_out_today = Attendance.query.filter(
            Attendance.date == today,
            Attendance.check_in.isnot(None),
            Attendance.check_out.isnot(None),
            Attendance.user_id.in_([u.id for u in users])
        ).count()

        not_checked_in = total_employees - checked_in_today
        still_working = checked_in_today - checked_out_today

        attendance_status = {
            'checked_in': checked_in_today,
            'still_working': still_working,
            'not_checked_in': not_checked_in
        }

        # 5. Biểu đồ trạng thái đơn xin nghỉ
        leave_status = {
            'pending': LeaveRequest.query.filter_by(status='pending').count(),
            'approved': LeaveRequest.query.filter_by(status='approved').count(),
            'rejected': LeaveRequest.query.filter_by(status='rejected').count()
        }

        # 6. Biểu đồ phân bố giờ làm việc (histogram)
        current_month_start = today.replace(day=1)
        current_month_end = (current_month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        work_hours_data = []
        for user in users:
            attendances = Attendance.query.filter(
                Attendance.user_id == user.id,
                Attendance.date.between(current_month_start, current_month_end),
                Attendance.check_in.isnot(None),
                Attendance.check_out.isnot(None)
            ).all()

            total_hours = sum(
                (att.check_out - att.check_in).total_seconds() / 3600
                for att in attendances
            )
            if total_hours > 0:
                work_hours_data.append(round(total_hours, 1))

        # Tạo bins cho histogram (nhóm giờ làm việc)
        hours_bins = {'0-20': 0, '20-40': 0, '40-60': 0, '60-80': 0, '80-100': 0, '100+': 0}
        for hours in work_hours_data:
            if hours < 20:
                hours_bins['0-20'] += 1
            elif hours < 40:
                hours_bins['20-40'] += 1
            elif hours < 60:
                hours_bins['40-60'] += 1
            elif hours < 80:
                hours_bins['60-80'] += 1
            elif hours < 100:
                hours_bins['80-100'] += 1
            else:
                hours_bins['100+'] += 1

        # === THÊM DỮ LIỆU CHO 3 BIỂU ĐỒ MỚI ===

        # 7. Biểu đồ phân bố lương (histogram lương)
        salary_bins = {'0-5M': 0, '5-10M': 0, '10-15M': 0, '15-20M': 0, '20M+': 0}
        for user in users:
            contract = Contract.query.filter(
                Contract.user_id == user.id,
                Contract.start_date <= today
            ).order_by(Contract.start_date.desc()).first()
            if contract and contract.pay_unit == 'month':
                salary = contract.pay_rate
                if salary < 5000000:
                    salary_bins['0-5M'] += 1
                elif salary < 10000000:
                    salary_bins['5-10M'] += 1
                elif salary < 15000000:
                    salary_bins['10-15M'] += 1
                elif salary < 20000000:
                    salary_bins['15-20M'] += 1
                else:
                    salary_bins['20M+'] += 1

        # 8. Biểu đồ đơn xin nghỉ theo loại
        leave_types = {
            'leave': LeaveRequest.query.filter_by(request_type='leave').count(),
            'late': LeaveRequest.query.filter_by(request_type='late').count(),
            'early': LeaveRequest.query.filter_by(request_type='early').count(),
            'shift_change': LeaveRequest.query.filter_by(request_type='shift_change').count()
        }

        # 9. Biểu đồ hiệu suất làm việc (số ngày làm việc trung bình theo tháng)
        performance_trend = []
        for i in range(5, -1, -1):  # 6 tháng gần nhất
            month_date = today.replace(day=1) - timedelta(days=i*30)
            month_start = month_date.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            total_working_days = 0
            for user in users:
                user_days = Attendance.query.filter(
                    Attendance.user_id == user.id,
                    Attendance.date.between(month_start, month_end),
                    Attendance.check_in.isnot(None)
                ).count()
                total_working_days += user_days

            avg_days = round(total_working_days / len(users), 1) if users else 0
            performance_trend.append({
                'month': month_date.strftime('%m/%Y'),
                'avg_days': avg_days
            })

        # 5. Gửi tất cả dữ liệu đến template
        return render_template(
            'attendance/admin_dashboard.html',
            users=users,
            attendance_rate=attendance_rate,
            total_salary=formatted_total_salary,
            attendance=admin_attendance_today,
            pending_leaves=pending_leaves,
            attendance_trend=attendance_trend,
            attendance_status=attendance_status,
            leave_status=leave_status,
            hours_bins=hours_bins,
            salary_bins=salary_bins,
            leave_types=leave_types,
            performance_trend=performance_trend
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
    Xử lý check-in thủ công (Đã nâng cấp với tính năng ca làm việc)
    - CHỈ cho phép check-in nếu không có ca làm nào khác đang mở.
    - Tích hợp với lịch làm việc để tự động gán schedule_id và tính toán thời gian trễ.
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

    # --- BƯỚC 2: TÌM LỊCH LÀM VIỆC HÔM NAY ---
    # Tìm schedule của user cho ngày hôm nay
    schedule_today = Schedule.query.filter_by(user_id=user_id, date=today).first()
    schedule_id = schedule_today.id if schedule_today else None

    # --- BƯỚC 3: TÍNH TOÁN THỜI GIAN TRỄ (NẾU CÓ SCHEDULE) ---
    late_minutes = 0
    if schedule_today:
        # Lấy thời gian bắt đầu của ca làm việc
        shift_start_time = schedule_today.shift.start_time
        # Tạo datetime object cho thời gian bắt đầu ca làm
        shift_start_datetime = datetime.combine(today, shift_start_time).replace(tzinfo=vn_tz)

        # Tính số phút trễ
        if check_time > shift_start_datetime:
            late_minutes = int((check_time - shift_start_datetime).total_seconds() / 60)

    # --- BƯỚC 4: TẠO CHECK-IN MỚI ---
    existing_today = Attendance.query.filter_by(user_id=user_id, date=today).first()

    if existing_today and existing_today.check_in:
         flash('Bạn đã check-in hôm nay rồi (logic dự phòng).', 'warning')
         return redirect(url_for('attendance.dashboard'))

    # Tạo bản ghi mới VỚI NGÀY HÔM NAY và schedule_id
    attendance = Attendance(
        user_id=user_id,
        check_in=check_time,
        date=today,  # <-- Dòng fix quan trọng từ lần trước
        schedule_id=schedule_id
    )
    db.session.add(attendance)
    db.session.commit()

    # Thông báo check-in thành công với thông tin ca làm việc
    if schedule_today:
        shift_name = schedule_today.shift.name
        if late_minutes > 0:
            flash(f'Check-in thành công lúc {check_time.strftime("%H:%M:%S")} - Ca: {shift_name} (Trễ {late_minutes} phút)', 'warning')
        else:
            flash(f'Check-in thành công lúc {check_time.strftime("%H:%M:%S")} - Ca: {shift_name}', 'success')
    else:
        flash(f'Check-in thành công lúc {check_time.strftime("%H:%M:%S")} (Không có lịch làm việc)', 'success')

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


@attendance_bp.route('/all_history')
def all_history():
    """Trang xem toàn bộ lịch sử chấm công (chỉ admin) - CÓ PHÂN TRANG và BỘ LỌC."""

    page = request.args.get('page', 1, type=int)
    selected_employee_id = request.args.get('employee_id', 0, type=int)
    RECORDS_PER_PAGE = 12

    # Lấy danh sách tất cả nhân viên để hiển thị trong dropdown
    all_employees = User.query.filter(User.role != 'admin').all()

    # Xây dựng query cơ bản
    attendances_query = db.session.query(
        Attendance, User.username
    ).join(User, Attendance.user_id == User.id)

    # Áp dụng bộ lọc nếu có chọn nhân viên cụ thể
    if selected_employee_id > 0:
        attendances_query = attendances_query.filter(Attendance.user_id == selected_employee_id)

    # Sắp xếp và phân trang
    attendances_query = attendances_query.order_by(Attendance.date.desc(), User.username)

    pagination = attendances_query.paginate(
        page=page,
        per_page=RECORDS_PER_PAGE,
        error_out=False
    )

    attendances_on_page = pagination.items

    # Định nghĩa múi giờ
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

    # Gửi dữ liệu vào template
    return render_template(
        'attendance/all_history.html',
        attendances_with_users=attendances_on_page,
        pagination=pagination,
        vn_tz=vn_tz,
        all_employees=all_employees,
        selected_employee_id=selected_employee_id
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
