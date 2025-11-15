# /run.py

from app import create_app, db
from app.models import User # Import các model cần thiết
from app import bcrypt
# from authlib.integrations.flask_client import OAuth

app = create_app()

def init_db():
    with app.app_context():
        db.create_all()
        # User mẫu admin (pass: 123, hashed)
        if not User.query.filter_by(username='admin').first():
            hashed_pw = bcrypt.generate_password_hash('123').decode('utf-8')
            admin = User(username='admin', password=hashed_pw, role='admin')
            db.session.add(admin)
            db.session.commit()
            print("User mẫu 'admin' (pass: 123, role: admin) đã được tạo!")
        # Thêm các settings mặc định nếu cần

# if __name__ == '__main__':
#     init_db()

#     app.run(debug=True)
