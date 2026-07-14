package com.medicalrecord.backend.auth;

import com.medicalrecord.backend.security.AuthenticatedUser;
import com.medicalrecord.backend.security.SecurityUtils;
import com.medicalrecord.backend.security.TokenRevocationService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {
    private final AuthService authService;
    private final TokenRevocationService tokenRevocationService;

    public AuthController(AuthService authService, TokenRevocationService tokenRevocationService) {
        this.authService = authService;
        this.tokenRevocationService = tokenRevocationService;
    }

    @PostMapping("/login")
    public LoginResponse login(@Valid @RequestBody LoginRequest request) {
        return authService.login(request);
    }

    @PostMapping("/register")
    public LoginResponse register(@Valid @RequestBody RegisterRequest request) {
        return authService.register(request);
    }

    @GetMapping("/me")
    public UserResponse me(Authentication authentication) {
        AuthenticatedUser user = SecurityUtils.currentUser(authentication);
        return authService.currentUser(user);
    }

    @PostMapping("/logout")
    public ResponseEntity<Void> logout(HttpServletRequest request) {
        String authorization = request.getHeader("Authorization");
        if (authorization != null && authorization.startsWith("Bearer ")) {
            tokenRevocationService.revoke(authorization.substring(7));
        }
        return ResponseEntity.noContent().build();
    }
}
