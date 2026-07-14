package com.medicalrecord.backend.cases;

import com.medicalrecord.backend.common.ApiException;
import com.medicalrecord.backend.common.IdGenerator;
import com.medicalrecord.backend.files.AttachmentMetadata;
import com.medicalrecord.backend.files.FileStorageService;
import com.medicalrecord.backend.files.StoredFileResource;
import com.medicalrecord.backend.jobs.JobDocument;
import com.medicalrecord.backend.jobs.JobRepository;
import com.medicalrecord.backend.jobs.JobStatus;
import org.springframework.core.task.TaskRejectedException;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.time.Instant;
import java.util.List;
import java.util.regex.Pattern;

@Service
public class CaseService {
    private final CaseRepository caseRepository;
    private final JobRepository jobRepository;
    private final CaseProcessingService processingService;
    private final FileStorageService fileStorageService;
    private final CaseMapper caseMapper;

    public CaseService(
            CaseRepository caseRepository,
            JobRepository jobRepository,
            CaseProcessingService processingService,
            FileStorageService fileStorageService,
            CaseMapper caseMapper
    ) {
        this.caseRepository = caseRepository;
        this.jobRepository = jobRepository;
        this.processingService = processingService;
        this.fileStorageService = fileStorageService;
        this.caseMapper = caseMapper;
    }

    public CreateCaseResponse create(String ownerId, CreateCaseRequest request, List<MultipartFile> files) {
        String caseId = IdGenerator.caseId();
        String jobId = IdGenerator.jobId();
        Instant now = Instant.now();
        List<AttachmentMetadata> attachments = fileStorageService.storeAttachments(caseId, files);
        CaseDocument caseDocument = new CaseDocument(
                caseId,
                ownerId,
                CaseInput.from(request),
                attachments,
                jobId,
                JobStatus.QUEUED,
                now
        );
        JobDocument job = new JobDocument(jobId, caseId, ownerId, now);

        try {
            caseRepository.save(caseDocument);
            jobRepository.save(job);
            submit(job, caseDocument);
            return new CreateCaseResponse(caseId, jobId, JobStatus.QUEUED, now);
        } catch (ApiException exception) {
            throw exception;
        } catch (RuntimeException exception) {
            jobRepository.deleteById(jobId);
            caseRepository.deleteById(caseId);
            fileStorageService.deleteCaseAttachments(caseId);
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "病例创建失败");
        }
    }

    public CreateCaseResponse retry(String caseId, String ownerId) {
        CaseDocument caseDocument = findOwned(caseId, ownerId);
        if (caseDocument.getStatus() != JobStatus.FAILED) {
            throw new ApiException(HttpStatus.CONFLICT, "JOB_NOT_RETRYABLE", "只有失败的病例任务可以重试");
        }
        String jobId = IdGenerator.jobId();
        Instant now = Instant.now();
        JobDocument job = new JobDocument(jobId, caseId, ownerId, now);
        caseDocument.setCurrentJobId(jobId);
        caseDocument.setStatus(JobStatus.QUEUED);
        caseDocument.touch(now);
        caseRepository.save(caseDocument);
        jobRepository.save(job);
        submit(job, caseDocument);
        return new CreateCaseResponse(caseId, jobId, JobStatus.QUEUED, now);
    }

    public CaseResultResponse result(String caseId, String ownerId) {
        CaseDocument document = findOwned(caseId, ownerId);
        if (document.getStatus() != JobStatus.COMPLETED || document.getResult() == null) {
            throw new ApiException(HttpStatus.CONFLICT, "RESULT_NOT_READY", "分析结果尚未生成");
        }
        return caseMapper.toResult(document);
    }

    public CaseDetailResponse detail(String caseId, String ownerId) {
        return caseMapper.toDetail(findOwned(caseId, ownerId));
    }

    public CaseHistoryPageResponse history(String ownerId, String keyword, int page, int size) {
        PageRequest pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        String normalizedKeyword = keyword == null ? "" : keyword.strip();
        Page<CaseDocument> result = normalizedKeyword.isEmpty()
                ? caseRepository.findByOwnerId(ownerId, pageable)
                : caseRepository.searchByOwnerId(ownerId, Pattern.quote(normalizedKeyword), pageable);
        return new CaseHistoryPageResponse(
                result.getContent().stream().map(caseMapper::toHistoryItem).toList(),
                result.getNumber(),
                result.getSize(),
                result.getTotalElements(),
                result.getTotalPages()
        );
    }

    public CaseDetailResponse updateRecord(String caseId, String ownerId, UpdateRecordRequest request) {
        CaseDocument document = findOwned(caseId, ownerId);
        if (document.getResult() == null || document.getStatus() != JobStatus.COMPLETED) {
            throw new ApiException(HttpStatus.CONFLICT, "RESULT_NOT_READY", "分析完成后才能编辑病历");
        }
        if (document.getReport() != null) {
            fileStorageService.deleteReport(document.getReport().path());
            document.setReport(null);
        }
        document.setEditedRecord(request.editedRecord());
        document.incrementContentRevision();
        document.touch(Instant.now());
        return caseMapper.toDetail(caseRepository.save(document));
    }

    public StoredFileResource attachment(String caseId, String fileId, String ownerId) {
        CaseDocument document = findOwned(caseId, ownerId);
        AttachmentMetadata metadata = document.getAttachments().stream()
                .filter(attachment -> attachment.id().equals(fileId))
                .findFirst()
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "FILE_NOT_FOUND", "附件不存在"));
        return fileStorageService.loadAttachment(metadata);
    }

    private CaseDocument findOwned(String caseId, String ownerId) {
        return caseRepository.findByCaseIdAndOwnerId(caseId, ownerId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "CASE_NOT_FOUND", "病例不存在"));
    }

    private void submit(JobDocument job, CaseDocument caseDocument) {
        try {
            processingService.process(job.getJobId());
        } catch (TaskRejectedException exception) {
            Instant now = Instant.now();
            job.fail("TASK_QUEUE_FULL", "任务队列已满，请稍后重试", now);
            jobRepository.save(job);
            caseDocument.setStatus(JobStatus.FAILED);
            caseDocument.touch(now);
            caseRepository.save(caseDocument);
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "TASK_QUEUE_FULL", "任务队列已满，请稍后重试");
        }
    }
}
