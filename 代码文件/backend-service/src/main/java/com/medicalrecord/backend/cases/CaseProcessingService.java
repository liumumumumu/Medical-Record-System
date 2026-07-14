package com.medicalrecord.backend.cases;

import com.medicalrecord.backend.ai.AiAnalysisResult;
import com.medicalrecord.backend.ai.AiGateway;
import com.medicalrecord.backend.ai.AiServiceException;
import com.medicalrecord.backend.jobs.JobDocument;
import com.medicalrecord.backend.jobs.JobRepository;
import com.medicalrecord.backend.jobs.JobStatus;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.Instant;

@Service
public class CaseProcessingService {
    private final CaseRepository caseRepository;
    private final JobRepository jobRepository;
    private final AiGateway aiGateway;

    public CaseProcessingService(
            CaseRepository caseRepository,
            JobRepository jobRepository,
            AiGateway aiGateway
    ) {
        this.caseRepository = caseRepository;
        this.jobRepository = jobRepository;
        this.aiGateway = aiGateway;
    }

    @Async("caseTaskExecutor")
    public void process(String jobId) {
        JobDocument job = jobRepository.findById(jobId).orElse(null);
        if (job == null) {
            return;
        }
        CaseDocument document = caseRepository.findById(job.getCaseId()).orElse(null);
        if (document == null) {
            fail(job, null, "CASE_NOT_FOUND", "病例不存在");
            return;
        }

        try {
            Instant now = Instant.now();
            job.update(JobStatus.PROCESSING, 20, "正在调用 AI 分析服务", now);
            jobRepository.save(job);
            document.setStatus(JobStatus.PROCESSING);
            document.touch(now);
            caseRepository.save(document);

            String attachmentContext = document.getAttachments().stream()
                    .filter(attachment -> "parsed".equals(attachment.parseStatus()))
                    .map(attachment -> attachment.originalFileName() + "：\n" + attachment.extractedText())
                    .reduce((left, right) -> left + "\n\n" + right)
                    .orElse("");
            AiAnalysisResult analysis = aiGateway.analyze(
                    document.getInput().withAttachmentContext(attachmentContext));

            now = Instant.now();
            job.update(JobStatus.PROCESSING, 90, "正在保存分析结果", now);
            jobRepository.save(job);
            document.setResult(new CaseResult(analysis, now));
            document.setStatus(JobStatus.COMPLETED);
            document.touch(now);
            caseRepository.save(document);

            job.update(JobStatus.COMPLETED, 100, "分析完成", Instant.now());
            jobRepository.save(job);
        } catch (AiServiceException exception) {
            fail(job, document, exception.getCode(), exception.getMessage());
        } catch (RuntimeException exception) {
            fail(job, document, "AI_PROCESSING_FAILED", "分析任务执行失败");
        }
    }

    private void fail(JobDocument job, CaseDocument document, String code, String message) {
        Instant now = Instant.now();
        job.fail(code, message, now);
        jobRepository.save(job);
        if (document != null) {
            document.setStatus(JobStatus.FAILED);
            document.touch(now);
            caseRepository.save(document);
        }
    }
}
