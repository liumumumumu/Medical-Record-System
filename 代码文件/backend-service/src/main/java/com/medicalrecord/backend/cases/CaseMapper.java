package com.medicalrecord.backend.cases;

import com.medicalrecord.backend.ai.AiAnalysisResult;
import com.medicalrecord.backend.files.AttachmentMetadata;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class CaseMapper {
    public static final String DISCLAIMER = "仅供辅助整理与课程演示，不替代执业医师判断。";

    public CaseResultResponse toResult(CaseDocument document) {
        CaseInput input = document.getInput();
        CaseResult result = document.getResult();
        AiAnalysisResult ai = result.analysis();
        String generatedContent = hasText(document.getEditedRecord())
                ? document.getEditedRecord()
                : ai.generatedRecord();

        return new CaseResultResponse(
                document.getCaseId(),
                result.generatedAt(),
                new CaseResultResponse.Summary(
                        input.patientName(), input.gender(), input.age(), input.department(),
                        input.visitDate(), input.chiefComplaint()),
                new CaseResultResponse.StructuredRecord(
                        generatedContent,
                        input.presentIllness(),
                        input.pastHistory(),
                        input.allergyHistory(),
                        input.vitalSigns(),
                        input.physicalExam(),
                        input.auxiliaryExam()),
                new CaseResultResponse.Analysis(
                        input.preliminaryDiagnosis(),
                        input.treatmentTaken(),
                        input.medicationUsage(),
                        input.generationNeeds(),
                        ai.content(),
                        ai.symptoms(),
                        ai.medicalTerms(),
                        ai.diagnosisTop1(),
                        ai.diagnosisCandidates(),
                        ai.diagnosisReason(),
                        ai.treatmentAdvice(),
                        ai.modelVersion(),
                        ai.confidence(),
                        ai.lowConfidence(),
                        ai.lowConfidenceReason(),
                        DISCLAIMER),
                attachments(document)
        );
    }

    public CaseDetailResponse toDetail(CaseDocument document) {
        return new CaseDetailResponse(
                document.getCaseId(),
                document.getInput(),
                document.getStatus(),
                document.getCurrentJobId(),
                document.getResult() == null ? null : toResult(document),
                document.getEditedRecord(),
                attachments(document),
                document.getCreatedAt(),
                document.getUpdatedAt()
        );
    }

    public CaseHistoryPageResponse.Item toHistoryItem(CaseDocument document) {
        CaseInput input = document.getInput();
        CaseResult result = document.getResult();
        return new CaseHistoryPageResponse.Item(
                document.getCaseId(),
                input.patientName(),
                input.gender(),
                input.age(),
                input.department(),
                input.chiefComplaint(),
                result == null ? null : result.analysis().diagnosisTop1(),
                input.preliminaryDiagnosis(),
                document.getStatus(),
                document.getCreatedAt(),
                document.getUpdatedAt()
        );
    }

    private List<AttachmentResponse> attachments(CaseDocument document) {
        return document.getAttachments().stream()
                .map(attachment -> toAttachment(document.getCaseId(), attachment))
                .toList();
    }

    private AttachmentResponse toAttachment(String caseId, AttachmentMetadata attachment) {
        return new AttachmentResponse(
                attachment.id(),
                attachment.originalFileName(),
                attachment.mimeType(),
                attachment.size(),
                "/api/v1/cases/" + caseId + "/attachments/" + attachment.id(),
                attachment.parseStatus(),
                attachment.extractedText(),
                attachment.parseError()
        );
    }

    private boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
