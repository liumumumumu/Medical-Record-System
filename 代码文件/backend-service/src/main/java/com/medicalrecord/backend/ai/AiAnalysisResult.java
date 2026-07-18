package com.medicalrecord.backend.ai;

import java.util.List;

public record AiAnalysisResult(
        String generatedRecord,
        List<String> symptoms,
        List<String> medicalTerms,
        String diagnosisTop1,
        List<String> diagnosisCandidates,
        String diagnosisReason,
        String treatmentAdvice,
        String content,
        String modelVersion,
        double confidence,
        boolean lowConfidence,
        String lowConfidenceReason,
        RecordGenerationInfo recordGeneration,
        FormalizedRecord formalizedRecord
) {
    public AiAnalysisResult {
        symptoms = symptoms == null ? List.of() : List.copyOf(symptoms);
        medicalTerms = medicalTerms == null ? List.of() : List.copyOf(medicalTerms);
        diagnosisCandidates = diagnosisCandidates == null ? List.of() : List.copyOf(diagnosisCandidates);
        recordGeneration = recordGeneration == null ? RecordGenerationInfo.unknown() : recordGeneration;
        formalizedRecord = formalizedRecord == null ? FormalizedRecord.empty() : formalizedRecord;
    }

    public AiAnalysisResult(
            String generatedRecord,
            List<String> symptoms,
            List<String> medicalTerms,
            String diagnosisTop1,
            List<String> diagnosisCandidates,
            String diagnosisReason,
            String treatmentAdvice,
            String content,
            String modelVersion,
            double confidence,
            boolean lowConfidence,
            String lowConfidenceReason,
            RecordGenerationInfo recordGeneration
    ) {
        this(generatedRecord, symptoms, medicalTerms, diagnosisTop1, diagnosisCandidates,
                diagnosisReason, treatmentAdvice, content, modelVersion, confidence,
                lowConfidence, lowConfidenceReason, recordGeneration, FormalizedRecord.empty());
    }

    public AiAnalysisResult(
            String generatedRecord,
            List<String> symptoms,
            List<String> medicalTerms,
            String diagnosisTop1,
            List<String> diagnosisCandidates,
            String diagnosisReason,
            String treatmentAdvice,
            String content,
            String modelVersion,
            double confidence,
            boolean lowConfidence,
            String lowConfidenceReason
    ) {
        this(generatedRecord, symptoms, medicalTerms, diagnosisTop1, diagnosisCandidates,
                diagnosisReason, treatmentAdvice, content, modelVersion, confidence,
                lowConfidence, lowConfidenceReason, RecordGenerationInfo.unknown(), FormalizedRecord.empty());
    }
}
