from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False) 
    role = db.Column(db.String(20), default='employee')
    email = db.Column(db.String(120), unique=True, nullable=True)
    full_name = db.Column(db.String(100), nullable=True)
    gender = db.Column(db.String(20), nullable=True) 
    avatar_image = db.Column(db.String(200), nullable=False, default='default-avatar.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 
    fcm_token = db.Column(db.String(200))

       # Mối quan hệ: Một User có nhiều bản ghi liên quan
    contracts = db.relationship('Contract', backref='user', lazy=True, cascade="all, delete-orphan")
    attendances = db.relationship('Attendance', backref='user', lazy=True, cascade="all, delete-orphan")
    payrolls = db.relationship('Payroll', backref='user', lazy=True, cascade="all, delete-orphan")
    bonuses = db.relationship('Bonus', backref='user', lazy=True, cascade="all, delete-orphan")
    deductions = db.relationship('Deduction', backref='user', lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade="all, delete-orphan", order_by="Notification.timestamp.desc()")
    leave_requests = db.relationship('LeaveRequest', backref='user', lazy=True, cascade="all, delete-orphan")


# Bảng Hợp đồng 
class Contract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    pay_rate = db.Column(db.Float, nullable=False) # 6,000,000 hoặc 20,000
    pay_unit = db.Column(db.String(20), default='month') # 'month' hoặc 'hour'

# Bảng Chấm công 
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    check_in = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    check_out = db.Column(db.DateTime)
    date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    image_path = db.Column(db.String(200))
    gps_lat = db.Column(db.Float)
    gps_lng = db.Column(db.Float)

# Bảng Thưởng
class Bonus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, default=0)
    reason = db.Column(db.String(100))


# các khoản khấu trừ 
class Deduction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(100))

# Bảng lưu kết quả lương hàng tháng 
class Payroll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    gross_salary = db.Column(db.Float)
    total_bonus = db.Column(db.Float)
    total_deduction = db.Column(db.Float)
    net_salary = db.Column(db.Float)
    __table_args__ = (db.UniqueConstraint('user_id', 'month', 'year', name='_user_month_year_uc'),)

class SalarySettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    standard_work_hours_per_day = db.Column(db.Float, default=8)
    standard_work_days_per_month = db.Column(db.Integer, default=24)
    late_penalty_amount = db.Column(db.Float, default=50000)
    

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    leave_request_id = db.Column(db.Integer, db.ForeignKey('leave_request.id'), nullable=True)

    def __repr__(self):
        return f'<Notification {self.id} for user {self.user_id}>'
    

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Loại yêu cầu: 'leave', 'late', 'early', 'shift_change'
    request_type = db.Column(db.String(20), nullable=False, default='leave') 
    # Dùng cho 'leave' (nghỉ phép)
    start_date = db.Column(db.Date) 
    end_date = db.Column(db.Date)   
    # Dùng cho 'late', 'early'
    request_date = db.Column(db.Date) 
    request_time = db.Column(db.Time) 
    # Dùng cho 'shift_change' và lý do chung
    reason = db.Column(db.String(200), nullable=False) # Lý do chung/chi tiết đổi ca
    
    status = db.Column(db.String(20), default='pending') # 'pending', 'approved', 'rejected'
    
    # (Thêm mối quan hệ với Notification nếu bạn có)
    notifications = db.relationship('Notification', backref='leave_request', lazy=True)

    @property
    def relevant_date(self):
        return self.request_date if self.request_type in ['late', 'early'] else self.start_date