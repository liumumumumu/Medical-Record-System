package com.medicalrecord.backend.jobs;

import java.time.Instant;

public record JobResponse(
        String jobId,
        String caseId,
        JobStatus status,
        Integer progress,
        String message,
        String errorCode,
        String errorMessage,
        Instant createdAt,
        Instant updatedAt
) {
    public static JobResponse from(JobDocument job) {
        return new JobResponse(
                job.getJobId(),
                job.getCaseId(),
                job.getStatus(),
                job.getProgress(),
                job.getMessage(),
                job.getErrorCode(),
                job.getErrorMessage(),
                job.getCreatedAt(),
                job.getUpdatedAt()
        );
    }
}
