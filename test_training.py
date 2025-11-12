import pickle
with open("insightface_encodings.pkl", "rb") as f:
    data = pickle.load(f)
print(f"Embeddings: {len(data['embeddings'])}")
print(f"Names: {data['names']}")
