package com.medicalrecord.backend.security;

import com.medicalrecord.backend.config.JwtProperties;
import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;

class JwtServiceTest {

    @Test
    void createsAndParsesBearerToken() {
        JwtService service = new JwtService(new JwtProperties(
                "test-secret-for-medical-record-backend-with-more-than-32-bytes",
                Duration.ofHours(2)
        ));
        AuthenticatedUser expected = new AuthenticatedUser("user_1", "demo", "USER");

        String token = service.createToken(expected);

        assertThat(service.parseToken(token)).isEqualTo(expected);
        assertThat(service.expiresInSeconds()).isEqualTo(7200);
    }
}
