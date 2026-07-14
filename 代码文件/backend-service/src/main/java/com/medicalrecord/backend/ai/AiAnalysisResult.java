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
        String lowConfidenceReason
) {
    public AiAnalysisResult {
        symptoms = symptoms == null ? List.of() : List.copyOf(symptoms);
        medicalTerms = medicalTerms == null ? List.of() : List.copyOf(medicalTerms);
        diagnosisCandidates = diagnosisCandidates == null ? List.of() : List.copyOf(diagnosisCandidates);
    }
}
