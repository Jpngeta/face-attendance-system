"""
Migration Script: Transfer data from pickle file to database
Migrates existing face encodings from insightface_encodings.pkl to SQLite database
"""
import os
import pickle
import sys
from pathlib import Path
from app import create_app
from database import DatabaseManager
from models import db

def migrate_pickle_to_database(pickle_file: str = "insightface_encodings.pkl"):
    """
    Migrate face encodings from pickle file to database

    Args:
        pickle_file: Path to the pickle file containing encodings
    """
    print("=" * 70)
    print("FACE ATTENDANCE SYSTEM - DATABASE MIGRATION")
    print("=" * 70)

    # Check if pickle file exists
    if not os.path.exists(pickle_file):
        print(f"[ERROR] Pickle file not found: {pickle_file}")
        print("[INFO] Skipping migration. Database will be empty.")
        return False

    # Load pickle data
    print(f"\n[INFO] Loading data from {pickle_file}...")
    try:
        with open(pickle_file, "rb") as f:
            data = pickle.load(f)

        embeddings = data.get("embeddings", [])
        names = data.get("names", [])

        print(f"[INFO] Found {len(embeddings)} face encodings")
        print(f"[INFO] Unique people: {len(set(names))}")

    except Exception as e:
        print(f"[ERROR] Failed to load pickle file: {e}")
        return False

    # Create Flask app context
    app = create_app()

    with app.app_context():
        print("\n[INFO] Migrating data to database...")

        # Track migration statistics
        students_created = 0
        encodings_added = 0
        errors = 0

        # Group encodings by person
        person_encodings = {}
        for embedding, name in zip(embeddings, names):
            if name not in person_encodings:
                person_encodings[name] = []
            person_encodings[name].append(embedding)

        # Migrate each person
        for person_name, person_embeds in person_encodings.items():
            try:
                print(f"\n[INFO] Processing: {person_name}")

                # Check if student already exists
                student = DatabaseManager.get_student_by_name(person_name)

                if not student:
                    # Create new student
                    # Generate student_id from name (you may want to customize this)
                    student_id = person_name.lower().replace(" ", "_")

                    student = DatabaseManager.create_student(
                        student_id=student_id,
                        name=person_name,
                        email=None,
                        phone=None,
                        program=None,
                        year_of_study=None
                    )
                    students_created += 1
                    print(f"  [+] Created student: {person_name} (ID: {student_id})")
                else:
                    print(f"  [*] Student already exists: {person_name}")

                # Add face encodings
                for i, embedding in enumerate(person_embeds):
                    # Find corresponding image path if exists
                    dataset_path = Path("insightface_dataset") / person_name
                    image_path = None
                    if dataset_path.exists():
                        images = list(dataset_path.glob("*.jpg"))
                        if i < len(images):
                            image_path = str(images[i])

                    face_encoding = DatabaseManager.add_face_encoding(
                        student_id=student.student_id,
                        encoding=embedding,
                        quality_score=None,
                        image_path=image_path
                    )

                    if face_encoding:
                        encodings_added += 1
                        print(f"  [+] Added encoding {i+1}/{len(person_embeds)}")

            except Exception as e:
                print(f"  [ERROR] Failed to migrate {person_name}: {e}")
                errors += 1
                continue

        # Print summary
        print("\n" + "=" * 70)
        print("MIGRATION SUMMARY")
        print("=" * 70)
        print(f"Students created:     {students_created}")
        print(f"Encodings added:      {encodings_added}")
        print(f"Errors:               {errors}")
        print(f"Status:               {'SUCCESS' if errors == 0 else 'COMPLETED WITH ERRORS'}")
        print("=" * 70)

        return errors == 0

def initialize_database():
    """Initialize database with tables"""
    print("\n[INFO] Initializing database...")

    app = create_app()

    with app.app_context():
        # Create all tables
        db.create_all()
        print("[INFO] Database tables created successfully")

        # Verify tables
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"[INFO] Created tables: {', '.join(tables)}")

    return True

def main():
    """Main migration function"""
    print("\n[1/2] Initializing database...")
    if not initialize_database():
        print("[ERROR] Database initialization failed")
        sys.exit(1)

    print("\n[2/2] Migrating data from pickle file...")
    success = migrate_pickle_to_database()

    if success:
        print("\n[SUCCESS] Migration completed successfully!")
        print("\n[INFO] Next steps:")
        print("  1. Review migrated data in the database")
        print("  2. Start the Flask application: python app.py")
        print("  3. Access the dashboard at http://localhost:5000")
    else:
        print("\n[WARNING] Migration completed with errors or skipped")
        print("[INFO] You can still use the system, but you may need to register students manually")

if __name__ == "__main__":
    main()
