from datetime import datetime
from typing import List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..core.db import get_db
from ..crud.job import (
    complete_job,
    create_job,
    dispatch_job,
    find_next_available_slot,
    get_dispatch_conflict,
    get_job,
    get_job_timeline,
    get_jobs,
    mark_job_on_my_way,
    start_job,
    update_job,
)
from ..models.core import User
from ..schemas.job import (
    JobActivityOut,
    JobCompletionUpdate,
    JobCreate,
    JobDispatchConflictOut,
    JobDispatchUpdate,
    JobNextSlotOut,
    JobOut,
    JobUpdate,
)

router = APIRouter()


@router.get("/jobs/scheduling/conflict", response_model=JobDispatchConflictOut)
def check_dispatch_conflict_api(
    technician_id: int,
    scheduled_time: datetime,
    exclude_job_id: Optional[int] = None,
    buffer_minutes: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if buffer_minutes < 0 or buffer_minutes > 480:
        raise HTTPException(status_code=422, detail="buffer_minutes must be between 0 and 480")

    org_id = int(cast(int, current_user.organization_id))
    conflict = get_dispatch_conflict(
        db,
        org_id,
        technician_id,
        scheduled_time,
        exclude_job_id=exclude_job_id,
        buffer_minutes=buffer_minutes,
    )
    if conflict is None:
        return {
            "conflict": False,
            "conflicting_job_id": None,
            "message": "No scheduling conflict detected",
        }
    return {
        "conflict": True,
        "conflicting_job_id": int(cast(int, conflict.id)),
        "message": "Technician already has a job scheduled at that time",
    }


@router.get("/jobs/scheduling/next-slot", response_model=JobNextSlotOut)
def get_next_available_slot_api(
    technician_id: int,
    requested_time: datetime,
    search_hours: int = 24,
    step_minutes: int = 30,
    exclude_job_id: Optional[int] = None,
    buffer_minutes: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if search_hours < 1 or search_hours > 168:
        raise HTTPException(status_code=422, detail="search_hours must be between 1 and 168")
    if step_minutes < 5 or step_minutes > 240:
        raise HTTPException(status_code=422, detail="step_minutes must be between 5 and 240")
    if buffer_minutes < 0 or buffer_minutes > 480:
        raise HTTPException(status_code=422, detail="buffer_minutes must be between 0 and 480")

    org_id = int(cast(int, current_user.organization_id))
    next_time, conflicts = find_next_available_slot(
        db,
        org_id,
        technician_id,
        requested_time,
        search_hours=search_hours,
        step_minutes=step_minutes,
        exclude_job_id=exclude_job_id,
        buffer_minutes=buffer_minutes,
    )
    return {
        "technician_id": technician_id,
        "requested_time": requested_time,
        "search_hours": search_hours,
        "step_minutes": step_minutes,
        "next_available_time": next_time,
        "conflicting_job_ids": conflicts,
    }


@router.get("/jobs", response_model=List[JobOut])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_jobs(db, current_user.organization_id)


@router.post("/jobs", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job_api(
    job: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return create_job(db, job.model_dump(), current_user.organization_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job_api(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = get_job(db, job_id, current_user.organization_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.put("/jobs/{job_id}", response_model=JobOut)
def update_job_api(
    job_id: int,
    update: JobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = get_job(db, job_id, current_user.organization_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return update_job(db, job, update.model_dump(exclude_unset=True))


@router.patch("/jobs/{job_id}/dispatch", response_model=JobOut)
def dispatch_job_api(
    job_id: int,
    update: JobDispatchUpdate,
    buffer_minutes: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if buffer_minutes < 0 or buffer_minutes > 480:
        raise HTTPException(status_code=422, detail="buffer_minutes must be between 0 and 480")

    job = get_job(db, job_id, current_user.organization_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    dispatched, error = dispatch_job(
        db,
        job,
        current_user.organization_id,
        update.technician_id,
        update.scheduled_time,
        buffer_minutes=buffer_minutes,
        actor_user_id=int(cast(int, current_user.id)),
    )
    if error:
        raise HTTPException(status_code=422, detail=error)
    return dispatched


@router.patch("/jobs/{job_id}/on-my-way", response_model=JobOut)
def mark_job_on_my_way_api(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = get_job(db, job_id, current_user.organization_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    updated, error = mark_job_on_my_way(
        db,
        job,
        current_user.organization_id,
        actor_user_id=int(cast(int, current_user.id)),
    )
    if error:
        raise HTTPException(status_code=422, detail=error)
    return updated


@router.patch("/jobs/{job_id}/start", response_model=JobOut)
def start_job_api(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = get_job(db, job_id, current_user.organization_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    updated, error = start_job(
        db,
        job,
        current_user.organization_id,
        actor_user_id=int(cast(int, current_user.id)),
    )
    if error:
        raise HTTPException(status_code=422, detail=error)
    return updated


@router.patch("/jobs/{job_id}/complete", response_model=JobOut)
def complete_job_api(
    job_id: int,
    update: JobCompletionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = get_job(db, job_id, current_user.organization_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    completed, error = complete_job(
        db,
        job,
        current_user.organization_id,
        update.completion_notes,
        actor_user_id=int(cast(int, current_user.id)),
    )
    if error:
        raise HTTPException(status_code=422, detail=error)
    return completed


@router.get("/jobs/{job_id}/timeline", response_model=List[JobActivityOut])
def list_job_timeline_api(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = get_job(db, job_id, current_user.organization_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return get_job_timeline(db, job_id, current_user.organization_id)
