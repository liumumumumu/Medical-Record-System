package com.medicalrecord.backend.security;

import com.medicalrecord.backend.common.ApiException;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;

public final class SecurityUtils {
    private SecurityUtils() {
    }

    public static AuthenticatedUser currentUser(Authentication authentication) {
        if (authentication == null || !(authentication.getPrincipal() instanceof AuthenticatedUser user)) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "UNAUTHORIZED", "请先登录");
        }
        return user;
    }
}
