# /app/payroll/calculator.py

import csv
import io
from datetime import datetime, date
from calendar import monthrange
from typing import List, Tuple, Dict, Optional 
import zipfile
from ..models import db, User, Contract, Attendance, SalarySettings, Bonus, Deduction, Payroll
import pytz


# ============================================
# === CÁC HÀM HỖ TRỢ CHO VIỆC TÍNH LƯƠNG ===
# ============================================

def _get_salary_settings() -> SalarySettings:
    """Lấy cấu hình lương chung."""
    settings = SalarySettings.query.first()
    if not settings:
        print("❌ LỖI: Chưa có cấu hình lương trong SalarySettings! Hãy tạo một bản ghi.")
        raise Exception("Chưa có cấu hình lương trong SalarySettings!")
    return settings

def _get_active_employees() -> List[User]:
    """Lấy danh sách nhân viên cần tính lương."""
    return User.query.filter(User.role != 'admin').all()

def _get_employee_contract(employee_id: int, month: int, year: int) -> Optional[Contract]:
    """Lấy hợp đồng hợp lệ của nhân viên cho tháng/năm cụ thể."""
    first_day_of_month = date(year, month, 1)
    contract = Contract.query.filter(
        Contract.user_id == employee_id,
        Contract.start_date <= first_day_of_month
    ).order_by(Contract.start_date.desc()).first()
    return contract

def _get_employee_attendance(employee_id: int, month: int, year: int) -> List[Attendance]:
    """Lấy tất cả bản ghi chấm công của nhân viên trong tháng."""
    _, num_days_in_month = monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, num_days_in_month)
    
    attendances = Attendance.query.filter(
        Attendance.user_id == employee_id,
        Attendance.date.between(month_start, month_end)
    ).all()
    return attendances

def _calculate_attendance_metrics(attendances: List[Attendance]) -> Tuple[int, float]:
    """Tính số ngày làm và tổng giờ làm từ danh sách chấm công."""
    actual_work_days = 0
    total_work_hours = 0
    for att in attendances:
        if att.check_in and att.check_out:
            actual_work_days += 1
            duration = att.check_out - att.check_in
            total_work_hours += duration.total_seconds() / 3600
    return actual_work_days, total_work_hours

def _calculate_gross_salary(contract: Contract, actual_work_days: int, total_work_hours: float, settings: SalarySettings) -> float:
    """Tính lương tổng (gross) dựa trên hợp đồng và số liệu chấm công."""
    gross_salary = 0.0 # Khởi tạo là float
    if contract.pay_unit == 'month':
        standard_days = settings.standard_work_days_per_month
        if standard_days is not None and standard_days > 0: # Kiểm tra None
            gross_salary = contract.pay_rate * (actual_work_days / standard_days)
        # In thông tin debug (giữ nguyên từ code gốc)
        print(f"    -> Lương Full-time: {contract.pay_rate} * ({actual_work_days}/{standard_days}) = {gross_salary}")
    elif contract.pay_unit == 'hour':
        gross_salary = contract.pay_rate * total_work_hours
        # In thông tin debug (giữ nguyên từ code gốc)
        print(f"    -> Lương Part-time: {contract.pay_rate} * {total_work_hours} = {gross_salary}")
    return gross_salary

def _get_adjustments(employee_id: int, month: int, year: int) -> Tuple[float, float]:
    """Lấy tổng thưởng và tổng khấu trừ trong tháng."""
    total_bonus = db.session.query(db.func.sum(Bonus.amount)).filter_by(user_id=employee_id, month=month, year=year).scalar() or 0.0
    total_deduction = db.session.query(db.func.sum(Deduction.amount)).filter_by(user_id=employee_id, month=month, year=year).scalar() or 0.0
    return total_bonus, total_deduction

