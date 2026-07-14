package com.medicalrecord.backend.cases;

import java.time.LocalDate;
import java.util.List;

public record CaseInput(
        String patientName,
        Gender gender,
        Integer age,
        Department department,
        LocalDate visitDate,
        String chiefComplaint,
        String presentIllness,
        String pastHistory,
        String allergyHistory,
        String vitalSigns,
        String physicalExam,
        String auxiliaryExam,
        String preliminaryDiagnosis,
        String treatmentTaken,
        String medicationUsage,
        List<GenerationNeed> generationNeeds
) {
    public static CaseInput from(CreateCaseRequest request) {
        return new CaseInput(
                request.patientName(),
                request.gender(),
                request.age(),
                request.department(),
                request.visitDate(),
                request.chiefComplaint(),
                request.presentIllness(),
                request.pastHistory(),
                request.allergyHistory(),
                request.vitalSigns(),
                request.physicalExam(),
                request.auxiliaryExam(),
                request.preliminaryDiagnosis(),
                request.treatmentTaken(),
                request.medicationUsage(),
                request.generationNeeds()
        );
    }

    public CaseInput withAttachmentContext(String attachmentContext) {
        if (attachmentContext == null || attachmentContext.isBlank()) {
            return this;
        }
        String combinedAuxiliaryExam = auxiliaryExam == null || auxiliaryExam.isBlank()
                ? "附件提取内容：\n" + attachmentContext
                : auxiliaryExam + "\n附件提取内容：\n" + attachmentContext;
        return new CaseInput(
                patientName, gender, age, department, visitDate, chiefComplaint, presentIllness,
                pastHistory, allergyHistory, vitalSigns, physicalExam, combinedAuxiliaryExam,
                preliminaryDiagnosis, treatmentTaken, medicationUsage, generationNeeds
        );
    }
}
