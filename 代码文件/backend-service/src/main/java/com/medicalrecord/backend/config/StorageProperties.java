package com.medicalrecord.backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.util.unit.DataSize;

import java.nio.file.Path;

@ConfigurationProperties(prefix = "app.storage")
public record StorageProperties(
        Path uploadDir,
        Path reportDir,
        DataSize maxFileSize,
        DataSize maxTotalSize,
        int maxFiles
) {
}
