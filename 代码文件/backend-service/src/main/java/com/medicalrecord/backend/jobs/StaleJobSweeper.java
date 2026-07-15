package com.medicalrecord.backend.jobs;

import com.medicalrecord.backend.cases.CaseRepository;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.util.List;

/**
 * 后端异常退出时，正在处理的任务会永远停留在 QUEUED/PROCESSING。
 * 定期把长时间无进展的任务标记为失败，让前端拿到稳定错误码而不是无限等待。
 */
@Component
public class StaleJobSweeper {
    static final Duration STALE_AFTER = Duration.ofMinutes(10);

    private final JobRepository jobRepository;
    private final CaseRepository caseRepository;

    public StaleJobSweeper(JobRepository jobRepository, CaseRepository caseRepository) {
        this.jobRepository = jobRepository;
        this.caseRepository = caseRepository;
    }

    @Scheduled(fixedDelay = 60_000, initialDelay = 60_000)
    public void sweepNow() {
        sweep(Instant.now());
    }

    void sweep(Instant now) {
        List<JobDocument> staleJobs = jobRepository.findByStatusInAndUpdatedAtBefore(
                List.of(JobStatus.QUEUED, JobStatus.PROCESSING),
                now.minus(STALE_AFTER)
        );
        for (JobDocument job : staleJobs) {
            job.fail("PROCESSING_TIMEOUT", "分析任务长时间未完成，已标记为失败，请重新提交分析", now);
            jobRepository.save(job);
            caseRepository.findById(job.getCaseId()).ifPresent(document -> {
                if (document.getStatus() == JobStatus.QUEUED || document.getStatus() == JobStatus.PROCESSING) {
                    document.setStatus(JobStatus.FAILED);
                    document.touch(now);
                    caseRepository.save(document);
                }
            });
        }
    }
}
