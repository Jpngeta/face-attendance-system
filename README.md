# Face Attendance System

A smart hybrid-edge facial recognition attendance system built for Raspberry Pi 5 using InsightFace, Flask, and SQLite.

## Features

- **Real-time Face Recognition**: Powered by InsightFace for accurate face detection and recognition
- **Live Video Streaming**: Browser-based live camera feed with real-time face detection overlay
- **Automatic Attendance Marking**: Face detection automatically marks attendance during active sessions
- **Database Management**: SQLite database for storing students, sessions, and attendance records
- **Web Dashboard**: Modern responsive web interface for managing attendance
- **REST API**: Full-featured API for programmatic access
- **Offline Capability**: Queue-based system for offline attendance marking with automatic sync
- **Google Sheets Integration**: Optional cloud sync to Google Sheets
- **Raspberry Pi Optimized**: Designed for Raspberry Pi 5 with Camera Module 3 in headless mode

## Hardware Requirements

- Raspberry Pi 5 (4GB+ RAM recommended)
- Raspberry Pi Camera Module 3
- MicroSD card (32GB+ recommended)
- Power supply (5V, 3A+)
- Heat sink and case

## Software Requirements

- Raspberry Pi OS (64-bit)
- Python 3.9+
- See [requirements.txt](requirements.txt) for Python dependencies

## Installation

### 1. Clone the Repository

```bash
cd /home/jpngeta
git clone <repository-url> face-attendance-system
cd face-attendance-system
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file and edit it:

```bash
cp .env.example .env
nano .env
```

Key configuration options:
- `DATABASE_URL`: Database connection string
- `SECRET_KEY`: Flask secret key (change in production!)
- `RECOGNITION_THRESHOLD`: Face recognition sensitivity (default: 20)
- `GOOGLE_SHEETS_ENABLED`: Enable/disable Google Sheets sync

### 5. Initialize Database

Run the migration script to set up the database and migrate existing data:

```bash
python migrate_to_database.py
```

This will:
- Create all database tables
- Migrate existing face encodings from `insightface_encodings.pkl` (if present)
- Import registered students

## Usage

### Starting the Web Application

```bash
python app.py
```

The dashboard will be available at: `http://localhost:5000`

### Registering New Students

**Option 1: Web Interface**
1. Go to `http://localhost:5000/register`
2. Fill in student details
3. Click "Register"

**Option 2: Command Line**
1. Update `PERSON_NAME` in `insightface_capture.py`
2. Run the capture script:
   ```bash
   python insightface_capture.py
   ```
3. Press SPACE to capture photos (recommended: 6-10 photos from different angles)
4. Press 'q' to quit
5. Train the model:
   ```bash
   python insightface_training.py
   ```
6. Re-run migration to update database:
   ```bash
   python migrate_to_database.py
   ```

### Running Face Recognition

**Recommended: Live Web Interface**:
1. Create a session in the web dashboard at `http://localhost:5000/sessions`
2. Navigate to Live Recognition at `http://localhost:5000/live`
3. The camera feed will start automatically with real-time face detection
4. Recognized students are automatically marked present
5. View real-time attendance updates in the side panel

**Alternative: Command Line (Headless Mode)**:
1. Create a session in the web dashboard
2. Start the recognition service:
   ```bash
   python recognition_service.py
   ```
3. Recognized students will be automatically marked present
4. Note: This runs without display, designed for headless Raspberry Pi

**Recognition Only (No Attendance Marking)**:
```bash
python insightface_recognition.py
```

## Project Structure

```
face-attendance-system/
├── app.py                      # Flask application entry point
├── config.py                   # Configuration management
├── models.py                   # Database models (SQLAlchemy)
├── database.py                 # Database helper functions
├── recognition_service.py      # Refactored recognition engine with DB
├── google_sheets_service.py    # Google Sheets integration
├── migrate_to_database.py      # Database migration script
│
├── routes/                     # Flask routes
│   ├── api.py                  # REST API endpoints
│   └── web.py                  # Web page routes
│
├── templates/                  # HTML templates
│   ├── base.html              # Base template
│   ├── index.html             # Dashboard
│   ├── live_recognition.html  # Live video feed with attendance
│   ├── students.html          # Students management
│   ├── sessions.html          # Sessions list
│   ├── session_detail.html    # Session details
│   ├── attendance.html        # Attendance records
│   └── register.html          # Student registration
│
├── static/                     # Static files
│   ├── css/style.css          # Custom CSS
│   └── js/main.js             # JavaScript
│
├── insightface_dataset/        # Training images
├── requirements.txt            # Python dependencies
├── .env.example               # Environment configuration template
└── README.md                  # This file

## Legacy Scripts (for reference)
├── insightface_capture.py     # Original photo capture script
├── insightface_training.py    # Original training script
└── insightface_recognition.py # Original recognition script
```

