package com.medicalrecord.backend.cases;

import jakarta.validation.Validation;
import jakarta.validation.Validator;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

class CreateCaseRequestValidationTest {
    private static Validator validator;

    @BeforeAll
    static void setUpValidator() {
        validator = Validation.buildDefaultValidatorFactory().getValidator();
    }

    @Test
    void acceptsTheFrontendContract() {
        assertThat(validator.validate(validRequest())).isEmpty();
    }

    @Test
    void rejectsRequiredFieldsAndAgeOutsideRange() {
        CreateCaseRequest request = new CreateCaseRequest(
                "", null, 131, null, null, "", "", "",
                null, null, null, null, null, null, null, List.of());

        Set<String> paths = validator.validate(request).stream()
                .map(violation -> violation.getPropertyPath().toString())
                .collect(java.util.stream.Collectors.toSet());

        assertThat(paths).contains("patientName", "gender", "age", "chiefComplaint", "presentIllness");
        assertThat(paths).doesNotContain("pastHistory");
    }

    @Test
    void defaultsMissingPastHistory() {
        CreateCaseRequest request = new CreateCaseRequest(
                "张某", Gender.MALE, 32, null, null, "咳嗽", "咳嗽 2 天", null,
                null, null, null, null, null, null, null, List.of());

        assertThat(validator.validate(request)).isEmpty();
        assertThat(request.pastHistory()).isEqualTo("未提供");
    }

    private CreateCaseRequest validRequest() {
        return new CreateCaseRequest(
                "张某",
                Gender.MALE,
                32,
                Department.INTERNAL,
                java.time.LocalDate.of(2026, 7, 10),
                "发热、咳嗽 3 天",
                "受凉后出现发热和咳嗽",
                "无",
                "无",
                "体温 38.2℃",
                "咽部充血",
                "白细胞轻度升高",
                null,
                null,
                null,
                List.of(GenerationNeed.RECORD, GenerationNeed.DIAGNOSIS)
        );
    }
}
