package com.medicalrecord.backend.ai;

public record FormalizedRecord(
        String chiefComplaint,
        String presentIllness,
        String pastHistory,
        String allergyHistory,
        String vitalSigns,
        String physicalExam,
        String auxiliaryExam,
        String preliminaryDiagnosis,
        String treatmentTaken,
        String medicationUsage
) {
    public static FormalizedRecord empty() {
        return new FormalizedRecord(null, null, null, null, null, null, null, null, null, null);
    }
}