## API Endpoints

### Students
- `GET /api/students` - Get all students
- `GET /api/students/<student_id>` - Get specific student
- `POST /api/students` - Create new student
- `PUT /api/students/<student_id>` - Update student
- `DELETE /api/students/<student_id>` - Delete student

### Sessions
- `GET /api/sessions` - Get all sessions
- `GET /api/sessions/active` - Get active session
- `POST /api/sessions` - Create new session
- `POST /api/sessions/<id>/end` - End session

### Attendance
- `GET /api/attendance` - Get attendance records (with filters)
- `POST /api/attendance` - Mark attendance
- `GET /api/attendance/stats` - Get attendance statistics

### System
- `GET /api/status` - Get system status
- `GET /api/health` - Health check

### Live Recognition & Video Streaming
- `GET /api/recognition/stream` - MJPEG video stream with face detection overlay
- `GET /api/recognition/status` - Get recognition service status
- `POST /api/recognition/reload` - Reload face encodings from database

## Database Schema

### Students Table
- Student information (ID, name, email, program, etc.)
- Status tracking (active/inactive)

### Face Encodings Table
- Binary storage of face embeddings
- Linked to students
- Quality scores and image paths

### Attendance Sessions Table
- Class/session information
- Course details and instructor
- Start/end times and status

### Attendance Records Table
- Individual attendance entries
- Timestamp and confidence scores
- Sync status for cloud integration

### Sync Queue Table
- Offline data queue
- Retry mechanism for failed syncs

## Google Sheets Integration

### Setup

1. Create a Google Cloud Project
2. Enable Google Sheets API and Google Drive API
3. Create a Service Account and download credentials JSON
4. Place credentials file as `credentials.json` in project root
5. Create a Google Sheet and share it with the service account email
6. Copy the Sheet ID from the URL
7. Update `.env`:
   ```
   GOOGLE_SHEETS_ENABLED=true
   GOOGLE_CREDENTIALS_FILE=credentials.json
   GOOGLE_SHEET_ID=your-sheet-id-here
   ```

### Manual Sync

```bash
python google_sheets_service.py
```

## Configuration

### Recognition Settings

Edit in `.env` or `config.py`:

- `RECOGNITION_THRESHOLD`: Distance threshold for face matching (lower = stricter, higher = more lenient)
- `DETECTION_SIZE`: Detection model size (320 for speed, 640 for accuracy)
- `PROCESS_EVERY_N_FRAMES`: Process every Nth frame (higher = faster but less responsive)
- `ATTENDANCE_COOLDOWN_MINUTES`: Prevent duplicate attendance within N minutes

### Camera Settings

- `CAMERA_WIDTH`: Camera resolution width (default: 640)
- `CAMERA_HEIGHT`: Camera resolution height (default: 480)
- `CAMERA_FPS`: Camera frame rate (default: 30)

## Troubleshooting

### Face Recognition Not Working
- Check camera connection: `libcamera-hello`
- Verify InsightFace installation: `python -c "from insightface.app import FaceAnalysis"`
- Lower DETECTION_SIZE for better performance
- Increase RECOGNITION_THRESHOLD if too strict

### Video Stream Not Loading in Browser
- Check Flask app is running: `http://localhost:5000/api/health`
- Verify camera is not in use by another process
- Check browser console for errors
- Try refreshing the page or restarting Flask app

### "Working outside of application context" Error
- This is now fixed automatically
- The recognition service creates its own Flask app context when run standalone
- If issues persist, restart the Flask application

### Database Errors
- Delete `attendance.db` and re-run `migrate_to_database.py`
- Check file permissions

### Google Sheets Sync Fails
- Verify credentials.json exists
- Check service account has access to the sheet
- Verify GOOGLE_SHEET_ID is correct

### Performance Issues
- Increase `PROCESS_EVERY_N_FRAMES`
- Lower camera resolution
- Reduce `DETECTION_SIZE` to 320
- Close other browser tabs to reduce CPU load

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
```

## Migration from Legacy System

If you have existing pickle-based encodings:

1. Keep `insightface_encodings.pkl` in place
2. Run `python migrate_to_database.py`
3. Verify data in database
4. Legacy scripts will continue to work alongside new system

## Future Enhancements

- [ ] User authentication and role-based access
- [ ] Email notifications for attendance
- [ ] Advanced reporting and analytics
- [ ] Mobile app integration
- [ ] Multi-camera support
- [ ] Docker deployment
- [ ] Automated testing suite

## License

[Your License Here]

## Contributors

[Your Name]

## Acknowledgments

- InsightFace for face recognition models
- Flask for web framework
- Bootstrap for UI components
- Raspberry Pi Foundation
