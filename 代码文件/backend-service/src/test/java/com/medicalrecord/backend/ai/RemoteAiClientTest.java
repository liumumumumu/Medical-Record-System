package com.medicalrecord.backend.ai;

import com.medicalrecord.backend.cases.CaseInput;
import com.medicalrecord.backend.cases.Gender;
import com.medicalrecord.backend.config.AiProperties;
import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.reactive.function.client.WebClient;

import java.io.IOException;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;
import java.util.logging.Logger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class RemoteAiClientTest {
    private MockWebServer server;

    @BeforeEach
    void startServer() throws IOException {
        Logger.getLogger(MockWebServer.class.getName()).setLevel(Level.OFF);
        server = new MockWebServer();
        server.start();
    }

    @AfterEach
    void stopServer() throws IOException {
        server.shutdown();
    }

    @Test
    void mapsSnakeCaseAiResponse() {
        server.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("""
                        {
                          "generated_record": "结构化病历",
                          "symptoms": ["发热", "咳嗽"],
                          "medical_terms": ["白细胞"],
                          "diagnosis_top1": "上呼吸道感染",
                          "diagnosis_candidates": ["上呼吸道感染", "流感"],
                          "diagnosis_reason": "符合呼吸道表现",
                          "treatment_advice": "建议进一步评估",
                          "content": "综合分析",
                          "model_version": "rules-1.0",
                          "confidence": 0.86,
                          "low_confidence": false
                        }
                        """));
        RemoteAiClient client = client(Duration.ofSeconds(2));

        AiAnalysisResult result = client.analyze(input());

        assertThat(result.generatedRecord()).isEqualTo("结构化病历");
        assertThat(result.diagnosisCandidates()).containsExactly("上呼吸道感染", "流感");
        assertThat(result.modelVersion()).isEqualTo("rules-1.0");
        assertThat(result.confidence()).isEqualTo(0.86);
        assertThat(result.lowConfidence()).isFalse();
    }

    @Test
    void mapsCurrentLlyCamelCaseResponse() {
        server.enqueue(new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("""
                        {
                          "generatedRecord": "结构化病历",
                          "symptoms": ["发热", "咳嗽"],
                          "medicalTerms": ["白细胞"],
                          "diagnosisTop1": "上呼吸道感染",
                          "diagnosisCandidates": ["上呼吸道感染", "流感"],
                          "diagnosisReason": "符合呼吸道表现",
                          "treatmentAdvice": "建议进一步评估"
                        }
                        """));

        AiAnalysisResult result = client(Duration.ofSeconds(2)).analyze(input());

        assertThat(result.generatedRecord()).isEqualTo("结构化病历");
        assertThat(result.diagnosisTop1()).isEqualTo("上呼吸道感染");
        assertThat(result.modelVersion()).isEqualTo("unknown");
    }

    @Test
    void reportsTimeoutAfterSingleRetry() {
        server.enqueue(delayedResponse());
        server.enqueue(delayedResponse());
        RemoteAiClient client = client(Duration.ofMillis(80));

        assertThatThrownBy(() -> client.analyze(input()))
                .isInstanceOf(AiServiceException.class)
                .extracting(exception -> ((AiServiceException) exception).getCode())
                .isEqualTo("AI_TIMEOUT");
    }

    private MockResponse delayedResponse() {
        return new MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("{}")
                .setHeadersDelay(300, TimeUnit.MILLISECONDS);
    }

    private RemoteAiClient client(Duration timeout) {
        return new RemoteAiClient(
                new AiProperties("remote", server.url("/").toString(), "nlp/analyze", timeout),
                WebClient.builder()
        );
    }

    private CaseInput input() {
        return new CaseInput(
                "张某", Gender.MALE, 32, null, null,
                "发热咳嗽", "发热咳嗽 3 天", "无", "无",
                null, null, null, null, null, null, List.of());
    }
}
