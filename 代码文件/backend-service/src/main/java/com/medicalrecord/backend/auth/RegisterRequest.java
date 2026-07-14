package com.medicalrecord.backend.auth;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record RegisterRequest(
        @NotBlank(message = "账号不能为空")
        @Pattern(regexp = "[A-Za-z0-9_]{3,30}", message = "账号需为 3-30 位字母、数字或下划线")
        String username,

        @NotBlank(message = "密码不能为空")
        @Size(min = 6, max = 72, message = "密码长度需为 6-72 位")
        @ValidBcryptPassword
        String password,

        @NotBlank(message = "显示名称不能为空")
        @Size(max = 30, message = "显示名称最多 30 个字符")
        String displayName
) {
}
