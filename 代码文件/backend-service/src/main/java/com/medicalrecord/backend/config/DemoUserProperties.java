package com.medicalrecord.backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.demo-user")
public record DemoUserProperties(boolean enabled, String username, String password) {
}
