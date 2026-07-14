package com.medicalrecord.backend.ai;

import com.medicalrecord.backend.cases.CaseInput;
import com.medicalrecord.backend.cases.Gender;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class MockAiClientTest {
    private final MockAiClient client = new MockAiClient();

    @Test
    void returnsDeterministicRespiratoryResult() {
        CaseInput input = new CaseInput(
                "张某", Gender.MALE, 32, null, null,
                "发热、咳嗽 3 天", "受凉后发热咳嗽", "无", "无",
                null, "咽部充血", "白细胞轻度升高",
                null, null, null, List.of());

        AiAnalysisResult first = client.analyze(input);
        AiAnalysisResult second = client.analyze(input);

        assertThat(first).isEqualTo(second);
        assertThat(first.diagnosisTop1()).isEqualTo("上呼吸道感染");
        assertThat(first.generatedRecord()).contains("张某", "发热、咳嗽 3 天");
        assertThat(first.treatmentAdvice()).doesNotContain("不替代执业医师判断");
        assertThat(first.confidence()).isBetween(0.0, 1.0);
        assertThat(first.lowConfidence()).isFalse();
    }
}
