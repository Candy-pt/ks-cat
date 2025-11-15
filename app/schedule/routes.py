# /app/schedule/routes.py

from flask import (Blueprint, render_template, request, redirect, url_for, 
                   session, flash, jsonify)
# Import decorator dùng chung của bạn
from ..decorators import admin_required 
# Import CSDL và các model
from ..models import db, User, Shift, Schedule
# Import các hàm xử lý thời gian
from datetime import datetime, timedelta, date, time
from sqlalchemy import and_

schedule_bp = Blueprint('schedule', __name__, url_prefix='/schedule')

# --- 1. QUẢN LÝ CA LÀM VIỆC (CRUD) ---

@schedule_bp.route('/shifts')
@admin_required
def manage_shifts():
    """Trang hiển thị & quản lý các ca làm việc mẫu (Ca Sáng, Ca Tối...)."""
    shifts = Shift.query.order_by(Shift.start_time).all()
    return render_template('schedule/manage_shifts.html', shifts=shifts)

@schedule_bp.route('/shifts/add', methods=['GET', 'POST'])
@admin_required 
def add_shift():
    """Trang thêm một ca làm việc mẫu mới."""
    if request.method == 'POST':
        name = request.form.get('name')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')

        try:
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()

            new_shift = Shift(name=name, start_time=start_time, end_time=end_time)
            db.session.add(new_shift)
            db.session.commit()

            flash('Thêm ca làm việc thành công!', 'success')
            return redirect(url_for('schedule.manage_shifts'))
        except ValueError:
            flash('Định dạng thời gian không hợp lệ. Vui lòng sử dụng HH:MM.', 'danger')

    return render_template('schedule/add_shift.html')

@schedule_bp.route('/shifts/edit/<int:shift_id>', methods=['GET', 'POST'])
@admin_required 
def edit_shift(shift_id):
    """Trang sửa một ca làm việc mẫu."""
    shift = Shift.query.get_or_404(shift_id)

    if request.method == 'POST':
        shift.name = request.form.get('name')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')

        try:
            shift.start_time = datetime.strptime(start_time_str, '%H:%M').time()
            shift.end_time = datetime.strptime(end_time_str, '%H:%M').time()

            db.session.commit()
            flash('Cập nhật ca làm việc thành công!', 'success')
            return redirect(url_for('schedule.manage_shifts'))
        except ValueError:
            flash('Định dạng thời gian không hợp lệ. Vui lòng sử dụng HH:MM.', 'danger')

    return render_template('schedule/edit_shift.html', shift=shift)

@schedule_bp.route('/shifts/delete/<int:shift_id>', methods=['POST'])
@admin_required
def delete_shift(shift_id):
    """Xử lý xóa một ca làm việc mẫu."""
    shift = Shift.query.get_or_404(shift_id)

    if Schedule.query.filter_by(shift_id=shift_id).first():
        flash('Không thể xóa ca này vì đang được sử dụng trong lịch làm việc.', 'danger')
    else:
        db.session.delete(shift)
        db.session.commit()
        flash('Xóa ca làm việc thành công!', 'success')

    return redirect(url_for('schedule.manage_shifts'))

# --- 2. XẾP LỊCH CHO ADMIN (GIAO DIỆN 3 NGÀY) ---

@schedule_bp.route('/calendar')
@admin_required 
def calendar():
    """
    Trang xếp lịch chính cho Admin (dạng 3 ngày: Ngày -> Ca -> Nhân viên).
    """
    # Xử lý lấy ngày và phân trang 3 ngày
    start_date_str = request.args.get('start_date')
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = datetime.now().date()
    else:
        start_date = datetime.now().date()

    display_days = [start_date + timedelta(days=i) for i in range(3)]
    end_date = display_days[-1]

    # Lấy dữ liệu
    employees = User.query.filter_by(role='employee').all()
    shifts = Shift.query.order_by(Shift.start_time).all()
    schedules_in_period = Schedule.query.filter(
        Schedule.date.between(start_date, end_date)
    ).all()

    # Xây dựng cấu trúc dữ liệu: schedules_data[ngày][shift_id] = [danh_sách_user]
    schedules_data = {}
    for day in display_days:
        schedules_data[day] = {}
        for shift in shifts:
            schedules_data[day][shift.id] = [] # Khởi tạo

    # Đổ nhân viên vào đúng ca, đúng ngày
    for schedule in schedules_in_period:
        user = next((emp for emp in employees if emp.id == schedule.user_id), None)
        if user and schedule.date in schedules_data and schedule.shift_id in schedules_data[schedule.date]:
            schedules_data[schedule.date][schedule.shift_id].append(user)

    return render_template('schedule/calendar.html',
                           display_days=display_days,
                           shifts=shifts,
                           employees=employees,
                           schedules_data=schedules_data
                           )

# --- 3. API CẬP NHẬT LỊCH (DÙNG CHUNG) ---

@schedule_bp.route('/update_schedule', methods=['POST'])
@admin_required 
def update_schedule():
    """API để JavaScript gọi khi thêm/xóa nhân viên khỏi ca."""
    data = request.get_json()
    user_id = data.get('user_id')
    shift_id = data.get('shift_id')
    date_str = data.get('date')

    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

        existing_schedule = Schedule.query.filter_by(user_id=user_id, date=date_obj).first()

        if shift_id:  # Thêm hoặc cập nhật
            if existing_schedule:
                existing_schedule.shift_id = shift_id
            else:
                new_schedule = Schedule(user_id=user_id, shift_id=shift_id, date=date_obj)
                db.session.add(new_schedule)
        else:  # Xóa (nếu shift_id là null/rỗng)
            if existing_schedule:
                db.session.delete(existing_schedule)

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# --- 4. TRANG XEM LỊCH CỦA NHÂN VIÊN (GIAO DIỆN 3 NGÀY) ---

@schedule_bp.route('/my_schedule')
def my_schedule():
    """Trang xem lịch (read-only) cho nhân viên."""
    if 'user_id' not in session:
        flash('Bạn cần đăng nhập để xem trang này.', 'danger')
        return redirect(url_for('auth.login'))
        
    # Xử lý lấy ngày và phân trang 3 ngày
    start_date_str = request.args.get('start_date')
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = datetime.now().date()
    else:
        start_date = datetime.now().date()

    display_days = [start_date + timedelta(days=i) for i in range(3)]
    end_date = display_days[-1]

    # Lấy lịch của user hiện tại
    schedules = Schedule.query.filter(
        and_(Schedule.user_id == session['user_id'],
             Schedule.date.between(start_date, end_date))
    ).all()

    # Tạo cấu trúc dữ liệu
    week_schedule = {}
    for day in display_days:
        schedule = next((s for s in schedules if s.date == day), None)
        week_schedule[day] = schedule

    return render_template('schedule/my_schedule.html',
                           week_schedule=week_schedule,
                           display_days=display_days
                           )