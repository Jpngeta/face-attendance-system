import cv2
import numpy as np
import pickle
from picamera2 import Picamera2
from insightface.app import FaceAnalysis
import time

# Load embeddings
print("[INFO] Loading embeddings...")
with open("insightface_encodings.pkl", "rb") as f:
    data = pickle.load(f)

known_embeddings = np.array(data["embeddings"])
known_names = data["names"]

print(f"[INFO] Loaded {len(known_embeddings)} face embeddings")
print(f"[INFO] Names: {set(known_names)}")

# Initialize InsightFace with smaller detection size for speed
print("[INFO] Initializing InsightFace...")
app = FaceAnalysis(providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(320, 320))  # Reduced from 640 for speed

# Initialize camera with lower resolution
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
picam2.start()

time.sleep(2)

# FPS calculation
frame_count = 0
start_time = time.time()
fps = 0

# Recognition threshold - ADJUSTED (lower = stricter, higher = more lenient)
THRESHOLD = 20  # Increased from 0.4 - try this first

def recognize_face(embedding):
    """Compare embedding with known faces"""
    if len(known_embeddings) == 0:
        return "Unknown", 1.0
    
    # Calculate cosine distances (L2 norm)
    distances = np.linalg.norm(known_embeddings - embedding, axis=1)
    min_distance_idx = np.argmin(distances)
    min_distance = distances[min_distance_idx]
    
    print(f"[DEBUG] Min distance: {min_distance:.3f}, Name: {known_names[min_distance_idx]}")
    
    if min_distance < THRESHOLD:
        return known_names[min_distance_idx], min_distance
    else:
        return "Unknown", min_distance

print("[INFO] Starting recognition... Press 'q' to quit")

# Process every N frames for speed
process_every = 2
frame_counter = 0
last_faces = []

while True:
    # Capture frame
    frame = picam2.capture_array()
    
    # Convert to BGR for OpenCV
    display_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    
    # Only process every Nth frame
    if frame_counter % process_every == 0:
        # Detect faces
        last_faces = app.get(display_frame)
    
    frame_counter += 1
    
    # Draw results from last detection
    for face in last_faces:
        # Get bounding box
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox
        
        # Get embedding and recognize
        embedding = face.embedding
        name, distance = recognize_face(embedding)
        
        # Draw rectangle
        color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
        cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
        
        # Draw label
        label = f"{name} (d:{distance:.2f})"
        cv2.rectangle(display_frame, (x1, y1 - 35), (x2, y1), color, cv2.FILLED)
        cv2.putText(display_frame, label, (x1 + 6, y1 - 6), 
                    cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
    
    # Calculate FPS
    frame_count += 1
    elapsed_time = time.time() - start_time
    if elapsed_time > 1:
        fps = frame_count / elapsed_time
        frame_count = 0
        start_time = time.time()
    
    # Display FPS
    cv2.putText(display_frame, f"FPS: {fps:.1f}", (display_frame.shape[1] - 150, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    cv2.putText(display_frame, f"Threshold: {THRESHOLD}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    # Show frame
    cv2.imshow('InsightFace Recognition', display_frame)
    
    if cv2.waitKey(1) == ord('q'):
        break

cv2.destroyAllWindows()
picam2.stop()