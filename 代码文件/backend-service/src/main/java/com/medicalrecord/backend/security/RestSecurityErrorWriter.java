package com.medicalrecord.backend.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.medicalrecord.backend.common.ApiError;
import com.medicalrecord.backend.common.RequestIdFilter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;

@Component
public class RestSecurityErrorWriter {
    private final ObjectMapper objectMapper;

    public RestSecurityErrorWriter(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public void write(
            HttpServletRequest request,
            HttpServletResponse response,
            int status,
            String code,
            String message
    ) throws IOException {
        response.setStatus(status);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        objectMapper.writeValue(response.getOutputStream(), new ApiError(
                code,
                message,
                Map.of(),
                RequestIdFilter.current(request)
        ));
    }
}
