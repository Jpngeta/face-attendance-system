"""
Database models for Face Attendance System
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index

db = SQLAlchemy()

class Student(db.Model):
    """Student model for storing registered students"""
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    program = db.Column(db.String(100), nullable=True)
    year_of_study = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, inactive, graduated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    face_encodings = db.relationship('FaceEncoding', backref='student', lazy=True, cascade='all, delete-orphan')
    attendance_records = db.relationship('AttendanceRecord', backref='student', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Student {self.name} ({self.student_id})>'

    def to_dict(self):
        """Convert student object to dictionary"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'program': self.program,
            'year_of_study': self.year_of_study,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class FaceEncoding(db.Model):
    """Face encoding model for storing face embeddings"""
    __tablename__ = 'face_encodings'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    encoding = db.Column(db.LargeBinary, nullable=False)  # Store numpy array as binary
    quality_score = db.Column(db.Float, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<FaceEncoding student_id={self.student_id}>'

    def to_dict(self):
        """Convert face encoding object to dictionary"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'quality_score': self.quality_score,
            'image_path': self.image_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }

class AttendanceSession(db.Model):
    """Attendance session model for managing class sessions"""
    __tablename__ = 'attendance_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_name = db.Column(db.String(100), nullable=False)
    course_code = db.Column(db.String(50), nullable=True)
    course_name = db.Column(db.String(200), nullable=True)
    instructor_name = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, paused, completed
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    attendance_records = db.relationship('AttendanceRecord', backref='session', lazy=True, cascade='all, delete-orphan')

    # Indexes
    __table_args__ = (
        Index('idx_session_status_start', 'status', 'start_time'),
    )

    def __repr__(self):
        return f'<AttendanceSession {self.session_name} ({self.status})>'

    def to_dict(self):
        """Convert session object to dictionary"""
        return {
            'id': self.id,
            'session_name': self.session_name,
            'course_code': self.course_code,
            'course_name': self.course_name,
            'instructor_name': self.instructor_name,
            'location': self.location,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'attendance_count': len(self.attendance_records) if self.attendance_records else 0
        }

class AttendanceRecord(db.Model):
    """Attendance record model for storing attendance logs"""
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    confidence_score = db.Column(db.Float, nullable=True)  # Recognition confidence/distance
    status = db.Column(db.String(20), default='present')  # present, late, excused
    image_path = db.Column(db.String(255), nullable=True)  # Optional: store snapshot
    notes = db.Column(db.Text, nullable=True)
    synced_to_cloud = db.Column(db.Boolean, default=False)
    sync_attempts = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_session_student', 'session_id', 'student_id'),
        Index('idx_student_timestamp', 'student_id', 'timestamp'),
        Index('idx_sync_status', 'synced_to_cloud', 'sync_attempts'),
    )

    def __repr__(self):
        return f'<AttendanceRecord session={self.session_id} student={self.student_id}>'

    def to_dict(self):
        """Convert attendance record object to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'student_id': self.student_id,
            'student_name': self.student.name if self.student else None,
            'student_student_id': self.student.student_id if self.student else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'confidence_score': self.confidence_score,
            'status': self.status,
            'image_path': self.image_path,
            'notes': self.notes,
            'synced_to_cloud': self.synced_to_cloud,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SystemConfig(db.Model):
    """System configuration model for storing application settings"""
    __tablename__ = 'system_config'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SystemConfig {self.key}={self.value}>'

    def to_dict(self):
        """Convert config object to dictionary"""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SyncQueue(db.Model):
    """Sync queue model for managing offline data synchronization"""
    __tablename__ = 'sync_queue'

    id = db.Column(db.Integer, primary_key=True)
    record_type = db.Column(db.String(50), nullable=False)  # attendance, student, etc.
    record_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(20), nullable=False)  # create, update, delete
    payload = db.Column(db.Text, nullable=True)  # JSON payload
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    attempts = db.Column(db.Integer, default=0)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)

    # Index for efficient queue processing
    __table_args__ = (
        Index('idx_queue_status_created', 'status', 'created_at'),
    )

    def __repr__(self):
        return f'<SyncQueue {self.record_type}:{self.record_id} ({self.status})>'

    def to_dict(self):
        """Convert sync queue object to dictionary"""
        return {
            'id': self.id,
            'record_type': self.record_type,
            'record_id': self.record_id,
            'action': self.action,
            'status': self.status,
            'attempts': self.attempts,
            'last_error': self.last_error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }
