package com.medicalrecord.backend.cases;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;

public record CaseResultResponse(
        String caseId,
        Instant generatedAt,
        Summary summary,
        StructuredRecord structuredRecord,
        Analysis analysis,
        List<AttachmentResponse> attachments
) {
    public record Summary(
            String patientName,
            Gender gender,
            Integer age,
            Department department,
            LocalDate visitDate,
            String chiefComplaint
    ) {
    }

    public record StructuredRecord(
            String generatedContent,
            String presentIllness,
            String pastHistory,
            String allergyHistory,
            String vitalSigns,
            String physicalExam,
            String auxiliaryExam
    ) {
    }

    public record Analysis(
            String preliminaryDiagnosis,
            String treatmentTaken,
            String medicationUsage,
            List<GenerationNeed> generationNeeds,
            String content,
            List<String> symptoms,
            List<String> medicalTerms,
            String diagnosisTop1,
            List<String> diagnosisCandidates,
            String diagnosisReason,
            String treatmentAdvice,
            String modelVersion,
            double confidence,
            boolean lowConfidence,
            String lowConfidenceReason,
            String disclaimer
    ) {
    }
}
