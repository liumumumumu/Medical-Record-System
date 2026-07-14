package com.medicalrecord.backend.jobs;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

@Document("jobs")
public class JobDocument {
    @Id
    private String jobId;

    @Indexed
    private String caseId;

    @Indexed
    private String ownerId;

    private JobStatus status;
    private Integer progress;
    private String message;
    private String errorCode;
    private String errorMessage;
    private Instant createdAt;
    private Instant updatedAt;

    public JobDocument() {
    }

    public JobDocument(String jobId, String caseId, String ownerId, Instant createdAt) {
        this.jobId = jobId;
        this.caseId = caseId;
        this.ownerId = ownerId;
        this.status = JobStatus.QUEUED;
        this.progress = 0;
        this.message = "任务已进入队列";
        this.createdAt = createdAt;
        this.updatedAt = createdAt;
    }

    public String getJobId() {
        return jobId;
    }

    public String getCaseId() {
        return caseId;
    }

    public String getOwnerId() {
        return ownerId;
    }

    public JobStatus getStatus() {
        return status;
    }

    public Integer getProgress() {
        return progress;
    }

    public String getMessage() {
        return message;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void update(JobStatus status, Integer progress, String message, Instant now) {
        this.status = status;
        this.progress = progress;
        this.message = message;
        this.updatedAt = now;
        if (status != JobStatus.FAILED) {
            this.errorCode = null;
            this.errorMessage = null;
        }
    }

    public void fail(String errorCode, String errorMessage, Instant now) {
        this.status = JobStatus.FAILED;
        this.progress = null;
        this.message = "分析任务失败";
        this.errorCode = errorCode;
        this.errorMessage = errorMessage;
        this.updatedAt = now;
    }
}
