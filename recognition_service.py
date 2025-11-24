"""
Face Recognition Service with Database Integration
Refactored recognition engine that uses database instead of pickle files
"""
import os
# Set headless mode for OpenCV before importing cv2
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import cv2
import numpy as np
from picamera2 import Picamera2
from insightface.app import FaceAnalysis
import time
from datetime import datetime
from typing import Optional, Tuple, List
from config import Config
from database import DatabaseManager
from flask import Flask
import threading

class FaceRecognitionService:
    """Face recognition service with real-time detection and database integration"""

    def __init__(self, config: Config = None, flask_app: Optional[Flask] = None):
        """
        Initialize face recognition service

        Args:
            config: Configuration object (uses default Config if None)
            flask_app: Flask application instance (creates one if None)
        """
        self.config = config or Config()

        # Initialize or use provided Flask app
        if flask_app is None:
            from app import create_app
            self.app_context = create_app().app_context()
            self.app_context.push()
        else:
            self.app_context = None

        # Initialize InsightFace
        print("[INFO] Initializing InsightFace...")
        self.app = FaceAnalysis(providers=[self.config.EXECUTION_PROVIDER])
        self.app.prepare(ctx_id=0, det_size=self.config.INSIGHTFACE_DET_SIZE)

        # Initialize camera
        print("[INFO] Initializing camera...")
        self.picam2 = Picamera2()
        camera_config = self.picam2.create_preview_configuration(
            main={"format": 'XRGB8888',
                  "size": (self.config.CAMERA_WIDTH, self.config.CAMERA_HEIGHT)}
        )
        self.picam2.configure(camera_config)

        # Load face encodings from database
        self.known_encodings = []
        self.known_names = []
        self.known_ids = []  # Database IDs
        self.load_encodings_from_db()

        # FPS tracking
        self.frame_count = 0
        self.start_time = time.time()
        self.fps = 0

        # Frame processing optimization
        self.process_every = self.config.PROCESS_EVERY_N_FRAMES
        self.frame_counter = 0
        self.last_faces = []

        # Camera started flag
        self.camera_started = False

        # Streaming control flags (thread-safe)
        self._streaming_lock = threading.Lock()
        self._recognition_streaming = False
        self._enrollment_streaming = False

    def load_encodings_from_db(self):
        """Load face encodings from database"""
        print("[INFO] Loading face encodings from database...")
        encodings_list = DatabaseManager.get_all_face_encodings(active_only=True)

        self.known_encodings = []
        self.known_names = []
        self.known_ids = []

        for name, encoding, student_id in encodings_list:
            self.known_encodings.append(encoding)
            self.known_names.append(name)
            self.known_ids.append(student_id)

        print(f"[INFO] Loaded {len(self.known_encodings)} face encodings")
        print(f"[INFO] Registered students: {set(self.known_names)}")

    def start_camera(self):
        """Start the camera"""
        if not self.camera_started:
            self.picam2.start()
            time.sleep(2)  # Camera warm-up
            self.camera_started = True
            print("[INFO] Camera started")

    def stop_camera(self):
        """Stop the camera"""
        if self.camera_started:
            self.picam2.stop()
            self.camera_started = False
            print("[INFO] Camera stopped")

    def start_recognition_stream(self):
        """Signal that recognition streaming should start"""
        with self._streaming_lock:
            self._recognition_streaming = True
            print("[INFO] Recognition streaming flag set to True")

    def stop_recognition_stream(self):
        """Signal that recognition streaming should stop"""
        with self._streaming_lock:
            self._recognition_streaming = False
            print("[INFO] Recognition streaming flag set to False")

    def is_recognition_streaming(self):
        """Check if recognition streaming is active"""
        with self._streaming_lock:
            return self._recognition_streaming

    def start_enrollment_stream(self):
        """Signal that enrollment streaming should start"""
        with self._streaming_lock:
            self._enrollment_streaming = True
            print("[INFO] Enrollment streaming flag set to True")

    def stop_enrollment_stream(self):
        """Signal that enrollment streaming should stop"""
        with self._streaming_lock:
            self._enrollment_streaming = False
            print("[INFO] Enrollment streaming flag set to False")

    def is_enrollment_streaming(self):
        """Check if enrollment streaming is active"""
        with self._streaming_lock:
            return self._enrollment_streaming

    def recognize_face(self, embedding: np.ndarray) -> Tuple[str, float, Optional[int]]:
        """
        Compare embedding with known faces

        Args:
            embedding: Face embedding to compare

        Returns:
            Tuple of (name, distance, student_db_id)
        """
        if len(self.known_encodings) == 0:
            return "Unknown", 1.0, None

        # Calculate L2 distances (Euclidean norm)
        distances = np.linalg.norm(
            np.array(self.known_encodings) - embedding, axis=1
        )
        min_distance_idx = np.argmin(distances)
        min_distance = distances[min_distance_idx]

        # Check against threshold
        if min_distance < self.config.RECOGNITION_THRESHOLD:
            return (
                self.known_names[min_distance_idx],
                min_distance,
                self.known_ids[min_distance_idx]
            )
        else:
            return "Unknown", min_distance, None

    def capture_frame(self) -> np.ndarray:
        """Capture a single frame from the camera"""
        if not self.camera_started:
            self.start_camera()

        try:
            # Capture the latest frame
            frame = self.picam2.capture_array()

            if frame is None:
                print("[WARNING] Camera returned None frame")
                return None

            # Convert to BGR for OpenCV
            return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"[ERROR] Failed to capture frame: {e}")
            return None

    def process_frame(self, frame: np.ndarray,
                     detect_faces: bool = True) -> Tuple[np.ndarray, List[dict]]:
        """
        Process a frame and detect/recognize faces

        Args:
            frame: Input frame (BGR format)
            detect_faces: Whether to detect faces in this frame

        Returns:
            Tuple of (annotated_frame, detections_list)
            detections_list contains dicts with keys: name, distance, bbox, student_db_id
        """
        detections = []

        # Only detect faces every N frames for performance
        if detect_faces and self.frame_counter % self.process_every == 0:
            self.last_faces = self.app.get(frame)

        self.frame_counter += 1

        # Process detected faces
        for face in self.last_faces:
            # Get bounding box
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox

            # Get embedding and recognize
            embedding = face.embedding
            name, distance, student_db_id = self.recognize_face(embedding)

            # Store detection
            detections.append({
                'name': name,
                'distance': distance,
                'bbox': (x1, y1, x2, y2),
                'student_db_id': student_db_id,
                'confidence_score': float(distance)
            })

            # Draw rectangle
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Draw label
            label = f"{name} (d:{distance:.2f})"
            cv2.rectangle(frame, (x1, y1 - 35), (x2, y1), color, cv2.FILLED)
            cv2.putText(frame, label, (x1 + 6, y1 - 6),
                       cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

        # Calculate and display FPS
        self.frame_count += 1
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 1:
            self.fps = self.frame_count / elapsed_time
            self.frame_count = 0
            self.start_time = time.time()

        # Display FPS
        cv2.putText(frame, f"FPS: {self.fps:.1f}",
                   (frame.shape[1] - 150, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Display threshold
        cv2.putText(frame, f"Threshold: {self.config.RECOGNITION_THRESHOLD}",
                   (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        return frame, detections

    def generate_frames(self, session_id: Optional[int] = None,
                       auto_mark_attendance: bool = True):
        """
        Generator function for video streaming
        Yields JPEG frames for Flask streaming response

        Args:
            session_id: Active session ID for attendance marking
            auto_mark_attendance: Whether to automatically mark attendance
        """
        self.start_camera()
        self.start_recognition_stream()

        # Track recent detections to prevent spam
        recent_detections = {}

        # Error recovery tracking
        consecutive_errors = 0
        max_consecutive_errors = 5

        while self.is_recognition_streaming():
            try:
                # Check flag at the start of each iteration
                if not self.is_recognition_streaming():
                    print("[INFO] Stream stop requested, breaking loop")
                    break

                # Capture frame with timeout protection
                frame = self.capture_frame()

                if frame is None or frame.size == 0:
                    print("[WARNING] Empty frame captured, skipping...")
                    time.sleep(0.1)
                    continue

                # Process frame
                annotated_frame, detections = self.process_frame(frame)

                # Auto-mark attendance if enabled and session is active
                if auto_mark_attendance and session_id and len(detections) > 0:
                    print(f"[DEBUG] Auto-mark enabled, session_id={session_id}, detections={len(detections)}")
                    for detection in detections:
                        print(f"[DEBUG] Detection: name={detection['name']}, db_id={detection['student_db_id']}, distance={detection['distance']:.3f}")
                        if detection['name'] != "Unknown" and detection['student_db_id']:
                            student_db_id = detection['student_db_id']

                            # Check if we've recently marked this student
                            last_marked = recent_detections.get(student_db_id)
                            now = datetime.utcnow()

                            if not last_marked or \
                               (now - last_marked).total_seconds() > 30:  # 30 second local cooldown
                                print(f"[DEBUG] Attempting to mark attendance for student_db_id={student_db_id}")
                                # Mark attendance
                                try:
                                    record = DatabaseManager.mark_attendance(
                                        session_id=session_id,
                                        student_db_id=student_db_id,
                                        confidence_score=detection['confidence_score'],
                                        cooldown_minutes=self.config.ATTENDANCE_COOLDOWN_MINUTES
                                    )

                                    if record:
                                        recent_detections[student_db_id] = now
                                        print(f"[INFO] ✓ Attendance marked: {detection['name']} "
                                              f"(confidence: {detection['confidence_score']:.2f})")
                                    else:
                                        print(f"[INFO] Attendance already marked recently for {detection['name']}")
                                except Exception as db_error:
                                    print(f"[ERROR] Database error marking attendance: {db_error}")
                                    import traceback
                                    traceback.print_exc()
                                    # Continue streaming even if DB fails
                            else:
                                time_since_last = (now - last_marked).total_seconds()
                                print(f"[DEBUG] Skipping {detection['name']} - marked {time_since_last:.0f}s ago")
                else:
                    if not auto_mark_attendance:
                        print("[DEBUG] Auto-mark disabled")
                    if not session_id:
                        print("[DEBUG] No active session")

                # Encode frame as JPEG with quality setting
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
                ret, buffer = cv2.imencode('.jpg', annotated_frame, encode_params)

                if not ret:
                    print("[WARNING] Failed to encode frame")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print("[ERROR] Too many encoding failures, stopping stream")
                        break
                    continue

                frame_bytes = buffer.tobytes()

                # Reset error counter on success
                consecutive_errors = 0

                # Check flag before yielding
                if not self.is_recognition_streaming():
                    print("[INFO] Stream stop requested before yield, breaking")
                    break

                # Yield frame in multipart format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                # Check flag after yield (in case it was set while we were blocked)
                if not self.is_recognition_streaming():
                    print("[INFO] Stream stop requested after yield, breaking")
                    break

                # Small delay to prevent overwhelming the client
                time.sleep(0.033)  # ~30 FPS

            except GeneratorExit:
                # Client disconnected
                print("[INFO] Client disconnected from stream")
                self.stop_recognition_stream()
                break
            except Exception as e:
                print(f"[ERROR] Frame generation error: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print("[ERROR] Too many consecutive errors, stopping stream")
                    self.stop_recognition_stream()
                    break
                time.sleep(0.1)  # Brief pause before retry
                continue

        # Cleanup on exit
        print("[INFO] Recognition stream ended, cleaning up...")
        self.stop_recognition_stream()
        self.stop_camera()

    def run_recognition_loop(self, session_id: Optional[int] = None,
                           auto_mark_attendance: bool = True,
                           display: bool = True):
        """
        Run continuous recognition loop

        Args:
            session_id: Active session ID for attendance marking
            auto_mark_attendance: Whether to automatically mark attendance
            display: Whether to display the video feed (deprecated for headless mode)
        """
        self.start_camera()
        print("[INFO] Starting recognition loop... Press 'q' to quit")

        # Track recent detections to prevent spam
        recent_detections = {}

        try:
            while True:
                # Capture frame
                frame = self.capture_frame()

                # Process frame
                annotated_frame, detections = self.process_frame(frame)

                # Auto-mark attendance if enabled and session is active
                if auto_mark_attendance and session_id:
                    for detection in detections:
                        if detection['name'] != "Unknown" and detection['student_db_id']:
                            student_db_id = detection['student_db_id']

                            # Check if we've recently marked this student
                            last_marked = recent_detections.get(student_db_id)
                            now = datetime.utcnow()

                            if not last_marked or \
                               (now - last_marked).total_seconds() > 30:  # 30 second local cooldown
                                # Mark attendance
                                record = DatabaseManager.mark_attendance(
                                    session_id=session_id,
                                    student_db_id=student_db_id,
                                    confidence_score=detection['confidence_score'],
                                    cooldown_minutes=self.config.ATTENDANCE_COOLDOWN_MINUTES
                                )

                                if record:
                                    recent_detections[student_db_id] = now
                                    print(f"[INFO] Attendance marked: {detection['name']} "
                                          f"(confidence: {detection['confidence_score']:.2f})")

                # Display is disabled for headless Raspberry Pi
                # Use web interface instead
                time.sleep(0.03)  # ~30 FPS

        finally:
            self.stop_camera()

    def capture_enrollment_photo(self, person_name: str,
                                 save_path: str) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Capture photo for enrollment

        Args:
            person_name: Name of the person
            save_path: Path to save the image

        Returns:
            Tuple of (success, embedding)
        """
        self.start_camera()

        try:
            # Capture frame
            frame = self.capture_frame()

            # Detect faces
            faces = self.app.get(frame)

            if len(faces) == 0:
                print("[WARNING] No face detected")
                return False, None

            if len(faces) > 1:
                print("[WARNING] Multiple faces detected, using first face")

            # Use first detected face
            face = faces[0]
            embedding = face.embedding

            # Draw bounding box
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, person_name, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

            # Save image
            cv2.imwrite(save_path, frame)
            print(f"[INFO] Photo saved: {save_path}")

            return True, embedding

        except Exception as e:
            print(f"[ERROR] Failed to capture photo: {e}")
            return False, None

    def capture_enrollment_photo_with_quality(self, person_name: str,
                                              save_path: str) -> Tuple[bool, Optional[np.ndarray], float]:
        """
        Capture photo for enrollment with quality assessment

        Args:
            person_name: Name of the person
            save_path: Path to save the image

        Returns:
            Tuple of (success, embedding, quality_score)
        """
        self.start_camera()

        try:
            # Capture frame
            frame = self.capture_frame()

            if frame is None:
                print("[ERROR] Failed to capture frame")
                return False, None, 0.0

            # Detect faces
            faces = self.app.get(frame)

            if len(faces) == 0:
                print("[WARNING] No face detected")
                return False, None, 0.0

            if len(faces) > 1:
                print("[WARNING] Multiple faces detected, using largest face")
                # Use the largest face (by bounding box area)
                faces = sorted(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)

            # Use first/largest detected face
            face = faces[0]
            embedding = face.embedding

            # Calculate quality score based on detection score and face size
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox
            face_area = (x2 - x1) * (y2 - y1)
            frame_area = frame.shape[0] * frame.shape[1]
            size_ratio = face_area / frame_area

            # Quality score: combination of detection score and size
            # Good if face is between 5% and 40% of frame
            size_quality = min(1.0, max(0.0, (size_ratio - 0.05) / 0.35))
            detection_score = float(face.det_score) if hasattr(face, 'det_score') else 0.9
            quality_score = (size_quality * 0.5 + detection_score * 0.5)

            # Draw bounding box with quality indicator
            color = (0, 255, 0) if quality_score > 0.7 else (0, 165, 255) if quality_score > 0.5 else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Draw label with quality
            label = f"{person_name} (Q: {quality_score:.2f})"
            cv2.rectangle(frame, (x1, y1 - 35), (x2, y1), color, cv2.FILLED)
            cv2.putText(frame, label, (x1 + 6, y1 - 6),
                       cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

            # Save image
            cv2.imwrite(save_path, frame)
            print(f"[INFO] Photo saved: {save_path} (Quality: {quality_score:.2f})")

            return True, embedding, quality_score

        except Exception as e:
            print(f"[ERROR] Failed to capture photo: {e}")
            import traceback
            traceback.print_exc()
            return False, None, 0.0

    def generate_enrollment_preview(self):
        """
        Generator function for enrollment preview streaming
        Shows live camera feed with face detection for enrollment purposes
        Yields JPEG frames for Flask streaming response
        """
        self.start_camera()
        self.start_enrollment_stream()
        print("[INFO] Starting enrollment preview stream...")

        # Error recovery tracking
        consecutive_errors = 0
        max_consecutive_errors = 5

        try:
            while self.is_enrollment_streaming():
                try:
                    # Capture frame
                    frame = self.capture_frame()

                    if frame is None or frame.size == 0:
                        print("[WARNING] Empty frame captured, skipping...")
                        time.sleep(0.1)
                        continue

                    # Detect faces
                    faces = self.app.get(frame)

                    # Process detected faces with quality overlay
                    for face in faces:
                        bbox = face.bbox.astype(int)
                        x1, y1, x2, y2 = bbox

                        # Calculate quality metrics
                        face_area = (x2 - x1) * (y2 - y1)
                        frame_area = frame.shape[0] * frame.shape[1]
                        size_ratio = face_area / frame_area

                        size_quality = min(1.0, max(0.0, (size_ratio - 0.05) / 0.35))
                        detection_score = float(face.det_score) if hasattr(face, 'det_score') else 0.9
                        quality_score = (size_quality * 0.5 + detection_score * 0.5)

                        # Color based on quality
                        if quality_score > 0.7:
                            color = (0, 255, 0)  # Green - Good
                            quality_text = "GOOD"
                        elif quality_score > 0.5:
                            color = (0, 165, 255)  # Orange - OK
                            quality_text = "OK"
                        else:
                            color = (0, 0, 255)  # Red - Poor
                            quality_text = "POOR"

                        # Draw rectangle
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                        # Draw quality label
                        label = f"{quality_text} ({quality_score:.2f})"
                        cv2.rectangle(frame, (x1, y1 - 35), (x2, y1), color, cv2.FILLED)
                        cv2.putText(frame, label, (x1 + 6, y1 - 6),
                                   cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

                    # Add instructions
                    instruction_text = "Position your face in the frame"
                    cv2.putText(frame, instruction_text, (10, frame.shape[0] - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                    # Add face count
                    face_count_text = f"Faces detected: {len(faces)}"
                    cv2.putText(frame, face_count_text, (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                    # Encode frame as JPEG
                    encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
                    ret, buffer = cv2.imencode('.jpg', frame, encode_params)

                    if not ret:
                        print("[WARNING] Failed to encode frame")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            print("[ERROR] Too many encoding failures, stopping stream")
                            break
                        continue

                    frame_bytes = buffer.tobytes()

                    # Reset error counter on success
                    consecutive_errors = 0

                    # Yield frame in multipart format
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                    # Control frame rate
                    time.sleep(0.033)  # ~30 FPS

                except GeneratorExit:
                    print("[INFO] Client disconnected from enrollment preview")
                    self.stop_enrollment_stream()
                    break
                except Exception as e:
                    print(f"[ERROR] Frame generation error: {e}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print("[ERROR] Too many consecutive errors, stopping stream")
                        self.stop_enrollment_stream()
                        break
                    time.sleep(0.1)
                    continue

        finally:
            print("[INFO] Enrollment preview stream ended, cleaning up...")
            self.stop_enrollment_stream()
            self.stop_camera()

    def cleanup(self):
        """Cleanup resources"""
        self.stop_camera()
        cv2.destroyAllWindows()
        # Pop app context if we created one
        if self.app_context:
            self.app_context.pop()

if __name__ == "__main__":
    # Test the service
    service = FaceRecognitionService()

    # Check for active session
    active_session = DatabaseManager.get_active_session()

    if active_session:
        print(f"[INFO] Active session: {active_session.session_name}")
        service.run_recognition_loop(
            session_id=active_session.id,
            auto_mark_attendance=True,
            display=True
        )
    else:
        print("[WARNING] No active session. Running in recognition-only mode.")
        service.run_recognition_loop(
            session_id=None,
            auto_mark_attendance=False,
            display=True
        )
