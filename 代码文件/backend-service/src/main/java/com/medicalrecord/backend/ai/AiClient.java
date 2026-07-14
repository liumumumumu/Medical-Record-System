package com.medicalrecord.backend.ai;

import com.medicalrecord.backend.cases.CaseInput;

public interface AiClient {
    AiAnalysisResult analyze(CaseInput input);
}
