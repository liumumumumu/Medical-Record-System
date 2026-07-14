package com.medicalrecord.backend.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI medicalRecordOpenApi() {
        return new OpenAPI().info(new Info()
                .title("医疗病历生成与分析系统 API")
                .version("v1")
                .description("病例录入、异步 AI 分析、历史记录、附件与 DOCX 报告接口"));
    }
}
