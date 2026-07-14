package com.medicalrecord.backend.cases;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record UpdateRecordRequest(
        @NotBlank(message = "病历内容不能为空")
        @Size(max = 20000, message = "病历内容最多 20000 个字符")
        String editedRecord
) {
}
