"""
Google Sheets Integration Service
Handles synchronization of attendance data to Google Sheets
"""
import os
from datetime import datetime
from typing import List, Dict, Optional
import gspread
from google.oauth2.service_account import Credentials
from config import Config
from database import DatabaseManager
from models import AttendanceRecord

class GoogleSheetsService:
    """Service for syncing attendance data to Google Sheets"""

    def __init__(self, config: Config = None):
        """
        Initialize Google Sheets service

        Args:
            config: Configuration object (uses default Config if None)
        """
        self.config = config or Config()
        self.client = None
        self.sheet = None

        if self.config.GOOGLE_SHEETS_ENABLED:
            self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Sheets API"""
        try:
            # Define the required scopes
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            # Load credentials from service account file
            credentials_file = str(self.config.GOOGLE_CREDENTIALS_FILE)

            if not os.path.exists(credentials_file):
                print(f"[WARNING] Google credentials file not found: {credentials_file}")
                print("[INFO] Google Sheets integration disabled")
                self.config.GOOGLE_SHEETS_ENABLED = False
                return

            credentials = Credentials.from_service_account_file(
                credentials_file,
                scopes=scopes
            )

            # Create gspread client
            self.client = gspread.authorize(credentials)

            print("[INFO] Google Sheets authentication successful")

        except Exception as e:
            print(f"[ERROR] Google Sheets authentication failed: {e}")
            self.config.GOOGLE_SHEETS_ENABLED = False

    def get_or_create_sheet(self, sheet_name: str = "Attendance Records") -> Optional[gspread.Worksheet]:
        """
        Get or create a worksheet

        Args:
            sheet_name: Name of the worksheet

        Returns:
            Worksheet object or None if failed
        """
        if not self.config.GOOGLE_SHEETS_ENABLED or not self.client:
            return None

        try:
            # Open the spreadsheet by ID
            spreadsheet = self.client.open_by_key(self.config.GOOGLE_SHEET_ID)

            # Try to get existing worksheet
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                print(f"[INFO] Found existing worksheet: {sheet_name}")
            except gspread.exceptions.WorksheetNotFound:
                # Create new worksheet
                worksheet = spreadsheet.add_worksheet(
                    title=sheet_name,
                    rows=1000,
                    cols=10
                )
                print(f"[INFO] Created new worksheet: {sheet_name}")

                # Add headers
                headers = [
                    'Timestamp',
                    'Session Name',
                    'Course Code',
                    'Student ID',
                    'Student Name',
                    'Confidence Score',
                    'Status',
                    'Location',
                    'Instructor',
                    'Sync Time'
                ]
                worksheet.append_row(headers)

            return worksheet

        except Exception as e:
            print(f"[ERROR] Failed to get/create worksheet: {e}")
            return None

    def sync_attendance_record(self, record: AttendanceRecord) -> bool:
        """
        Sync a single attendance record to Google Sheets

        Args:
            record: AttendanceRecord object

        Returns:
            True if successful, False otherwise
        """
        if not self.config.GOOGLE_SHEETS_ENABLED:
            return False

        try:
            worksheet = self.get_or_create_sheet()
            if not worksheet:
                return False

            # Prepare row data
            row_data = [
                record.timestamp.isoformat() if record.timestamp else '',
                record.session.session_name if record.session else '',
                record.session.course_code if record.session else '',
                record.student.student_id if record.student else '',
                record.student.name if record.student else '',
                f"{record.confidence_score:.2f}" if record.confidence_score else '',
                record.status,
                record.session.location if record.session else '',
                record.session.instructor_name if record.session else '',
                datetime.utcnow().isoformat()
            ]

            # Append to sheet
            worksheet.append_row(row_data)

            # Mark as synced in database
            DatabaseManager.mark_as_synced(record.id)

            print(f"[INFO] Synced record {record.id} to Google Sheets")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to sync record {record.id}: {e}")
            return False

    def sync_batch(self, records: List[AttendanceRecord]) -> Dict[str, int]:
        """
        Sync multiple attendance records in batch

        Args:
            records: List of AttendanceRecord objects

        Returns:
            Dictionary with success and failure counts
        """
        if not self.config.GOOGLE_SHEETS_ENABLED:
            return {'success': 0, 'failed': 0}

        stats = {'success': 0, 'failed': 0}

        try:
            worksheet = self.get_or_create_sheet()
            if not worksheet:
                return stats

            # Prepare batch data
            rows = []
            for record in records:
                row_data = [
                    record.timestamp.isoformat() if record.timestamp else '',
                    record.session.session_name if record.session else '',
                    record.session.course_code if record.session else '',
                    record.student.student_id if record.student else '',
                    record.student.name if record.student else '',
                    f"{record.confidence_score:.2f}" if record.confidence_score else '',
                    record.status,
                    record.session.location if record.session else '',
                    record.session.instructor_name if record.session else '',
                    datetime.utcnow().isoformat()
                ]
                rows.append(row_data)

            # Batch append to sheet
            if rows:
                worksheet.append_rows(rows)

                # Mark all as synced
                for record in records:
                    DatabaseManager.mark_as_synced(record.id)
                    stats['success'] += 1

            print(f"[INFO] Batch synced {stats['success']} records to Google Sheets")

        except Exception as e:
            print(f"[ERROR] Batch sync failed: {e}")
            stats['failed'] = len(records) - stats['success']

        return stats

    def sync_unsynced_records(self, limit: int = 100) -> Dict[str, int]:
        """
        Sync all unsynced records from database

        Args:
            limit: Maximum number of records to sync

        Returns:
            Dictionary with statistics
        """
        if not self.config.GOOGLE_SHEETS_ENABLED:
            print("[INFO] Google Sheets sync disabled")
            return {'success': 0, 'failed': 0}

        print("[INFO] Starting sync of unsynced records...")

        # Get unsynced records
        unsynced = DatabaseManager.get_unsynced_records()

        if not unsynced:
            print("[INFO] No unsynced records found")
            return {'success': 0, 'failed': 0}

        # Limit the number of records
        records_to_sync = unsynced[:limit]

        print(f"[INFO] Found {len(unsynced)} unsynced records, syncing {len(records_to_sync)}...")

        # Sync in batch
        stats = self.sync_batch(records_to_sync)

        print(f"[INFO] Sync complete: {stats['success']} succeeded, {stats['failed']} failed")

        return stats

    def export_session_to_sheet(self, session_id: int, sheet_name: Optional[str] = None) -> bool:
        """
        Export entire session attendance to a new sheet

        Args:
            session_id: Session ID to export
            sheet_name: Optional custom sheet name

        Returns:
            True if successful, False otherwise
        """
        if not self.config.GOOGLE_SHEETS_ENABLED:
            return False

        try:
            # Get session and records
            session = DatabaseManager.get_session_by_id(session_id)
            if not session:
                print(f"[ERROR] Session {session_id} not found")
                return False

            records = DatabaseManager.get_session_attendance(session_id)
            if not records:
                print(f"[WARNING] No attendance records for session {session_id}")
                return False

            # Generate sheet name
            if not sheet_name:
                sheet_name = f"{session.session_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Get or create worksheet
            worksheet = self.get_or_create_sheet(sheet_name)
            if not worksheet:
                return False

            # Sync all records
            stats = self.sync_batch(records)

            print(f"[INFO] Exported session {session_id} to sheet '{sheet_name}'")
            print(f"[INFO] Records: {stats['success']} succeeded, {stats['failed']} failed")

            return stats['failed'] == 0

        except Exception as e:
            print(f"[ERROR] Failed to export session: {e}")
            return False

if __name__ == "__main__":
    # Test the service
    from app import create_app

    app = create_app()

    with app.app_context():
        service = GoogleSheetsService()

        if service.config.GOOGLE_SHEETS_ENABLED:
            # Sync unsynced records
            stats = service.sync_unsynced_records()
            print(f"\nSync statistics: {stats}")
        else:
            print("\nGoogle Sheets integration is disabled")
            print("To enable:")
            print("1. Set GOOGLE_SHEETS_ENABLED=true in .env")
            print("2. Place credentials.json in project root")
            print("3. Set GOOGLE_SHEET_ID in .env")
