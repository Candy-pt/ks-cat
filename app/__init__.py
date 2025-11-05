from flask import Flask, g, session
from config import Config
from .models import db, Notification
from flask_bcrypt import Bcrypt
from flask_mail import Mail
import os

# Khởi tạo các extensions ở ngoài factory
bcrypt = Bcrypt()
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Tạo thư mục upload nếu chưa có
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Khởi tạo các extensions với app
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)

    @app.before_request
    def load_user_notifications():
        """
        Hàm này sẽ chạy TRƯỚC MỖI REQUEST.
        Nó lấy số thông báo chưa đọc và lưu vào biến global 'g'
        để template có thể truy cập được.
        """
        if 'user_id' in session:
            # Chỉ đếm số thông báo CHƯA ĐỌC
            count = Notification.query.filter_by(
                user_id=session['user_id'], 
                is_read=False
            ).count()
            g.unread_notifications_count = count
        else:
            g.unread_notifications_count = 0
    # ========================================================

    # Đăng ký các Blueprints
    from .auth.routes import auth_bp
    from .attendance.routes import attendance_bp
    from .employee.routes import employee_bp
    from .payroll.routes import payroll_bp
    from .contract.routes import contract_bp 
    from .leave.routes import leave_bp
    from .notification.routes import notification_bp
    from .user.routes import user_bp

    
    app.register_blueprint(auth_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(payroll_bp)
    app.register_blueprint(contract_bp) 
    app.register_blueprint(leave_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(user_bp)


    return app