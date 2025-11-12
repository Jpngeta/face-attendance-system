import os
import cv2
import numpy as np
import pickle
from insightface.app import FaceAnalysis

print("[INFO] Initializing InsightFace...")
app = FaceAnalysis(providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))

print("[INFO] Processing faces from dataset...")

known_embeddings = []
known_names = []

dataset_path = "insightface_dataset"

for person_name in os.listdir(dataset_path):
    person_folder = os.path.join(dataset_path, person_name)
    
    if not os.path.isdir(person_folder):
        continue
    
    print(f"[INFO] Processing {person_name}...")
    
    for image_name in os.listdir(person_folder):
        image_path = os.path.join(person_folder, image_name)
        
        # Read image
        img = cv2.imread(image_path)
        
        if img is None:
            print(f"[WARNING] Could not read {image_path}")
            continue
        
        # Detect faces and get embeddings
        faces = app.get(img)
        
        if len(faces) == 0:
            print(f"[WARNING] No face detected in {image_name}")
            continue
        
        # Use the first detected face
        face = faces[0]
        embedding = face.embedding
        
        known_embeddings.append(embedding)
        known_names.append(person_name)
        
        print(f"[INFO] Processed {image_name} - Face detected")

print(f"[INFO] Total faces processed: {len(known_embeddings)}")
print(f"[INFO] Unique people: {len(set(known_names))}")

# Save embeddings
data = {
    "embeddings": known_embeddings,
    "names": known_names
}

with open("insightface_encodings.pkl", "wb") as f:
    pickle.dump(data, f)

print("[INFO] Training complete! Embeddings saved to 'insightface_encodings.pkl'")