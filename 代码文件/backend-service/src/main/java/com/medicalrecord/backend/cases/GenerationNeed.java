package com.medicalrecord.backend.cases;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum GenerationNeed {
    RECORD("record"),
    SYMPTOM("symptom"),
    DIAGNOSIS("diagnosis"),
    TREATMENT("treatment"),
    FULL_REPORT("full-report");

    private final String value;

    GenerationNeed(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static GenerationNeed fromValue(String value) {
        for (GenerationNeed need : values()) {
            if (need.value.equals(value)) {
                return need;
            }
        }
        throw new IllegalArgumentException("Unsupported generation need: " + value);
    }
}