def _save_payroll_record(employee_id: int, month: int, year: int, data: Dict):
    """Lưu hoặc cập nhật bản ghi lương."""
    payroll_record = Payroll.query.filter_by(user_id=employee_id, month=month, year=year).first()
    if not payroll_record:
        payroll_record = Payroll(user_id=employee_id, month=month, year=year)
        db.session.add(payroll_record)
        print(f"    -> Tạo MỚI bản ghi Payroll.") # Thêm thông báo rõ hơn
    else:
         print(f"    -> Cập nhật bản ghi Payroll đã có.") # Thêm thông báo rõ hơn
        
    # Cập nhật các trường từ dictionary 'data'
    payroll_record.base_salary = data.get('base_salary')
    payroll_record.days_worked = data.get('days_worked')
    payroll_record.gross_salary = round(data.get('gross_salary', 0.0), 2)
    payroll_record.bonus_amount = round(data.get('total_bonus', 0.0), 2)
    # payroll_record.deduction_amount = round(data.get('total_deduction', 0.0), 2)
    payroll_record.net_salary = round(data.get('net_salary', 0.0), 2)

    print(f"    -> Lương cuối cùng: {payroll_record.net_salary}. Đang chuẩn bị lưu...")


# ============================================
# ===     HÀM TÍNH LƯƠNG CHÍNH            ===
# ============================================

def calculate_and_store_salaries(month: int, year: int):
    """
    Hàm chính (đã refactor) để điều phối việc tính lương và lưu vào bảng Payroll.
    """
    print(f"🚀 BẮT ĐẦU TÍNH LƯƠNG CHO THÁNG {month}/{year}")
    settings = _get_salary_settings()
    employees = _get_active_employees()

    if not employees:
         print("🟡 Không tìm thấy nhân viên nào để tính lương.")
         return # Thoát sớm nếu không có nhân viên

    for employee in employees:
        print(f"\n--- Đang xử lý cho: {employee.username} ---")

        contract = _get_employee_contract(employee.id, month, year)
        if not contract:
            print(f"    -> 🟡 Bỏ qua: Nhân viên '{employee.username}' không có hợp đồng hợp lệ.")
            continue

        attendances = _get_employee_attendance(employee.id, month, year)
        actual_work_days, total_work_hours = _calculate_attendance_metrics(attendances)
        print(f"    -> Chấm công: {actual_work_days} ngày, {round(total_work_hours, 2)} giờ") # Giữ lại print này

        gross_salary = _calculate_gross_salary(contract, actual_work_days, total_work_hours, settings)
        
        total_bonus, total_deduction = _get_adjustments(employee.id, month, year)
        
        net_salary = gross_salary + total_bonus - total_deduction

        # Chuẩn bị dữ liệu để lưu
        payroll_data = {
            'base_salary': contract.pay_rate,
            'days_worked': actual_work_days,
            'gross_salary': gross_salary,
            'total_bonus': total_bonus,
            'total_deduction': total_deduction,
            'net_salary': net_salary
        }
        
        # Gọi hàm lưu CSDL
        _save_payroll_record(employee.id, month, year, payroll_data)

    try:
        # Commit một lần sau khi xử lý tất cả
        db.session.commit()
        print("\n✅ HOÀN TẤT: Đã tính và lưu lương cho tất cả nhân viên.")
    except Exception as e:
        db.session.rollback() # Rất quan trọng: Hủy bỏ nếu có lỗi
        print(f"\n❌ LỖI KHI COMMIT DATABASE: {e}")
        # Cân nhắc ghi log lỗi chi tiết hơn ở đây
        raise e # Ném lại lỗi để route có thể bắt và hiển thị flash message


# ============================================
# === CÁC HÀM XUẤT BÁO CÁO (GIỮ NGUYÊN)   ===
# ============================================

def generate_salary_report(month: int, year: int):
    """Tạo báo cáo lương tóm tắt (Giữ nguyên)."""
    # ... (code cũ của bạn hoàn toàn giữ nguyên)
    output = io.StringIO()
    writer = csv.writer(output)
    header = ['ID Nhân viên', 'Tên Nhân viên', 'Lương Tổng', 'Tổng Thưởng', 'Tổng Khấu Trừ', 'Lương Thực Nhận']
    writer.writerow(header)
    payrolls = db.session.query(Payroll, User.username).join(User, Payroll.user_id == User.id).filter( # Sửa join condition
        Payroll.month == month,
        Payroll.year == year
    ).all()
    for payroll, username in payrolls:
        writer.writerow([
            payroll.user_id, username,
            payroll.gross_salary, getattr(payroll, 'bonus_amount', 0), # Sử dụng bonus_amount nếu có
            getattr(payroll, 'deduction_amount', 0), # Sử dụng deduction_amount nếu có
            payroll.net_salary
        ])
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    output.close()
    return mem


