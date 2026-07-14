package com.medicalrecord.backend.auth;

public record LoginResponse(
        String token,
        String tokenType,
        long expiresIn,
        UserResponse user
) {
}
