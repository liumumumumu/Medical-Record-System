package com.medicalrecord.backend.jobs;

import com.medicalrecord.backend.cases.CaseDocument;
import com.medicalrecord.backend.cases.CaseInput;
import com.medicalrecord.backend.cases.CaseRepository;
import com.medicalrecord.backend.cases.Gender;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyCollection;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class StaleJobSweeperTest {

    @Test
    void failsJobsStuckInProcessingBeyondTimeout() {
        JobRepository jobRepository = mock(JobRepository.class);
        CaseRepository caseRepository = mock(CaseRepository.class);
        Instant now = Instant.now();
        Instant longAgo = now.minus(Duration.ofMinutes(30));
        JobDocument job = new JobDocument("job_1", "case_1", "user_1", longAgo);
        job.update(JobStatus.PROCESSING, 20, "正在调用 AI 分析服务", longAgo);
        CaseDocument caseDocument = caseDocument();
        caseDocument.setStatus(JobStatus.PROCESSING);
        when(jobRepository.findByStatusInAndUpdatedAtBefore(anyCollection(), any(Instant.class)))
                .thenReturn(List.of(job));
        when(caseRepository.findById("case_1")).thenReturn(Optional.of(caseDocument));

        new StaleJobSweeper(jobRepository, caseRepository).sweep(now);

        assertThat(job.getStatus()).isEqualTo(JobStatus.FAILED);
        assertThat(job.getErrorCode()).isEqualTo("PROCESSING_TIMEOUT");
        assertThat(caseDocument.getStatus()).isEqualTo(JobStatus.FAILED);
        verify(jobRepository).save(job);
        verify(caseRepository).save(caseDocument);
    }

    @Test
    void leavesCompletedCaseUntouchedWhenOnlyJobRecordIsStale() {
        JobRepository jobRepository = mock(JobRepository.class);
        CaseRepository caseRepository = mock(CaseRepository.class);
        Instant now = Instant.now();
        JobDocument job = new JobDocument("job_1", "case_1", "user_1", now.minus(Duration.ofMinutes(30)));
        job.update(JobStatus.PROCESSING, 90, "正在保存分析结果", now.minus(Duration.ofMinutes(30)));
        CaseDocument caseDocument = caseDocument();
        caseDocument.setStatus(JobStatus.COMPLETED);
        when(jobRepository.findByStatusInAndUpdatedAtBefore(anyCollection(), any(Instant.class)))
                .thenReturn(List.of(job));
        when(caseRepository.findById("case_1")).thenReturn(Optional.of(caseDocument));

        new StaleJobSweeper(jobRepository, caseRepository).sweep(now);

        assertThat(job.getStatus()).isEqualTo(JobStatus.FAILED);
        assertThat(caseDocument.getStatus()).isEqualTo(JobStatus.COMPLETED);
        verify(caseRepository, never()).save(caseDocument);
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
}
