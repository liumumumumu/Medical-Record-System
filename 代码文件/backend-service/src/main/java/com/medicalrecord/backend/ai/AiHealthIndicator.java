package com.medicalrecord.backend.ai;

import com.medicalrecord.backend.config.AiProperties;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.util.Map;

@Component("aiService")
public class AiHealthIndicator implements HealthIndicator {
    private final AiProperties properties;
    private final WebClient webClient;

    public AiHealthIndicator(AiProperties properties, WebClient.Builder builder) {
        this.properties = properties;
        this.webClient = builder.baseUrl(properties.baseUrl()).build();
    }

    @Override
    public Health health() {
        if (!properties.isRemote()) {
            return Health.up().withDetail("mode", "mock").build();
        }
        try {
            Map<?, ?> response = webClient.get()
                    .uri("/health")
                    .retrieve()
                    .bodyToMono(Map.class)
                    .timeout(min(properties.timeout(), Duration.ofSeconds(3)))
                    .block();
            if (response == null || !"ok".equals(response.get("status"))) {
                return Health.down().withDetail("mode", "remote")
                        .withDetail("reason", "AI health response is invalid").build();
            }
            return Health.up()
                    .withDetail("mode", "remote")
                    .withDetail("modelVersion",
                            response.get("modelVersion") == null ? "unknown" : response.get("modelVersion"))
                    .build();
        } catch (RuntimeException exception) {
            return Health.down()
                    .withDetail("mode", "remote")
                    .withDetail("reason", "AI service is unavailable")
                    .build();
        }
    }

    private Duration min(Duration left, Duration right) {
        return left.compareTo(right) <= 0 ? left : right;
    }
}
