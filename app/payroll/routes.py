# /app/payroll/routes.py

from flask import (Blueprint, render_template, request, redirect, url_for, 
                   session, flash, send_file)
from datetime import datetime, timedelta
import pytz
from functools import wraps

# Import các thành phần cần thiết
from ..models import db, User, SalarySettings, Bonus, Payroll 
from ..decorators import admin_required 
from ..payroll.calculator import calculate_and_store_salaries, generate_salary_report, generate_detailed_report

# KHỞI TẠO BLUEPRINT
payroll_bp = Blueprint('payroll', __name__, url_prefix='/payroll')


# CÁC ROUTE XỬ LÝ LƯƠNG
# /app/payroll/routes.py

@payroll_bp.route('/', methods=['GET', 'POST'])
@admin_required
def salary_page():
    """Trang chính để xem, nhập thưởng và tính lương."""
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    
    if request.method == 'POST':
        year = int(request.form.get('year', datetime.now(vn_tz).year))
        month = int(request.form.get('month', datetime.now(vn_tz).month))
    else:
        year = int(request.args.get('year', datetime.now(vn_tz).year))
        month = int(request.args.get('month', datetime.now(vn_tz).month))

    settings = SalarySettings.query.first()
    if not settings:
        settings = SalarySettings()
        db.session.add(settings)
        db.session.commit()

    if request.method == 'POST':
        # Lưu các khoản thưởng từ form
        for key, value in request.form.items():
            if key.startswith('bonus_'):
                user_id = int(key.split('_')[1])
                # Chuyển đổi giá trị rỗng thành 0
                amount = float(value) if value else 0
                
                existing_bonus = Bonus.query.filter_by(user_id=user_id, month=month, year=year).first()
                if existing_bonus:
                    existing_bonus.amount = amount
                elif amount != 0: # Chỉ tạo mới nếu có giá trị
                    new_bonus = Bonus(user_id=user_id, month=month, year=year, amount=amount, reason="Thưởng tháng")
                    db.session.add(new_bonus)
        
        db.session.commit()
        flash('Đã cập nhật thưởng thành công!', 'success')
        
        # Chạy hàm tính lương
        try:
            calculate_and_store_salaries(month, year)
            flash('Đã tính và lưu lại bảng lương!', 'info')
        except Exception as e:
            flash(f'Có lỗi xảy ra khi tính lương: {e}', 'danger')

        return redirect(url_for('payroll.salary_page', month=month, year=year))

    # === LOGIC MỚI ĐỂ HIỂN THỊ DANH SÁCH NHÂN VIÊN ===
    # 1. Lấy tất cả nhân viên
    employees = User.query.filter(User.role != 'admin').all()
    
    # 2. Lấy tất cả bản ghi payroll và bonus đã có của tháng này
    payrolls_dict = {p.user_id: p for p in Payroll.query.filter_by(month=month, year=year).all()}
    bonuses_dict = {b.user_id: b for b in Bonus.query.filter_by(month=month, year=year).all()}

    # 3. Tạo một danh sách dữ liệu hoàn chỉnh để gửi tới template
    payroll_data = []
    for emp in employees:
        payroll_record = payrolls_dict.get(emp.id)
        bonus_record = bonuses_dict.get(emp.id)
        
        payroll_data.append({
            'user': emp,
            'payroll': payroll_record, # Sẽ là None nếu chưa có
            'bonus_amount': bonus_record.amount if bonus_record else 0
        })
    
    month_str = datetime(year, month, 1).strftime('%B %Y')
    
    return render_template('payroll/salary.html', 
                           payroll_data=payroll_data, # Gửi biến mới này
                           settings=settings, 
                           month_str=month_str, 
                           current_month=month, 
                           current_year=year)

@payroll_bp.route('/report/summary')
@admin_required
def salary_report_summary():
    """Tải về báo cáo lương tóm tắt (file CSV)."""
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    year = int(request.args.get('year', datetime.now(vn_tz).year))
    month = int(request.args.get('month', datetime.now(vn_tz).month))

    csv_output = generate_salary_report(month, year)
    
    download_name = f'Bao_cao_luong_tom_tat_{month}-{year}.csv'
    return send_file(csv_output, mimetype='text/csv', as_attachment=True, download_name=download_name)


@payroll_bp.route('/report/detailed')
@admin_required
def salary_report_detailed():
    """Tải về báo cáo chấm công chi tiết (file ZIP).""" # 
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    year = int(request.args.get('year', datetime.now(vn_tz).year))
    month = int(request.args.get('month', datetime.now(vn_tz).month))

    # Hàm này giờ trả về file ZIP dưới dạng BytesIO
    zip_output_buffer = generate_detailed_report(month, year) 
    
    # Tạo tên file ZIP
    download_name = f'BaoCaoChamCongChiTiet_{month}-{year}.zip' # <-- Đuôi .zip
    
    # Gửi file ZIP đi
    return send_file(
        zip_output_buffer, 
        mimetype='application/zip', # <-- Sửa mimetype thành zip
        as_attachment=True, 
        download_name=download_name
    )