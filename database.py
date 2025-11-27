"""
Database helper utilities for Face Attendance System
"""
import numpy as np
import pickle
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from models import db, Student, FaceEncoding, AttendanceSession, AttendanceRecord, SyncQueue

class DatabaseManager:
    """Database manager for handling common database operations"""

    @staticmethod
    def create_student(student_id: str, name: str, email: Optional[str] = None,
                      phone: Optional[str] = None, program: Optional[str] = None,
                      year_of_study: Optional[int] = None) -> Student:
        """Create a new student"""
        student = Student(
            student_id=student_id,
            name=name,
            email=email,
            phone=phone,
            program=program,
            year_of_study=year_of_study
        )
        db.session.add(student)
        db.session.commit()
        return student

    @staticmethod
    def get_student_by_id(student_id: str) -> Optional[Student]:
        """Get student by student ID"""
        return Student.query.filter_by(student_id=student_id).first()

    @staticmethod
    def get_student_by_name(name: str) -> Optional[Student]:
        """Get student by name"""
        return Student.query.filter_by(name=name).first()

    @staticmethod
    def get_all_students(status: str = 'active') -> List[Student]:
        """Get all students with given status"""
        if status:
            return Student.query.filter_by(status=status).all()
        return Student.query.all()

    @staticmethod
    def update_student(student_id: str, **kwargs) -> Optional[Student]:
        """Update student information"""
        student = DatabaseManager.get_student_by_id(student_id)
        if student:
            for key, value in kwargs.items():
                if hasattr(student, key):
                    setattr(student, key, value)
            student.updated_at = datetime.utcnow()
            db.session.commit()
        return student

    @staticmethod
    def delete_student(student_id: str) -> bool:
        """Delete a student (soft delete by setting status to inactive)"""
        student = DatabaseManager.get_student_by_id(student_id)
        if student:
            student.status = 'inactive'
            student.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        return False

    @staticmethod
    def add_face_encoding(student_id: str, encoding: np.ndarray,
                         quality_score: Optional[float] = None,
                         image_path: Optional[str] = None) -> Optional[FaceEncoding]:
        """Add face encoding for a student"""
        student = DatabaseManager.get_student_by_id(student_id)
        if not student:
            return None

        # Serialize numpy array to binary
        encoding_binary = pickle.dumps(encoding)

        face_encoding = FaceEncoding(
            student_id=student.id,
            encoding=encoding_binary,
            quality_score=quality_score,
            image_path=image_path
        )
        db.session.add(face_encoding)
        db.session.commit()
        return face_encoding

    @staticmethod
    def get_all_face_encodings(active_only: bool = True) -> List[Tuple[str, np.ndarray, int]]:
        """
        Get all face encodings
        Returns: List of tuples (student_name, encoding, student_db_id)
        """
        query = db.session.query(
            Student.name,
            FaceEncoding.encoding,
            Student.id
        ).join(
            FaceEncoding, Student.id == FaceEncoding.student_id
        )

        if active_only:
            query = query.filter(
                Student.status == 'active',
                FaceEncoding.is_active == True
            )

        results = query.all()

        # Deserialize encodings
        encodings_list = []
        for name, encoding_binary, student_id in results:
            encoding = pickle.loads(encoding_binary)
            encodings_list.append((name, encoding, student_id))

        return encodings_list

    @staticmethod
    def create_attendance_session(session_name: str, course_code: Optional[str] = None,
                                 course_name: Optional[str] = None,
                                 instructor_name: Optional[str] = None,
                                 instructor_email: Optional[str] = None,
                                 location: Optional[str] = None) -> AttendanceSession:
        """Create a new attendance session"""
        session = AttendanceSession(
            session_name=session_name,
            course_code=course_code,
            course_name=course_name,
            instructor_name=instructor_name,
            instructor_email=instructor_email,
            location=location
        )
        db.session.add(session)
        db.session.commit()
        return session

    @staticmethod
    def get_active_session() -> Optional[AttendanceSession]:
        """Get the currently active session"""
        return AttendanceSession.query.filter_by(status='active').first()

    @staticmethod
    def get_session_by_id(session_id: int) -> Optional[AttendanceSession]:
        """Get session by ID"""
        return AttendanceSession.query.get(session_id)

    @staticmethod
    def end_session(session_id: int) -> Optional[AttendanceSession]:
        """End an attendance session"""
        session = DatabaseManager.get_session_by_id(session_id)
        if session:
            session.status = 'completed'
            session.end_time = datetime.utcnow()
            db.session.commit()
        return session

    @staticmethod
    def mark_attendance(session_id: int, student_db_id: int,
                       confidence_score: float,
                       status: str = 'present',
                       image_path: Optional[str] = None,
                       cooldown_minutes: int = 5) -> Optional[AttendanceRecord]:
        """
        Mark attendance for a student in a session

        Args:
            session_id: Session ID
            student_db_id: Student database ID (not student_id string)
            confidence_score: Recognition confidence score
            status: Attendance status (present, late, excused)
            image_path: Optional path to captured image
            cooldown_minutes: Prevent duplicate marking within this time

        Returns:
            AttendanceRecord if created, None if duplicate within cooldown period
        """
        # Check for recent attendance (prevent duplicates)
        cooldown_time = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
        recent_record = AttendanceRecord.query.filter(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.student_id == student_db_id,
            AttendanceRecord.timestamp >= cooldown_time
        ).first()

        if recent_record:
            return None  # Already marked recently

        # Create new attendance record
        record = AttendanceRecord(
            session_id=session_id,
            student_id=student_db_id,
            confidence_score=confidence_score,
            status=status,
            image_path=image_path
        )
        db.session.add(record)
        db.session.commit()
        return record

    @staticmethod
    def get_session_attendance(session_id: int) -> List[AttendanceRecord]:
        """Get all attendance records for a session"""
        return AttendanceRecord.query.filter_by(session_id=session_id).all()

    @staticmethod
    def get_student_attendance_history(student_id: str,
                                      start_date: Optional[datetime] = None,
                                      end_date: Optional[datetime] = None) -> List[AttendanceRecord]:
        """Get attendance history for a student"""
        student = DatabaseManager.get_student_by_id(student_id)
        if not student:
            return []

        query = AttendanceRecord.query.filter_by(student_id=student.id)

        if start_date:
            query = query.filter(AttendanceRecord.timestamp >= start_date)
        if end_date:
            query = query.filter(AttendanceRecord.timestamp <= end_date)

        return query.order_by(AttendanceRecord.timestamp.desc()).all()

    @staticmethod
    def get_unsynced_records() -> List[AttendanceRecord]:
        """Get attendance records that haven't been synced to cloud"""
        return AttendanceRecord.query.filter_by(synced_to_cloud=False).all()

    @staticmethod
    def mark_as_synced(record_id: int) -> bool:
        """Mark an attendance record as synced"""
        record = AttendanceRecord.query.get(record_id)
        if record:
            record.synced_to_cloud = True
            db.session.commit()
            return True
        return False

    @staticmethod
    def add_to_sync_queue(record_type: str, record_id: int,
                         action: str, payload: Optional[str] = None) -> SyncQueue:
        """Add item to sync queue"""
        queue_item = SyncQueue(
            record_type=record_type,
            record_id=record_id,
            action=action,
            payload=payload
        )
        db.session.add(queue_item)
        db.session.commit()
        return queue_item

    @staticmethod
    def get_pending_sync_items(limit: int = 50) -> List[SyncQueue]:
        """Get pending items from sync queue"""
        return SyncQueue.query.filter_by(
            status='pending'
        ).order_by(
            SyncQueue.created_at
        ).limit(limit).all()

    @staticmethod
    def update_sync_status(queue_id: int, status: str,
                          error: Optional[str] = None) -> bool:
        """Update sync queue item status"""
        item = SyncQueue.query.get(queue_id)
        if item:
            item.status = status
            item.attempts += 1
            if error:
                item.last_error = error
            if status == 'completed':
                item.processed_at = datetime.utcnow()
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_attendance_stats(session_id: Optional[int] = None) -> dict:
        """Get attendance statistics"""
        if session_id:
            total = AttendanceRecord.query.filter_by(session_id=session_id).count()
            present = AttendanceRecord.query.filter_by(
                session_id=session_id, status='present'
            ).count()
            late = AttendanceRecord.query.filter_by(
                session_id=session_id, status='late'
            ).count()
        else:
            total = AttendanceRecord.query.count()
            present = AttendanceRecord.query.filter_by(status='present').count()
            late = AttendanceRecord.query.filter_by(status='late').count()

        return {
            'total': total,
            'present': present,
            'late': late,
            'absent': max(0, Student.query.filter_by(status='active').count() - total) if session_id else 0
        }
