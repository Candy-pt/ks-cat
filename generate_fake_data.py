import random
from datetime import datetime, date, time, timedelta
from app import create_app, db
from app.models import User, Contract, Attendance, Bonus, Deduction
from app import bcrypt

def generate_fake_data():
    app = create_app()
    with app.app_context():
        # Xóa dữ liệu cũ nếu cần (tùy chọn, uncomment nếu muốn reset)
        # db.session.query(Attendance).delete()
        # db.session.query(Contract).delete()
        # db.session.query(Bonus).delete()
        # db.session.query(Deduction).delete()
        # db.session.query(User).filter(User.role != 'admin').delete()
        # db.session.commit()

        # Tạo 8 nhân viên mẫu
        employees_data = [
            {'username': 'nguyen_van_a', 'full_name': 'Nguyễn Văn A', 'pay_rate': 6000000, 'pay_unit': 'month'},
            {'username': 'tran_thi_b', 'full_name': 'Trần Thị B', 'pay_rate': 5500000, 'pay_unit': 'month'},
            {'username': 'le_van_c', 'full_name': 'Lê Văn C', 'pay_rate': 6500000, 'pay_unit': 'month'},
            {'username': 'pham_thi_d', 'full_name': 'Phạm Thị D', 'pay_rate': 200000, 'pay_unit': 'hour'},  # Part-time
            {'username': 'hoang_van_e', 'full_name': 'Hoàng Văn E', 'pay_rate': 5800000, 'pay_unit': 'month'},
            {'username': 'do_thi_f', 'full_name': 'Đỗ Thị F', 'pay_rate': 6200000, 'pay_unit': 'month'},
            {'username': 'vu_van_g', 'full_name': 'Vũ Văn G', 'pay_rate': 210000, 'pay_unit': 'hour'},  # Part-time
            {'username': 'bui_thi_h', 'full_name': 'Bùi Thị H', 'pay_rate': 5900000, 'pay_unit': 'month'},
        ]

        employees = []
        for emp_data in employees_data:
            # Kiểm tra nếu user đã tồn tại
            existing_user = User.query.filter_by(username=emp_data['username']).first()
            if existing_user:
                employees.append(existing_user)
                continue

            hashed_pw = bcrypt.generate_password_hash('123').decode('utf-8')  # Mật khẩu mẫu: 123
            user = User(
                username=emp_data['username'],
                password=hashed_pw,
                role='employee',
                full_name=emp_data['full_name'],
                email=f"{emp_data['username']}@example.com"
            )
            db.session.add(user)
            db.session.commit()  # Commit để có ID

            # Tạo hợp đồng
            contract = Contract(
                user_id=user.id,
                start_date=date(2024, 8, 1),  # Bắt đầu từ tháng 8 để cover tháng 9-10
                pay_rate=emp_data['pay_rate'],
                pay_unit=emp_data['pay_unit']
            )
            db.session.add(contract)
            employees.append(user)

        db.session.commit()

        # Tạo dữ liệu chấm công cho tháng 9 và 10 năm 2024
        months = [9, 10]
        year = 2024

        for month in months:
            _, num_days = (31, 30) if month == 9 else (31, 31)  # 9: 30 days, 10: 31 days

            for emp in employees:
                # Giả sử mỗi nhân viên làm việc 20-24 ngày/tháng (trừ cuối tuần)
                work_days = random.randint(20, 24)
                worked_dates = random.sample(range(1, num_days + 1), work_days)

                for day in worked_dates:
                    att_date = date(year, month, day)

                    # Bỏ qua cuối tuần (Saturday=5, Sunday=6)
                    if att_date.weekday() >= 5:
                        continue

                    # Tạo thời gian check-in: 8:00 - 9:00 AM
                    check_in_hour = random.randint(8, 9)
                    check_in_minute = random.randint(0, 59)
                    check_in_time = time(check_in_hour, check_in_minute)

                    # Tạo thời gian check-out: 5:00 - 6:00 PM, đảm bảo sau check-in ít nhất 6 giờ
                    min_check_out_hour = max(check_in_hour + 6, 17)  # Tối thiểu 17:00
                    check_out_hour = random.randint(min_check_out_hour, 18)
                    check_out_minute = random.randint(0, 59)
                    check_out_time = time(check_out_hour, check_out_minute)

                    # Kết hợp date và time thành datetime
                    check_in_dt = datetime.combine(att_date, check_in_time)
                    check_out_dt = datetime.combine(att_date, check_out_time)

                    attendance = Attendance(
                        user_id=emp.id,
                        check_in=check_in_dt,
                        check_out=check_out_dt,
                        date=att_date
                    )
                    db.session.add(attendance)

                # Thêm thưởng ngẫu nhiên cho tháng này (0-500k)
                bonus_amount = random.choice([0, 100000, 200000, 300000, 500000])
                if bonus_amount > 0:
                    bonus = Bonus(
                        user_id=emp.id,
                        month=month,
                        year=year,
                        amount=bonus_amount,
                        reason="Thưởng tháng"
                    )
                    db.session.add(bonus)

                # Thêm khấu trừ ngẫu nhiên (0-100k, ví dụ phạt đi trễ)
                deduction_amount = random.choice([0, 50000, 100000])
                if deduction_amount > 0:
                    deduction = Deduction(
                        user_id=emp.id,
                        month=month,
                        year=year,
                        amount=deduction_amount,
                        reason="Khấu trừ phạt"
                    )
                    db.session.add(deduction)

        db.session.commit()
        print("✅ Đã tạo dữ liệu giả định thành công cho 8 nhân viên trong tháng 9 và 10 năm 2024!")
        print("Mật khẩu cho tất cả nhân viên: 123")
        print("Bạn có thể chạy tính lương từ trang admin để kiểm tra.")

if __name__ == '__main__':
    generate_fake_data()
