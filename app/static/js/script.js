function updateTime() {
    const timeElement = document.getElementById('time');
    
    if (timeElement) { 
        const now = new Date();
        const timeString = now.toLocaleTimeString('vi-VN');
        const dateString = now.toLocaleDateString('vi-VN');
        timeElement.innerHTML = `Thời gian hiện tại: ${timeString} ${dateString}`;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    updateTime();
    setInterval(updateTime, 1000);
});

// Thêm: Tạo hidden input với thời gian local khi submit check-in/out
document.addEventListener('DOMContentLoaded', () => {
    const forms = document.querySelectorAll('form[action*="/check_in"], form[action*="/check_out"]');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const timestamp = new Date().toISOString();  
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'client_timestamp';
            hiddenInput.value = timestamp;
            form.appendChild(hiddenInput);
        });
    });

    const toastElements = document.querySelectorAll('.toast');
    toastElements.forEach(toastEl => {
        const toast = new bootstrap.Toast(toastEl, {
            animation: true,  // Fade in/out mượt
            autohide: true,   // Tự ẩn sau 2s
            delay: 2000       // 2 giây
        });
        toast.show();  // Show từng toast
    });
});

// Thêm: Loading spinner cho form submit
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', () => {
        const spinner = document.createElement('div');
        spinner.className = 'loading';
        spinner.innerHTML = '<div class="spinner"></div> Đang xử lý...';
        form.appendChild(spinner);
        spinner.style.display = 'block';
    });
});

// Giữ nguyên code cũ

//  Firebase FCM cho push QR
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyDKPyqjPdp_FFjNS3F6fN6zdnGG7Ie6UdI",
  authDomain: "attendanceapp-34189.firebaseapp.com",
  projectId: "attendanceapp-34189",
  storageBucket: "attendanceapp-34189.firebasestorage.app",
  messagingSenderId: "337038504509",
  appId: "1:337038504509:web:6d03b73d60652b59b63054",
  measurementId: "G-NW53KH28G1"
};

firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

async function requestPermission() {
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
        const token = await messaging.getToken({ vapidKey: 'your_vapid_key' });  // Từ Firebase
        // Gửi token về server để lưu
        fetch('/save_fcm_token', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({token: token})
        });
    }
}

document.addEventListener('DOMContentLoaded', requestPermission);

function toggleLeaveFields() {
        const type = document.getElementById('request_type').value;
        const leaveFields = document.getElementById('leave_fields');
        const lateEarlyFields = document.getElementById('late_early_fields');
        const startDateInput = document.getElementById('start_date');
        const endDateInput = document.getElementById('end_date');
        const requestDateInput = document.getElementById('request_date');

        // Reset required
        startDateInput.required = false;
        endDateInput.required = false;
        requestDateInput.required = false;

        if (type === 'leave') {
            leaveFields.style.display = 'block';
            lateEarlyFields.style.display = 'none';
            startDateInput.required = true;
            endDateInput.required = true;
        } else if (type === 'late' || type === 'early') {
            leaveFields.style.display = 'none';
            lateEarlyFields.style.display = 'block';
            requestDateInput.required = true;
        } else { // shift_change
            leaveFields.style.display = 'none';
            lateEarlyFields.style.display = 'none';
        }
    }
    // Gọi lần đầu để đảm bảo đúng trạng thái ban đầu
    document.addEventListener('DOMContentLoaded', toggleLeaveFields);