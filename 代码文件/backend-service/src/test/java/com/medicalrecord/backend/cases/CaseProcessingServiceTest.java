package com.medicalrecord.backend.cases;

import com.medicalrecord.backend.ai.AiAnalysisResult;
import com.medicalrecord.backend.ai.AiGateway;
import com.medicalrecord.backend.ai.AiServiceException;
import com.medicalrecord.backend.jobs.JobDocument;
import com.medicalrecord.backend.jobs.JobRepository;
import com.medicalrecord.backend.jobs.JobStatus;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class CaseProcessingServiceTest {

    @Test
    void persistsCompletedStateAndResult() {
        CaseRepository caseRepository = mock(CaseRepository.class);
        JobRepository jobRepository = mock(JobRepository.class);
        AiGateway gateway = mock(AiGateway.class);
        CaseDocument caseDocument = caseDocument();
        JobDocument job = new JobDocument("job_1", "case_1", "user_1", Instant.now());
        when(jobRepository.findById("job_1")).thenReturn(Optional.of(job));
        when(caseRepository.findById("case_1")).thenReturn(Optional.of(caseDocument));
        when(gateway.analyze(caseDocument.getInput())).thenReturn(result());
        CaseProcessingService service = new CaseProcessingService(caseRepository, jobRepository, gateway);

        service.process("job_1");

        assertThat(job.getStatus()).isEqualTo(JobStatus.COMPLETED);
        assertThat(job.getProgress()).isEqualTo(100);
        assertThat(caseDocument.getStatus()).isEqualTo(JobStatus.COMPLETED);
        assertThat(caseDocument.getResult().analysis().diagnosisTop1()).isEqualTo("上呼吸道感染");
    }

    @Test
    void persistsStableAiFailureCode() {
        CaseRepository caseRepository = mock(CaseRepository.class);
        JobRepository jobRepository = mock(JobRepository.class);
        AiGateway gateway = mock(AiGateway.class);
        CaseDocument caseDocument = caseDocument();
        JobDocument job = new JobDocument("job_1", "case_1", "user_1", Instant.now());
        when(jobRepository.findById("job_1")).thenReturn(Optional.of(job));
        when(caseRepository.findById("case_1")).thenReturn(Optional.of(caseDocument));
        when(gateway.analyze(caseDocument.getInput()))
                .thenThrow(new AiServiceException("AI_TIMEOUT", "AI 分析服务响应超时"));
        CaseProcessingService service = new CaseProcessingService(caseRepository, jobRepository, gateway);

        service.process("job_1");

        assertThat(job.getStatus()).isEqualTo(JobStatus.FAILED);
        assertThat(job.getErrorCode()).isEqualTo("AI_TIMEOUT");
        assertThat(caseDocument.getStatus()).isEqualTo(JobStatus.FAILED);
    }

    private CaseDocument caseDocument() {
        return new CaseDocument(
                "case_1",
                "user_1",
                new CaseInput(
                        "张某", Gender.MALE, 32, null, null,
                        "发热咳嗽", "发热咳嗽 3 天", "无", "无",
                        null, null, null, null, null, null, List.of()),
                List.of(),
                "job_1",
                JobStatus.QUEUED,
                Instant.now()
        );
    }

    private AiAnalysisResult result() {
        return new AiAnalysisResult(
                "结构化病历", List.of("发热"), List.of("白细胞"),
                "上呼吸道感染", List.of("上呼吸道感染"), "诊断依据", "处理建议",
                "综合分析", "test-1.0", 0.82, false, null);
    }
}
