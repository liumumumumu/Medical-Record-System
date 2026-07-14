package com.medicalrecord.backend.files;

import org.springframework.core.io.Resource;

public record StoredFileResource(
        Resource resource,
        String fileName,
        String mimeType,
        long size
) {
}
