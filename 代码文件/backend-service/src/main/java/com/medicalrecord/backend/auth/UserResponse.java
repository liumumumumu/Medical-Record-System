package com.medicalrecord.backend.auth;

public record UserResponse(String id, String username, String displayName, String role) {
}
