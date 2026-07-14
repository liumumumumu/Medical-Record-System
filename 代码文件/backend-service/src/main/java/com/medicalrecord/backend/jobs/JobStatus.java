package com.medicalrecord.backend.jobs;

import com.fasterxml.jackson.annotation.JsonValue;

public enum JobStatus {
    QUEUED("queued"),
    PROCESSING("processing"),
    COMPLETED("completed"),
    FAILED("failed"),
    CANCELLED("cancelled");

    private final String value;

    JobStatus(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }
}
