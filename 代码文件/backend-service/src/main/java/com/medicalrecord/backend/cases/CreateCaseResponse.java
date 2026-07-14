package com.medicalrecord.backend.cases;

import com.medicalrecord.backend.jobs.JobStatus;

import java.time.Instant;

public record CreateCaseResponse(
        String caseId,
        String jobId,
        JobStatus status,
        Instant createdAt
) {
}
