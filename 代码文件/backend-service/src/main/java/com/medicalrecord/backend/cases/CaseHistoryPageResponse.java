package com.medicalrecord.backend.cases;

import com.medicalrecord.backend.jobs.JobStatus;

import java.time.Instant;
import java.util.List;

public record CaseHistoryPageResponse(
        List<Item> content,
        int page,
        int size,
        long totalElements,
        int totalPages
) {
    public record Item(
            String caseId,
            String patientName,
            Gender gender,
            Integer age,
            Department department,
            String chiefComplaint,
            JobStatus status,
            Instant createdAt,
            Instant updatedAt
    ) {
    }
}
