import cv2
import os
from datetime import datetime
from picamera2 import Picamera2
import time

# Change this to the person's name
PERSON_NAME = "elvin"

def create_folder(name):
    dataset_folder = "insightface_dataset"
    if not os.path.exists(dataset_folder):
        os.makedirs(dataset_folder)
    
    person_folder = os.path.join(dataset_folder, name)
    if not os.path.exists(person_folder):
        os.makedirs(person_folder)
    return person_folder

def capture_photos(name):
    folder = create_folder(name)
    
    # Initialize camera with lower resolution for better performance
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
    picam2.start()
    
    time.sleep(2)
    
    photo_count = 0
    print(f"Taking photos for {name}.")
    print("Press SPACE to capture, 'q' to quit.")
    print("TIP: Take photos from different angles and expressions!")
    
    while True:
        frame = picam2.capture_array()
        
        # Convert to BGR for OpenCV display
        display_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        cv2.putText(display_frame, f"Photos: {photo_count}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('Capture', display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord(' '):
            photo_count += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.jpg"
            filepath = os.path.join(folder, filename)
            cv2.imwrite(filepath, display_frame)
            print(f"Photo {photo_count} saved: {filepath}")
        
        elif key == ord('q'):
            break
    
    cv2.destroyAllWindows()
    picam2.stop()
    print(f"Capture complete! {photo_count} photos saved for {name}.")

if __name__ == "__main__":
    capture_photos(PERSON_NAME)