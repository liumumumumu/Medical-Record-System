package com.medicalrecord.backend.security;

public record AuthenticatedUser(String userId, String username, String role) {
}
