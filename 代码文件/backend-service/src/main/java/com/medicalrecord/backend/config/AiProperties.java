package com.medicalrecord.backend.config;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import java.time.Duration;

@Validated
@ConfigurationProperties(prefix = "app.ai")
public record AiProperties(
        @NotBlank String mode,
        @NotBlank String baseUrl,
        @NotBlank String endpoint,
        @NotNull Duration timeout
) {
    public boolean isRemote() {
        return "remote".equalsIgnoreCase(mode);
    }
}
