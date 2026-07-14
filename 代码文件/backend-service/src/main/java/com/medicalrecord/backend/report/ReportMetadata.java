package com.medicalrecord.backend.report;

import java.time.Instant;

public record ReportMetadata(
        String fileName,
        String path,
        int sourceRevision,
        Instant generatedAt
) {
}
