# /app/notification/routes.py (File mới)

from flask import (Blueprint, render_template, session, redirect, url_for)
from ..models import db, Notification
from ..decorators import login_required 

notification_bp = Blueprint('notification', __name__, url_prefix='/notifications')

@notification_bp.route('/')
@login_required
def list_notifications():
    notifications = Notification.query.filter_by(user_id=session['user_id']).order_by(Notification.timestamp.desc()).all()
    
    # Đánh dấu tất cả là "đã đọc"
    for notif in notifications:
        notif.is_read = True
    
    db.session.commit()
    
    return render_template('notification/list.html', notifications=notifications)


