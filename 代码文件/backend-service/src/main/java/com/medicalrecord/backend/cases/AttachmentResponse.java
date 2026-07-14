package com.medicalrecord.backend.cases;

public record AttachmentResponse(
        String id,
        String fileName,
        String mimeType,
        long size,
        String url,
        String parseStatus,
        String extractedText,
        String failureReason
) {
}
