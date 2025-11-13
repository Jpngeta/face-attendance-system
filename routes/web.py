"""
Web Routes for Face Attendance System
HTML page routes for the dashboard
"""
from flask import Blueprint, render_template, redirect, url_for, request
from models import db, Student, AttendanceSession, AttendanceRecord
from database import DatabaseManager
from datetime import datetime, timedelta

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    """Home page - Dashboard"""
    try:
        # Get active session
        active_session = DatabaseManager.get_active_session()

        # Get recent sessions
        recent_sessions = AttendanceSession.query.order_by(
            AttendanceSession.start_time.desc()
        ).limit(5).all()

        # Get statistics
        total_students = Student.query.filter_by(status='active').count()
        total_sessions = AttendanceSession.query.count()

        # Get today's attendance
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_attendance = AttendanceRecord.query.filter(
            AttendanceRecord.timestamp >= today_start
        ).count()

        return render_template('index.html',
                             active_session=active_session,
                             recent_sessions=recent_sessions,
                             total_students=total_students,
                             total_sessions=total_sessions,
                             today_attendance=today_attendance)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500

@web_bp.route('/students')
def students_page():
    """Students management page"""
    try:
        students = DatabaseManager.get_all_students('active')
        return render_template('students.html', students=students)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500

@web_bp.route('/sessions')
def sessions_page():
    """Sessions management page"""
    try:
        sessions = AttendanceSession.query.order_by(
            AttendanceSession.start_time.desc()
        ).all()
        return render_template('sessions.html', sessions=sessions)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500

@web_bp.route('/sessions/<int:session_id>')
def session_detail(session_id):
    """Session detail page"""
    try:
        session = DatabaseManager.get_session_by_id(session_id)
        if not session:
            return render_template('error.html', error='Session not found'), 404

        # Get attendance records for this session
        records = DatabaseManager.get_session_attendance(session_id)

        # Get statistics
        stats = DatabaseManager.get_attendance_stats(session_id)

        return render_template('session_detail.html',
                             session=session,
                             records=records,
                             stats=stats)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500

@web_bp.route('/attendance')
def attendance_page():
    """Attendance records page"""
    try:
        # Get filter parameters
        session_id = request.args.get('session_id', type=int)
        student_id = request.args.get('student_id')

        query = AttendanceRecord.query

        if session_id:
            query = query.filter_by(session_id=session_id)

        if student_id:
            student = DatabaseManager.get_student_by_id(student_id)
            if student:
                query = query.filter_by(student_id=student.id)

        records = query.order_by(AttendanceRecord.timestamp.desc()).limit(100).all()

        return render_template('attendance.html', records=records)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500

@web_bp.route('/register')
def register_page():
    """Student registration page"""
    return render_template('register.html')

@web_bp.route('/settings')
def settings_page():
    """Settings page"""
    return render_template('settings.html')

@web_bp.route('/live')
def live_recognition():
    """Live recognition page with video feed"""
    try:
        active_session = DatabaseManager.get_active_session()
        return render_template('live_recognition.html', active_session=active_session)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500
