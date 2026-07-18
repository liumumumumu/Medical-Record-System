package com.medicalrecord.backend.ai;

import java.util.List;

public record RecordGenerationInfo(
        String backend,
        String modelName,
        String modelVersion,
        boolean fallbackUsed,
        List<String> warnings
) {
    public RecordGenerationInfo {
        backend = normalize(backend);
        modelName = normalize(modelName);
        modelVersion = normalize(modelVersion);
        warnings = warnings == null ? List.of() : List.copyOf(warnings);
    }

    public static RecordGenerationInfo unknown() {
        return new RecordGenerationInfo("unknown", "unknown", "unknown", false, List.of());
    }

    private static String normalize(String value) {
        return value == null || value.isBlank() ? "unknown" : value;
    }
}
