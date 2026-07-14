package com.medicalrecord.backend.files;

import java.time.Instant;

public record AttachmentMetadata(
        String id,
        String originalFileName,
        String storedFileName,
        String mimeType,
        long size,
        String path,
        String parseStatus,
        String extractedText,
        String parseError,
        Instant createdAt
) {
}
