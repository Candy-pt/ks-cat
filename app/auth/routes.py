# /app/auth/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import User, db
from app import bcrypt 

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):

        # if user and user.password == password:
            
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['avatar_image'] = user.avatar_image
            flash('Đăng nhập thành công!')
            return redirect(url_for('attendance.dashboard')) # Chuyển hướng đến blueprint attendance
        flash('Sai tên đăng nhập hoặc mật khẩu!')
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Đăng xuất thành công!')
    return redirect(url_for('auth.login'))


@auth_bp.route('/about')
def about_page():
    return render_template('about.html')