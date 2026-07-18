package com.medicalrecord.backend.cases;

import com.medicalrecord.backend.ai.AiAnalysisResult;
import com.medicalrecord.backend.ai.FormalizedRecord;
import com.medicalrecord.backend.ai.RecordGenerationInfo;
import com.medicalrecord.backend.jobs.JobStatus;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class CaseMapperTest {

    @Test
    void historyItemCarriesDiagnosisWhenResultExists() {
        CaseDocument document = caseDocument();
        document.setResult(new CaseResult(analysis(), Instant.now()));
        document.setStatus(JobStatus.COMPLETED);

        CaseHistoryPageResponse.Item item = new CaseMapper().toHistoryItem(document);

        assertThat(item.diagnosisTop1()).isEqualTo("上呼吸道感染");
    }

    @Test
    void historyItemHasNoDiagnosisBeforeAnalysisCompletes() {
        CaseHistoryPageResponse.Item item = new CaseMapper().toHistoryItem(caseDocument());

        assertThat(item.diagnosisTop1()).isNull();
        assertThat(item.preliminaryDiagnosis()).isEqualTo("疑似上感");
    }

    @Test
    void resultUsesFormalizedFieldsWhileKeepingOriginalInputInCaseDocument() {
        CaseDocument document = caseDocument();
        AiAnalysisResult analysis = new AiAnalysisResult(
                "结构化病历", List.of("发热"), List.of("白细胞"),
                "上呼吸道感染", List.of("上呼吸道感染"), "诊断依据", "处理建议",
                "综合分析", "test-1.0", 0.82, false, null,
                RecordGenerationInfo.unknown(),
                new FormalizedRecord(
                        "发热、咳嗽3天", "患者3天前出现发热、咳嗽", "既往无特殊病史",
                        "否认药物过敏史", "T 38.5℃", "咽部充血", "未提供",
                        "考虑上呼吸道感染", "曾接受物理降温", "曾服用退热药"
                )
        );
        document.setResult(new CaseResult(analysis, Instant.now()));

        CaseResultResponse result = new CaseMapper().toResult(document);

        assertThat(result.summary().chiefComplaint()).isEqualTo("发热、咳嗽3天");
        assertThat(result.structuredRecord().presentIllness()).isEqualTo("患者3天前出现发热、咳嗽");
        assertThat(result.structuredRecord().allergyHistory()).isEqualTo("否认药物过敏史");
        assertThat(result.analysis().treatmentTaken()).isEqualTo("曾接受物理降温");
        assertThat(document.getInput().chiefComplaint()).isEqualTo("发热咳嗽");
    }

    private CaseDocument caseDocument() {
        return new CaseDocument(
                "case_1",
                "user_1",
                new CaseInput(
                        "张某", Gender.MALE, 32, null, null,
                        "发热咳嗽", "发热咳嗽 3 天", "无", "无",
                        null, null, null, "疑似上感", null, null, List.of()),
                List.of(),
                "job_1",
                JobStatus.QUEUED,
                Instant.now()
        );
    }

    private AiAnalysisResult analysis() {
        return new AiAnalysisResult(
                "结构化病历", List.of("发热"), List.of("白细胞"),
                "上呼吸道感染", List.of("上呼吸道感染"), "诊断依据", "处理建议",
                "综合分析", "test-1.0", 0.82, false, null);
    }
}