# ================================================================
# === HÀM XUẤT BÁO CÁO CHI TIẾT ===
# ================================================================

def generate_detailed_report(month: int, year: int) -> io.BytesIO:
    """
    Tạo báo cáo chấm công chi tiết cho TỪNG NHÂN VIÊN,
    nén thành file ZIP và trả về dưới dạng BytesIO trong bộ nhớ.
    """
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    
    # --- Bước 1: Lấy danh sách nhân viên đã có chấm công trong tháng ---
    month_start = date(year, month, 1)
    _, num_days_in_month = monthrange(year, month)
    month_end = date(year, month, num_days_in_month)

    # Lấy ID và Tên của những nhân viên có bản ghi Attendance trong tháng
    employees_in_month = db.session.query(
        User.id, User.username
    ).join(
        Attendance, User.id == Attendance.user_id
    ).filter(
        Attendance.date.between(month_start, month_end),
        User.role != 'admin' # Chỉ lấy nhân viên
    ).distinct().order_by(User.username).all()

    if not employees_in_month:
        # Nếu không có ai chấm công, trả về BytesIO rỗng hoặc báo lỗi tùy bạn
        return io.BytesIO() 

    # --- Bước 2: Tạo file ZIP trong bộ nhớ ---
    zip_buffer = io.BytesIO()
    # Mở file zip để ghi ('w'), sử dụng nén DEFLATED
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:

        # --- Bước 3: Lặp qua từng nhân viên ---
        for user_id, username in employees_in_month:
            
            # Tạo file CSV riêng cho nhân viên này trong bộ nhớ
            output = io.StringIO()
            writer = csv.writer(output)

            # Viết header
            header = ['Ngày', 'Check In', 'Check Out', 'Tổng Giờ Làm']
            writer.writerow(header)

            # Lấy dữ liệu chấm công CHỈ CỦA NHÂN VIÊN NÀY
            attendances = Attendance.query.filter(
                Attendance.user_id == user_id,
                Attendance.date.between(month_start, month_end)
            ).order_by(Attendance.date).all()

            # Viết dữ liệu chấm công vào CSV
            for attendance in attendances:
                check_in_str = attendance.check_in.astimezone(vn_tz).strftime('%H:%M:%S') if attendance.check_in else ''
                check_out_str = attendance.check_out.astimezone(vn_tz).strftime('%H:%M:%S') if attendance.check_out else ''
                work_hours = ''
                if attendance.check_in and attendance.check_out:
                    duration = attendance.check_out - attendance.check_in
                    work_hours = round(duration.total_seconds() / 3600, 2)

                writer.writerow([
                    attendance.date.strftime('%Y-%m-%d'),
                    check_in_str,
                    check_out_str,
                    work_hours
                ])
            
            # --- Bước 4: Thêm file CSV của nhân viên vào ZIP ---
            # Tạo tên file CSV (loại bỏ ký tự không hợp lệ nếu cần)
            safe_username = "".join(c if c.isalnum() else "_" for c in username)
            csv_filename = f'ChamCong_{safe_username}_{month}-{year}.csv'
            
            # Ghi nội dung CSV (đã encode utf-8) vào file trong ZIP
            zip_file.writestr(csv_filename, output.getvalue().encode('utf-8'))
            
            output.close() # Đóng StringIO

    # --- Bước 5: Chuẩn bị file ZIP để gửi đi ---
    zip_buffer.seek(0) # Đưa con trỏ về đầu file ZIP
    return zip_buffer # Trả về đối tượng BytesIO chứa file ZIP