package com.medicalrecord.backend.ai;

public class AiServiceException extends RuntimeException {
    private final String code;

    public AiServiceException(String code, String message) {
        super(message);
        this.code = code;
    }

    public String getCode() {
        return code;
    }
}
