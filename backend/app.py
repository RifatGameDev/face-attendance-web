import os
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fastapi import FastAPI, Form, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from face_service import (
    extract_face_embedding,
    verify_face_against_saved_embeddings,
    identify_face_from_saved_embeddings
)


from database import (
    test_database_connection,
    create_employee,
    get_employee_by_id,
    save_employee_face_pose_embedding,
    get_registered_face_poses,
    get_employee_face_embeddings,
    get_all_registered_face_embeddings
)


app = FastAPI(title="Face Attendance Web API")

FRONTEND_DIR = os.path.join(os.path.dirname(
    os.path.dirname(__file__)), "frontend")

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/health")
def health_check():
    return {
        "success": True,
        "status": "healthy"
    }


@app.get("/db-test")
def db_test():
    try:
        db_time = test_database_connection()

        return {
            "success": True,
            "message": "Database connected successfully",
            "database_time": db_time
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(e)}"
        )


@app.post("/register-user")
def register_user(
    name: str = Form(...)
):
    try:
        employee = create_employee(name)

        return {
            "success": True,
            "message": "User created successfully. Face is not registered yet.",
            "employee": employee
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"User registration failed: {str(e)}"
        )


@app.get("/employee/{employee_id}")
def get_employee(employee_id: str):
    employee = get_employee_by_id(employee_id)

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    return {
        "success": True,
        "employee": employee
    }


@app.post("/test-face-embedding")
async def test_face_embedding(
    image: UploadFile = File(...)
):
    try:
        image_bytes = await image.read()

        embedding = extract_face_embedding(image_bytes)

        return {
            "success": True,
            "message": "Face embedding extracted successfully",
            "embedding_length": len(embedding)
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Face embedding test failed: {str(e)}"
        )


@app.post("/register-face-pose")
async def register_face_pose(
    employee_id: str = Form(...),
    pose: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        allowed_poses = ["FRONT", "LEFT", "RIGHT"]

        pose = pose.upper().strip()

        if pose not in allowed_poses:
            raise HTTPException(
                status_code=400,
                detail="Invalid pose. Pose must be FRONT, LEFT, or RIGHT."
            )

        employee = get_employee_by_id(employee_id)

        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Employee not found. Please register user first."
            )

        if employee["is_face_registered"]:
            raise HTTPException(
                status_code=400,
                detail="Face already fully registered. Please use verify face."
            )

        image_bytes = await image.read()

        face_embedding = extract_face_embedding(image_bytes)

        result = save_employee_face_pose_embedding(
            employee_id=employee_id,
            pose=pose,
            face_embedding=face_embedding
        )

        registered_poses = get_registered_face_poses(employee_id)

        missing_poses = [
            p for p in allowed_poses
            if p not in registered_poses
        ]

        return {
            "success": True,
            "message": f"{pose} face registered successfully",
            "employee": result["employee"],
            "registered_poses": registered_poses,
            "missing_poses": missing_poses,
            "registered_pose_count": result["registered_pose_count"],
            "is_registration_complete": result["is_registration_complete"]
        }

    except HTTPException:
        raise

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Face pose registration failed: {str(e)}"
        )


@app.post("/verify-face")
async def verify_face(
    employee_id: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        employee = get_employee_by_id(employee_id)

        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Employee not found."
            )

        if not employee["is_face_registered"]:
            raise HTTPException(
                status_code=400,
                detail="Face is not fully registered for this employee."
            )

        saved_embeddings = get_employee_face_embeddings(employee_id)

        if len(saved_embeddings) < 3:
            raise HTTPException(
                status_code=400,
                detail="Employee does not have all 3 face poses registered."
            )

        image_bytes = await image.read()

        live_embedding = extract_face_embedding(image_bytes)

        result = verify_face_against_saved_embeddings(
            live_embedding=live_embedding,
            saved_embeddings=saved_embeddings,
            threshold=0.85
        )

        if result["matched"]:
            return {
                "success": True,
                "matched": True,
                "message": "Face verified successfully",
                "employee": {
                    "employee_id": employee["employee_id"],
                    "name": employee["name"]
                },
                "best_pose": result["best_pose"],
                "score": result["best_score"],
                "threshold": result["threshold"]
            }

        return {
            "success": True,
            "matched": False,
            "message": "Face verification failed",
            "employee_id": employee["employee_id"],
            "best_pose": result["best_pose"],
            "score": result["best_score"],
            "threshold": result["threshold"]
        }

    except HTTPException:
        raise

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Face verification failed: {str(e)}"
        )


@app.post("/identify-face")
async def identify_face(
    image: UploadFile = File(...)
):
    try:
        saved_embeddings = get_all_registered_face_embeddings()

        if not saved_embeddings:
            return {
                "success": True,
                "matched": False,
                "message": "User not verified. Please register first."
            }

        image_bytes = await image.read()

        live_embedding = extract_face_embedding(image_bytes)

        result = identify_face_from_saved_embeddings(
            live_embedding=live_embedding,
            saved_embeddings=saved_embeddings,
            threshold=0.85
        )

        if result["matched"]:
            return {
                "success": True,
                "matched": True,
                "message": f"Hi {result['name']}, you have verified successfully.",
                "employee": {
                    "employee_id": result["employee_id"],
                    "name": result["name"]
                },
                "best_pose": result["best_pose"],
                "score": result["best_score"],
                "threshold": result["threshold"]
            }

        return {
            "success": True,
            "matched": False,
            "message": "User not verified. Please register first.",
            "best_pose": result["best_pose"],
            "score": result["best_score"],
            "threshold": result["threshold"]
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Face identification failed: {str(e)}"
        )


@app.get("/env-check")
def env_check():
    database_url = os.getenv("DATABASE_URL")

    return {
        "success": True,
        "database_url_loaded": bool(database_url),
        "database_url_preview": database_url[:35] if database_url else None,
        "has_pooler": "pooler.supabase.com" in database_url if database_url else False
    }
