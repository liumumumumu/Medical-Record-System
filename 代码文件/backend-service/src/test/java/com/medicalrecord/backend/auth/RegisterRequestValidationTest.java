package com.medicalrecord.backend.auth;

import jakarta.validation.Validation;
import jakarta.validation.Validator;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class RegisterRequestValidationTest {
    private static Validator validator;

    @BeforeAll
    static void createValidator() {
        validator = Validation.buildDefaultValidatorFactory().getValidator();
    }

    @Test
    void rejectsPasswordLongerThanBcryptByteLimit() {
        RegisterRequest request = new RegisterRequest(
                "unicode_user",
                "密".repeat(30),
                "测试用户"
        );

        assertThat(validator.validate(request))
                .anySatisfy(violation -> {
                    assertThat(violation.getPropertyPath().toString()).isEqualTo("password");
                    assertThat(violation.getMessage()).contains("72");
                });
    }

    @Test
    void acceptsPasswordWithinBcryptByteLimit() {
        RegisterRequest request = new RegisterRequest(
                "valid_user",
                "安全Password123",
                "测试用户"
        );

        assertThat(validator.validate(request)).isEmpty();
    }
}
