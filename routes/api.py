"""
API Routes for Face Attendance System
RESTful API endpoints for the application
"""
from flask import Blueprint, request, jsonify, current_app, Response
from datetime import datetime, timedelta
from models import db, Student, AttendanceSession, AttendanceRecord
from database import DatabaseManager
import traceback
import os

api_bp = Blueprint('api', __name__)

# Global reference to recognition service (initialized when streaming starts)
recognition_service = None

# Student Management Endpoints

@api_bp.route('/students', methods=['GET']) 
def get_students():
    """Get all students"""
    try:
        status = request.args.get('status', 'active')
        students = DatabaseManager.get_all_students(status)
        return jsonify({
            'success': True,
            'count': len(students),
            'students': [student.to_dict() for student in students]
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/students/<student_id>', methods=['GET'])
def get_student(student_id):
    """Get a specific student"""
    try:
        student = DatabaseManager.get_student_by_id(student_id)
        if not student:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404

        return jsonify({
            'success': True,
            'student': student.to_dict()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/students', methods=['POST'])
def create_student():
    """Create a new student"""
    try:
        data = request.get_json()

        if not data.get('student_id') or not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'student_id and name are required'
            }), 400

        # Check if student already exists
        existing = DatabaseManager.get_student_by_id(data['student_id'])
        if existing:
            return jsonify({
                'success': False,
                'error': 'Student with this ID already exists'
            }), 400

        student = DatabaseManager.create_student(
            student_id=data['student_id'],
            name=data['name'],
            email=data.get('email'),
            phone=data.get('phone'),
            program=data.get('program'),
            year_of_study=data.get('year_of_study')
        )

        return jsonify({
            'success': True,
            'message': 'Student created successfully',
            'student': student.to_dict()
        }), 201
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/students/<student_id>', methods=['PUT'])
def update_student(student_id):
    """Update student information"""
    try:
        data = request.get_json()

        student = DatabaseManager.update_student(student_id, **data)
        if not student:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404

        return jsonify({
            'success': True,
            'message': 'Student updated successfully',
            'student': student.to_dict()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/students/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    """Delete (deactivate) a student"""
    try:
        success = DatabaseManager.delete_student(student_id)
        if not success:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404

        return jsonify({
            'success': True,
            'message': 'Student deleted successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Attendance Session Endpoints


@api_bp.route('/sessions', methods=['GET'])
def get_sessions():
    """Get all attendance sessions"""
    try:
        status = request.args.get('status')
        limit = request.args.get('limit', type=int)

        query = AttendanceSession.query

        if status:
            query = query.filter_by(status=status)

        query = query.order_by(AttendanceSession.start_time.desc())

        if limit:
            query = query.limit(limit)

        sessions = query.all()

        return jsonify({
            'success': True,
            'count': len(sessions),
            'sessions': [session.to_dict() for session in sessions]
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/sessions/active', methods=['GET'])
def get_active_session():
    """Get the currently active session"""
    try:
        session = DatabaseManager.get_active_session()
        if not session:
            return jsonify({
                'success': False,
                'error': 'No active session'
            }), 404

        return jsonify({
            'success': True,
            'session': session.to_dict()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/sessions', methods=['POST'])
def create_session():
    """Create a new attendance session"""
    try:
        data = request.get_json()

        if not data.get('session_name'):
            return jsonify({
                'success': False,
                'error': 'session_name is required'
            }), 400

        # Check if there's already an active session
        active_session = DatabaseManager.get_active_session()
        if active_session:
            return jsonify({
                'success': False,
                'error': 'There is already an active session. Please end it first.',
                'active_session': active_session.to_dict()
            }), 400

        session = DatabaseManager.create_attendance_session(
            session_name=data['session_name'],
            course_code=data.get('course_code'),
            course_name=data.get('course_name'),
            instructor_name=data.get('instructor_name'),
            location=data.get('location')
        )

        return jsonify({
            'success': True,
            'message': 'Session created successfully',
            'session': session.to_dict()
        }), 201
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/sessions/<int:session_id>/end', methods=['POST'])
def end_session(session_id):
    """End an attendance session"""
    try:
        session = DatabaseManager.end_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

        return jsonify({
            'success': True,
            'message': 'Session ended successfully',
            'session': session.to_dict()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Attendance Record Endpoints


@api_bp.route('/attendance', methods=['GET'])
def get_attendance():
    """Get attendance records with optional filters"""
    try:
        session_id = request.args.get('session_id', type=int)
        student_id = request.args.get('student_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', type=int)

        query = AttendanceRecord.query

        if session_id:
            query = query.filter_by(session_id=session_id)

        if student_id:
            student = DatabaseManager.get_student_by_id(student_id)
            if student:
                query = query.filter_by(student_id=student.id)

        if start_date:
            start = datetime.fromisoformat(start_date)
            query = query.filter(AttendanceRecord.timestamp >= start)

        if end_date:
            end = datetime.fromisoformat(end_date)
            query = query.filter(AttendanceRecord.timestamp <= end)

        query = query.order_by(AttendanceRecord.timestamp.desc())

        if limit:
            query = query.limit(limit)

        records = query.all()

        return jsonify({
            'success': True,
            'count': len(records),
            'records': [record.to_dict() for record in records]
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/attendance', methods=['POST'])
def mark_attendance():
    """Mark attendance for a student"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('session_id') or not data.get('student_id'):
            return jsonify({
                'success': False,
                'error': 'session_id and student_id are required'
            }), 400

        # Get student
        student = DatabaseManager.get_student_by_id(data['student_id'])
        if not student:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404

        # Mark attendance
        record = DatabaseManager.mark_attendance(
            session_id=data['session_id'],
            student_db_id=student.id,
            confidence_score=data.get('confidence_score', 0.0),
            status=data.get('status', 'present'),
            image_path=data.get('image_path'),
            cooldown_minutes=current_app.config.get('ATTENDANCE_COOLDOWN_MINUTES', 5)
        )

        if not record:
            return jsonify({
                'success': False,
                'error': 'Attendance already marked recently (within cooldown period)'
            }), 400

        return jsonify({
            'success': True,
            'message': 'Attendance marked successfully',
            'record': record.to_dict()
        }), 201
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/attendance/stats', methods=['GET'])
def get_attendance_stats():
    """Get attendance statistics"""
    try:
        session_id = request.args.get('session_id', type=int)
        stats = DatabaseManager.get_attendance_stats(session_id)

        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# System Status Endpoints


@api_bp.route('/status', methods=['GET'])
def system_status():
    """Get system status"""
    try:
        total_students = Student.query.filter_by(status='active').count()
        total_sessions = AttendanceSession.query.count()
        total_records = AttendanceRecord.query.count()
        active_session = DatabaseManager.get_active_session()

        return jsonify({
            'success': True,
            'status': {
                'total_students': total_students,
                'total_sessions': total_sessions,
                'total_attendance_records': total_records,
                'active_session': active_session.to_dict() if active_session else None,
                'timestamp': datetime.utcnow().isoformat()
            }
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


# Live Recognition & Video Streaming Endpoints


@api_bp.route('/recognition/stream', methods=['GET'])
def video_stream():
    """
    Video streaming endpoint - returns MJPEG stream
    Usage: <img src="/api/recognition/stream">
    """
    global recognition_service

    try:
        # Get active session for auto-attendance marking
        active_session = DatabaseManager.get_active_session()
        session_id = active_session.id if active_session else None

        # Initialize recognition service if not already done
        if recognition_service is None:
            from recognition_service import FaceRecognitionService
            from flask import current_app
            recognition_service = FaceRecognitionService(flask_app=current_app._get_current_object())

        # Create a wrapper generator that maintains Flask app context
        from flask import current_app
        app = current_app._get_current_object()

        def generate_with_context():
            with app.app_context():
                yield from recognition_service.generate_frames(
                    session_id=session_id,
                    auto_mark_attendance=True
                )

        # Return streaming response
        return Response(
            generate_with_context(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to start video stream: {str(e)}'
        }), 500

@api_bp.route('/recognition/status', methods=['GET'])
def recognition_status():
    """Get recognition service status"""
    global recognition_service

    try:
        active_session = DatabaseManager.get_active_session()

        return jsonify({
            'success': True,
            'status': {
                'service_initialized': recognition_service is not None,
                'camera_active': recognition_service.camera_started if recognition_service else False,
                'active_session': active_session.to_dict() if active_session else None,
                'known_faces': len(recognition_service.known_names) if recognition_service else 0
            }
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/recognition/reload', methods=['POST'])
def reload_encodings():
    """Reload face encodings from database"""
    global recognition_service

    try:
        if recognition_service is None:
            return jsonify({
                'success': False,
                'error': 'Recognition service not initialized'
            }), 400

        recognition_service.load_encodings_from_db()

        return jsonify({
            'success': True,
            'message': 'Face encodings reloaded',
            'count': len(recognition_service.known_names)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/recognition/stop', methods=['POST'])
def stop_recognition_stream():
    """Stop the recognition video stream"""
    global recognition_service

    try:
        print("[API] /recognition/stop endpoint called")

        if recognition_service is None:
            print("[API] Recognition service not initialized")
            return jsonify({
                'success': False,
                'error': 'Recognition service not initialized'
            }), 400

        print("[API] Calling recognition_service.stop_recognition_stream()")
        recognition_service.stop_recognition_stream()
        print("[API] Stream stop signal sent successfully")

        return jsonify({
            'success': True,
            'message': 'Recognition stream stopped'
        }), 200
    except Exception as e:
        print(f"[API] Error in stop endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Enrollment Endpoints

@api_bp.route('/enrollment/start', methods=['POST'])
def start_enrollment():
    """
    Start enrollment session for a student
    Validates student info but doesn't create record yet (waits for photos)
    """
    global recognition_service

    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('student_id') or not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'student_id and name are required'
            }), 400

        # Check if student already exists
        existing = DatabaseManager.get_student_by_id(data['student_id'])
        if existing:
            return jsonify({
                'success': False,
                'error': 'Student with this ID already exists'
            }), 400

        # Initialize recognition service if needed
        if recognition_service is None:
            from recognition_service import FaceRecognitionService
            recognition_service = FaceRecognitionService(flask_app=current_app._get_current_object())

        # Return success without creating student yet
        # Student will be created when first photo is captured
        return jsonify({
            'success': True,
            'message': 'Validation passed, ready for photo capture',
            'student_data': data  # Return the data for frontend to store temporarily
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/enrollment/capture', methods=['POST'])
def capture_enrollment_photo():
    """
    Capture a single photo for enrollment
    Creates student record on first photo capture
    """
    global recognition_service

    try:
        data = request.get_json()

        if not data.get('student_id'):
            return jsonify({
                'success': False,
                'error': 'student_id is required'
            }), 400

        # Check if student exists
        student = DatabaseManager.get_student_by_id(data['student_id'])

        # If student doesn't exist, create them now (first photo capture)
        if not student:
            # Student data should be passed from frontend
            if not data.get('name'):
                return jsonify({
                    'success': False,
                    'error': 'Student data required for first photo capture'
                }), 400

            print(f"[INFO] Creating student record on first photo: {data['student_id']}")
            student = DatabaseManager.create_student(
                student_id=data['student_id'],
                name=data['name'],
                email=data.get('email'),
                phone=data.get('phone'),
                program=data.get('program'),
                year_of_study=data.get('year_of_study')
            )

            if not student:
                return jsonify({
                    'success': False,
                    'error': 'Failed to create student record'
                }), 500

        # Initialize recognition service if needed
        if recognition_service is None:
            from recognition_service import FaceRecognitionService
            recognition_service = FaceRecognitionService(flask_app=current_app._get_current_object())

        # Create enrollment directory if needed
        enrollment_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'enrollments', student.student_id)
        os.makedirs(enrollment_dir, exist_ok=True)

        # Generate filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{student.student_id}_{timestamp}.jpg"
        filepath = os.path.join(enrollment_dir, filename)

        # Capture photo and get embedding
        success, embedding, quality_score = recognition_service.capture_enrollment_photo_with_quality(
            person_name=student.name,
            save_path=filepath
        )

        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to capture photo or detect face'
            }), 400

        # Save embedding to database
        # Pass student.student_id (the string ID like "STU001")
        face_encoding = DatabaseManager.add_face_encoding(
            student_id=student.student_id,  # Pass string student ID
            encoding=embedding,
            quality_score=quality_score,
            image_path=filepath
        )

        if not face_encoding:
            return jsonify({
                'success': False,
                'error': 'Failed to save face encoding to database'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Photo captured successfully',
            'encoding_id': face_encoding.id,
            'quality_score': quality_score,
            'image_path': filepath,
            'total_encodings': len(student.face_encodings)
        }), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/enrollment/complete', methods=['POST'])
def complete_enrollment():
    """
    Complete enrollment process
    Validates that sufficient photos have been captured and reloads encodings
    """
    global recognition_service

    try:
        data = request.get_json()

        if not data.get('student_id'):
            return jsonify({
                'success': False,
                'error': 'student_id is required'
            }), 400

        # Get student
        student = DatabaseManager.get_student_by_id(data['student_id'])
        if not student:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404

        # Check if sufficient encodings
        encoding_count = len(student.face_encodings)
        if encoding_count < 3:
            return jsonify({
                'success': False,
                'error': f'Insufficient photos. Please capture at least 3 photos (current: {encoding_count})'
            }), 400

        # Reload encodings into recognition service
        if recognition_service:
            recognition_service.load_encodings_from_db()

        return jsonify({
            'success': True,
            'message': f'Enrollment complete! {encoding_count} photos captured.',
            'student': student.to_dict(),
            'encoding_count': encoding_count
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/enrollment/preview', methods=['GET'])
def enrollment_preview_stream():
    """
    Video preview stream for enrollment
    Shows live camera feed with face detection overlay
    """
    global recognition_service

    try:
        # Initialize recognition service if needed
        if recognition_service is None:
            from recognition_service import FaceRecognitionService
            recognition_service = FaceRecognitionService(flask_app=current_app._get_current_object())

        # Get Flask app for context
        app = current_app._get_current_object()

        def generate_preview():
            with app.app_context():
                yield from recognition_service.generate_enrollment_preview()

        return Response(
            generate_preview(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to start preview stream: {str(e)}'
        }), 500

@api_bp.route('/enrollment/stop', methods=['POST'])
def stop_enrollment_stream():
    """Stop the enrollment preview stream"""
    global recognition_service

    try:
        if recognition_service is None:
            return jsonify({
                'success': False,
                'error': 'Recognition service not initialized'
            }), 400

        recognition_service.stop_enrollment_stream()

        return jsonify({
            'success': True,
            'message': 'Enrollment preview stream stopped'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500