package com.medicalrecord.backend.common;

import java.util.UUID;

public final class IdGenerator {
    private IdGenerator() {
    }

    public static String caseId() {
        return "case_" + compactUuid();
    }

    public static String jobId() {
        return "job_" + compactUuid();
    }

    public static String fileId() {
        return "file_" + compactUuid();
    }

    public static String requestId() {
        return "req_" + compactUuid();
    }

    private static String compactUuid() {
        return UUID.randomUUID().toString().replace("-", "");
    }
}
