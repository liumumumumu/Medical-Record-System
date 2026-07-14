package com.medicalrecord.backend.ai;

import com.medicalrecord.backend.cases.CaseInput;
import com.medicalrecord.backend.config.AiProperties;
import org.springframework.stereotype.Service;

@Service
public class AiGateway {
    private final AiProperties properties;
    private final MockAiClient mockAiClient;
    private final RemoteAiClient remoteAiClient;

    public AiGateway(AiProperties properties, MockAiClient mockAiClient, RemoteAiClient remoteAiClient) {
        this.properties = properties;
        this.mockAiClient = mockAiClient;
        this.remoteAiClient = remoteAiClient;
    }

    public AiAnalysisResult analyze(CaseInput input) {
        return properties.isRemote() ? remoteAiClient.analyze(input) : mockAiClient.analyze(input);
    }
}
