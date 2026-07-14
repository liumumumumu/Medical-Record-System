package com.medicalrecord.backend.cases;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum Department {
    INTERNAL("internal"),
    SURGERY("surgery"),
    PEDIATRICS("pediatrics"),
    EMERGENCY("emergency"),
    OTHER("other");

    private final String value;

    Department(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static Department fromValue(String value) {
        for (Department department : values()) {
            if (department.value.equals(value)) {
                return department;
            }
        }
        throw new IllegalArgumentException("Unsupported department: " + value);
    }
}
