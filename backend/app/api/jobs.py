from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..core.db import get_db
from ..crud.job import complete_job, create_job, dispatch_job, get_job, get_jobs, update_job
from ..models.core import User
from ..schemas.job import JobCompletionUpdate, JobCreate, JobDispatchUpdate, JobOut, JobUpdate

router = APIRouter()


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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = get_job(db, job_id, current_user.organization_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    dispatched, error = dispatch_job(
        db,
        job,
        current_user.organization_id,
        update.technician_id,
        update.scheduled_time,
    )
    if error:
        raise HTTPException(status_code=422, detail=error)
    return dispatched


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
    )
    if error:
        raise HTTPException(status_code=422, detail=error)
    return completed
