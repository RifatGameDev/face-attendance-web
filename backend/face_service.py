# from deepface import DeepFace
import tempfile
import numpy as np
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"


MODEL_NAME = "Facenet"


def extract_face_embedding(image_bytes: bytes) -> list:
    from deepface import DeepFace
    """
    Receives image bytes from frontend/API,
    saves image temporarily,
    extracts face embedding using DeepFace,
    then deletes the temporary image.
    """

    temp_path = None

    try:
        # Create temporary file path
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)

        # Write image bytes into temp file
        with open(temp_path, "wb") as f:
            f.write(image_bytes)

        # Extract face embedding
        result = DeepFace.represent(
            img_path=temp_path,
            model_name=MODEL_NAME,
            enforce_detection=True
        )

        if not result:
            raise ValueError("No face detected in the image.")

        embedding = result[0]["embedding"]
        return embedding

    finally:
        # Delete temporary file after processing
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def cosine_similarity(embedding1: list, embedding2: list) -> float:
    vec1 = np.array(embedding1, dtype=np.float32)
    vec2 = np.array(embedding2, dtype=np.float32)

    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = np.dot(vec1, vec2) / (norm1 * norm2)

    return float(similarity)


def verify_face_against_saved_embeddings(
    live_embedding: list,
    saved_embeddings: list,
    threshold: float = 0.85
):
    best_score = -1
    best_pose = None

    for item in saved_embeddings:
        pose = item["pose"]
        saved_embedding = item["face_embedding"]

        score = cosine_similarity(live_embedding, saved_embedding)

        if score > best_score:
            best_score = score
            best_pose = pose

    matched = best_score >= threshold

    return {
        "matched": matched,
        "best_score": round(best_score, 4),
        "best_pose": best_pose,
        "threshold": threshold
    }


def identify_face_from_saved_embeddings(
    live_embedding: list,
    saved_embeddings: list,
    threshold: float = 0.85
):
    best_score = -1
    best_match = None

    for item in saved_embeddings:
        score = cosine_similarity(live_embedding, item["face_embedding"])

        if score > best_score:
            best_score = score
            best_match = item

    if best_match and best_score >= threshold:
        return {
            "matched": True,
            "employee_id": best_match["employee_id"],
            "name": best_match["name"],
            "best_pose": best_match["pose"],
            "best_score": round(best_score, 4),
            "threshold": threshold
        }

    return {
        "matched": False,
        "employee_id": None,
        "name": None,
        "best_pose": best_match["pose"] if best_match else None,
        "best_score": round(best_score, 4),
        "threshold": threshold
    }
