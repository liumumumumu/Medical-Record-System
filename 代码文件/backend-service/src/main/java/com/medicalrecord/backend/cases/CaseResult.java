package com.medicalrecord.backend.cases;

import com.medicalrecord.backend.ai.AiAnalysisResult;

import java.time.Instant;

public record CaseResult(AiAnalysisResult analysis, Instant generatedAt) {
}
