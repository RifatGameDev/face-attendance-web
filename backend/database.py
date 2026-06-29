import os
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Please add DATABASE_URL inside .env file.")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "connect_timeout": 10
    }
)


def test_database_connection():
    with engine.connect() as conn:
        result = conn.execute(text("select now();"))
        return str(result.scalar())


def create_employee(name: str):
    query = text("""
        insert into employees (name, is_face_registered)
        values (:name, false)
        returning employee_id, name, is_face_registered;
    """)

    with engine.begin() as conn:
        result = conn.execute(query, {
            "name": name
        }).mappings().first()

        return dict(result)


def get_employee_by_id(employee_id: str):
    query = text("""
        select employee_id, name, is_face_registered
        from employees
        where employee_id = :employee_id;
    """)

    with engine.begin() as conn:
        result = conn.execute(query, {
            "employee_id": employee_id
        }).mappings().first()

        if not result:
            return None

        return dict(result)


def save_employee_face_pose_embedding(employee_id: str, pose: str, face_embedding: list):
    """
    Save FRONT / LEFT / RIGHT face embedding for an employee.
    If the same pose already exists, update it.
    """

    insert_query = text("""
        insert into employee_face_embeddings (employee_id, pose, face_embedding)
        values (:employee_id, :pose, cast(:face_embedding as jsonb))
        on conflict (employee_id, pose)
        do update set
            face_embedding = excluded.face_embedding
        returning employee_id, pose;
    """)

    count_query = text("""
        select count(distinct pose) as total_poses
        from employee_face_embeddings
        where employee_id = :employee_id;
    """)

    update_employee_query = text("""
        update employees
        set
            is_face_registered = true,
            updated_at = now()
        where employee_id = :employee_id
        returning employee_id, name, is_face_registered;
    """)

    get_employee_query = text("""
        select employee_id, name, is_face_registered
        from employees
        where employee_id = :employee_id;
    """)

    with engine.begin() as conn:
        conn.execute(insert_query, {
            "employee_id": employee_id,
            "pose": pose,
            "face_embedding": json.dumps(face_embedding)
        })

        pose_count_result = conn.execute(count_query, {
            "employee_id": employee_id
        }).mappings().first()

        total_poses = pose_count_result["total_poses"]

        if total_poses >= 3:
            employee_result = conn.execute(update_employee_query, {
                "employee_id": employee_id
            }).mappings().first()
        else:
            employee_result = conn.execute(get_employee_query, {
                "employee_id": employee_id
            }).mappings().first()

        return {
            "employee": dict(employee_result),
            "registered_pose_count": total_poses,
            "is_registration_complete": total_poses >= 3
        }


def get_registered_face_poses(employee_id: str):
    query = text("""
        select pose
        from employee_face_embeddings
        where employee_id = :employee_id;
    """)

    with engine.begin() as conn:
        result = conn.execute(query, {
            "employee_id": employee_id
        }).mappings().all()

        return [row["pose"] for row in result]


def get_employee_face_embeddings(employee_id: str):
    query = text("""
        select pose, face_embedding
        from employee_face_embeddings
        where employee_id = :employee_id;
    """)

    with engine.begin() as conn:
        result = conn.execute(query, {
            "employee_id": employee_id
        }).mappings().all()

        embeddings = []

        for row in result:
            face_embedding = row["face_embedding"]

            # Supabase jsonb usually returns list, but this handles string too
            if isinstance(face_embedding, str):
                face_embedding = json.loads(face_embedding)

            embeddings.append({
                "pose": row["pose"],
                "face_embedding": face_embedding
            })

        return embeddings


def get_all_registered_face_embeddings():
    query = text("""
        select
            e.employee_id,
            e.name,
            f.pose,
            f.face_embedding
        from employees e
        join employee_face_embeddings f
            on e.employee_id = f.employee_id
        where e.is_face_registered = true;
    """)

    with engine.begin() as conn:
        result = conn.execute(query).mappings().all()

        embeddings = []

        for row in result:
            face_embedding = row["face_embedding"]

            if isinstance(face_embedding, str):
                face_embedding = json.loads(face_embedding)

            embeddings.append({
                "employee_id": row["employee_id"],
                "name": row["name"],
                "pose": row["pose"],
                "face_embedding": face_embedding
            })

        return embeddings
