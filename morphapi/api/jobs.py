"""
MorphAPI Job Routes
Allows inspection and resumption of discovery and self-healing jobs.
"""

from fastapi import APIRouter, Header, HTTPException, status
from morphapi.db.repository import JobRepository
from morphapi.schemas.errors import ErrorResponse, FailureCode, MorphApiError
from morphapi.schemas.workflow import JobResponse, JobResumeRequest, JobStatus, JobType

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])
job_repo = JobRepository()


@router.get("/{job_id}", response_model=JobResponse, status_code=status.HTTP_200_OK)
async def get_job_status(job_id: str):
    """
    Retrieves status and diagnostic summary for a discovery or healing job.
    """
    job = await job_repo.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "JOB_NOT_FOUND", "message": f"Job '{job_id}' not found."},
        )

    return JobResponse(
        job_id=job["job_id"],
        endpoint_id=job["endpoint_id"],
        tenant_id=job["tenant_id"],
        job_type=JobType(job["job_type"]),
        workflow_thread_id=job["workflow_thread_id"],
        status=JobStatus(job["status"]),
        attempt_count=job["attempt_count"],
        max_attempts=job["max_attempts"],
        failure_reason=job["failure_reason"],
        result_summary=job["result_summary"],
        clarification=job["clarification"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
    )


@router.post("/{job_id}/resume", response_model=JobResponse, status_code=status.HTTP_200_OK)
async def resume_job(job_id: str, payload: JobResumeRequest):
    """
    Resumes a paused job with validated operator approval or clarification input.
    """
    job = await job_repo.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "JOB_NOT_FOUND", "message": f"Job '{job_id}' not found."},
        )

    if job["status"] not in ("PAUSED_FOR_APPROVAL", "PAUSED_FOR_CLARIFICATION"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_STATE", "message": f"Job is in state '{job['status']}' and cannot be resumed."},
        )

    # Process resume action
    new_status = "COMPLETED" if payload.approval_decision == "approve" else "IN_PROGRESS"
    if payload.approval_decision == "reject":
        new_status = "FAILED"

    updated = await job_repo.update_job_status(
        job_id=job_id,
        status=new_status,
        result_summary={"resume_payload": payload.model_dump()},
    )

    return JobResponse(
        job_id=updated["job_id"],
        endpoint_id=updated["endpoint_id"],
        tenant_id=updated["tenant_id"],
        job_type=JobType(updated["job_type"]),
        workflow_thread_id=updated["workflow_thread_id"],
        status=JobStatus(updated["status"]),
        attempt_count=updated["attempt_count"],
        max_attempts=updated["max_attempts"],
        failure_reason=updated["failure_reason"],
        result_summary=updated["result_summary"],
        clarification=updated["clarification"],
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
    )
