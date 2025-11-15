from app import create_app, db
from app.models import User, Attendance
import random
from datetime import datetime, timedelta
import pytz

app = create_app()

def seed_attendance_for_user():
    with app.app_context():
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        
        # --- THAY ĐỔI Ở ĐÂY ---
        # 1. Chỉ tìm nhân viên có username là 'thuthu'
        emp = User.query.filter_by(username='thuthu').first()

        # 2. Kiểm tra xem có tìm thấy nhân viên không
        if not emp:
            print("LỖI: Không tìm thấy nhân viên tên 'thuthu'. Vui lòng kiểm tra lại.")
            return # Dừng hàm nếu không tìm thấy

        # 3. Bỏ vòng lặp 'for emp in employees:'
        
        print(f"Đang thêm dữ liệu cho nhân viên: {emp.username}") # <-- Sửa 'emp.thuthu' thành 'emp.username'
        
        for day in range(1, 31):
            date = datetime(2025, 11, day)
            # Chỉ thêm cho ngày làm việc (thứ 2-6)
            if date.weekday() < 5:
                # Random check-in từ 7:30-8:30
                check_in = vn_tz.localize(datetime(2025, 11, day, 8, 0) + timedelta(minutes=random.randint(-30, 30)))
                # Check-out sau 8 giờ ±30 phút
                check_out = check_in + timedelta(hours=8, minutes=random.randint(-30, 30))

                att = Attendance(
                    user_id=emp.id,
                    check_in=check_in,
                    check_out=check_out,
                    date=date.date()
                )
                db.session.add(att)

        db.session.commit()
        print(f"Đã thêm dữ liệu chấm công tháng 11/2025 cho {emp.username} thành công!")

if __name__ == '__main__':
    seed_attendance_for_user()