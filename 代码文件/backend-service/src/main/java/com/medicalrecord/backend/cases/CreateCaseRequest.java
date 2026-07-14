package com.medicalrecord.backend.cases;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.time.LocalDate;
import java.util.List;

public record CreateCaseRequest(
        @NotBlank(message = "姓名不能为空")
        @Size(max = 30, message = "姓名最多 30 个字符")
        String patientName,

        @NotNull(message = "性别不能为空")
        Gender gender,

        @NotNull(message = "年龄不能为空")
        @Min(value = 0, message = "年龄必须在 0 至 130 之间")
        @Max(value = 130, message = "年龄必须在 0 至 130 之间")
        Integer age,

        Department department,
        LocalDate visitDate,

        @NotBlank(message = "主诉不能为空")
        @Size(max = 200, message = "主诉最多 200 个字符")
        String chiefComplaint,

        @NotBlank(message = "现病史不能为空")
        @Size(max = 1200, message = "现病史最多 1200 个字符")
        String presentIllness,

        @Size(max = 800, message = "既往病史最多 800 个字符")
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
    public CreateCaseRequest {
        pastHistory = pastHistory == null || pastHistory.isBlank() ? "未提供" : pastHistory.strip();
        generationNeeds = generationNeeds == null ? List.of() : List.copyOf(generationNeeds);
    }
}
