#!/usr/bin/env python3
"""
Script to check attendance system setup and diagnose issues
"""
from app import create_app
from database import DatabaseManager
from models import Student, AttendanceSession, AttendanceRecord

def main():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("FACE ATTENDANCE SYSTEM - STATUS CHECK")
        print("=" * 60)

        # Check for active session
        print("\n1. CHECKING ACTIVE SESSION:")
        active_session = DatabaseManager.get_active_session()
        if active_session:
            print(f"   ✓ Active session found!")
            print(f"     - Name: {active_session.session_name}")
            print(f"     - ID: {active_session.id}")
            print(f"     - Course: {active_session.course_code or 'N/A'}")
            print(f"     - Started: {active_session.start_time}")
        else:
            print("   ✗ NO ACTIVE SESSION FOUND!")
            print("   → You need to create a session for attendance to work")
            print("   → Go to Sessions page and click 'New Session'")

        # Check students
        print("\n2. CHECKING STUDENTS:")
        students = Student.query.filter_by(status='active').all()
        print(f"   Active students: {len(students)}")
        if students:
            for s in students:
                print(f"   - {s.name} (student_id: {s.student_id}, db_id: {s.id})")
        else:
            print("   ✗ No active students found!")

        # Check face encodings
        print("\n3. CHECKING FACE ENCODINGS:")
        encodings = DatabaseManager.get_all_face_encodings()
        print(f"   Registered faces: {len(encodings)}")
        if encodings:
            for name, enc, db_id in encodings:
                print(f"   - {name} (db_id: {db_id})")
        else:
            print("   ✗ No face encodings found!")
            print("   → You need to register faces first")

        # Check recent attendance records
        print("\n4. CHECKING RECENT ATTENDANCE:")
        if active_session:
            records = AttendanceRecord.query.filter_by(
                session_id=active_session.id
            ).order_by(AttendanceRecord.timestamp.desc()).limit(5).all()
            print(f"   Recent records for this session: {len(records)}")
            for r in records:
                student = Student.query.get(r.student_id)
                print(f"   - {student.name if student else 'Unknown'} at {r.timestamp}")
        else:
            print("   Skipped (no active session)")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY:")
        if active_session and students and encodings:
            print("✓ System ready for attendance tracking!")
            print(f"✓ Session: {active_session.session_name}")
            print(f"✓ Students: {len(students)}")
            print(f"✓ Face encodings: {len(encodings)}")
        else:
            print("✗ System NOT ready. Issues found:")
            if not active_session:
                print("  - No active session")
            if not students:
                print("  - No students registered")
            if not encodings:
                print("  - No face encodings")
        print("=" * 60)

if __name__ == "__main__":
    main()
