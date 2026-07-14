package com.medicalrecord.backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.List;

@ConfigurationProperties(prefix = "app.cors")
public record CorsProperties(List<String> allowedOrigins) {
    public CorsProperties {
        allowedOrigins = allowedOrigins == null
                ? List.of("http://localhost:5173", "http://127.0.0.1:5173")
                : allowedOrigins.stream().distinct().toList();
    }
}
