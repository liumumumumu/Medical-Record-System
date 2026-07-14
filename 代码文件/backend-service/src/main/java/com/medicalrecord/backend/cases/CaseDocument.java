package com.medicalrecord.backend.cases;

import com.medicalrecord.backend.files.AttachmentMetadata;
import com.medicalrecord.backend.jobs.JobStatus;
import com.medicalrecord.backend.report.ReportMetadata;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.Version;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Document("cases")
public class CaseDocument {
    @Id
    private String caseId;

    @Indexed
    private String ownerId;

    private CaseInput input;
    private CaseResult result;
    private String editedRecord;
    private List<AttachmentMetadata> attachments = new ArrayList<>();
    private ReportMetadata report;
    private String currentJobId;
    private JobStatus status;
    private int contentRevision;
    private Instant createdAt;
    private Instant updatedAt;

    @Version
    private Long version;

    public CaseDocument() {
    }

    public CaseDocument(
            String caseId,
            String ownerId,
            CaseInput input,
            List<AttachmentMetadata> attachments,
            String currentJobId,
            JobStatus status,
            Instant createdAt
    ) {
        this.caseId = caseId;
        this.ownerId = ownerId;
        this.input = input;
        this.attachments = new ArrayList<>(attachments);
        this.currentJobId = currentJobId;
        this.status = status;
        this.createdAt = createdAt;
        this.updatedAt = createdAt;
    }

    public String getCaseId() {
        return caseId;
    }

    public String getOwnerId() {
        return ownerId;
    }

    public CaseInput getInput() {
        return input;
    }

    public CaseResult getResult() {
        return result;
    }

    public void setResult(CaseResult result) {
        this.result = result;
    }

    public String getEditedRecord() {
        return editedRecord;
    }

    public void setEditedRecord(String editedRecord) {
        this.editedRecord = editedRecord;
    }

    public List<AttachmentMetadata> getAttachments() {
        return List.copyOf(attachments);
    }

    public ReportMetadata getReport() {
        return report;
    }

    public void setReport(ReportMetadata report) {
        this.report = report;
    }

    public String getCurrentJobId() {
        return currentJobId;
    }

    public void setCurrentJobId(String currentJobId) {
        this.currentJobId = currentJobId;
    }

    public JobStatus getStatus() {
        return status;
    }

    public void setStatus(JobStatus status) {
        this.status = status;
    }

    public int getContentRevision() {
        return contentRevision;
    }

    public void incrementContentRevision() {
        contentRevision++;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void touch(Instant instant) {
        this.updatedAt = instant;
    }
}
