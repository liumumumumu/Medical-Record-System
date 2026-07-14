package com.medicalrecord.backend.cases;

import com.medicalrecord.backend.jobs.JobStatus;

import java.time.Instant;
import java.util.List;

public record CaseDetailResponse(
        String caseId,
        CaseInput input,
        JobStatus status,
        String currentJobId,
        CaseResultResponse result,
        String editedRecord,
        List<AttachmentResponse> attachments,
        Instant createdAt,
        Instant updatedAt
) {
}
