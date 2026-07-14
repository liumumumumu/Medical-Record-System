package com.medicalrecord.backend.auth;

import com.medicalrecord.backend.common.ApiException;
import com.medicalrecord.backend.security.AuthenticatedUser;
import com.medicalrecord.backend.security.JwtService;
import com.medicalrecord.backend.user.UserDocument;
import com.medicalrecord.backend.user.UserRepository;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.UUID;

@Service
public class AuthService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public AuthService(
            UserRepository userRepository,
            PasswordEncoder passwordEncoder,
            JwtService jwtService
    ) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
    }

    public LoginResponse login(LoginRequest request) {
        UserDocument user = userRepository.findByUsername(request.username())
                .orElseThrow(this::invalidCredentials);
        if (!passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            throw invalidCredentials();
        }
        AuthenticatedUser authenticatedUser = new AuthenticatedUser(
                user.getId(), user.getUsername(), user.getRole());
        return response(user, authenticatedUser);
    }

    public LoginResponse register(RegisterRequest request) {
        if (userRepository.findByUsername(request.username()).isPresent()) {
            throw new ApiException(HttpStatus.CONFLICT, "USERNAME_EXISTS", "账号已存在");
        }
        UserDocument user = new UserDocument(
                "user_" + UUID.randomUUID().toString().replace("-", ""),
                request.username(),
                passwordEncoder.encode(request.password()),
                request.displayName(),
                "USER",
                Instant.now()
        );
        try {
            user = userRepository.save(user);
        } catch (DuplicateKeyException exception) {
            throw new ApiException(HttpStatus.CONFLICT, "USERNAME_EXISTS", "账号已存在");
        }
        AuthenticatedUser authenticatedUser = new AuthenticatedUser(
                user.getId(), user.getUsername(), user.getRole());
        return response(user, authenticatedUser);
    }

    public UserResponse currentUser(AuthenticatedUser authenticatedUser) {
        UserDocument user = userRepository.findById(authenticatedUser.userId())
                .orElseThrow(this::invalidCredentials);
        return new UserResponse(
                user.getId(), user.getUsername(), user.getDisplayName(), user.getRole());
    }

    private LoginResponse response(UserDocument user, AuthenticatedUser authenticatedUser) {
        return new LoginResponse(
                jwtService.createToken(authenticatedUser),
                "Bearer",
                jwtService.expiresInSeconds(),
                new UserResponse(
                        user.getId(), user.getUsername(), user.getDisplayName(), user.getRole())
        );
    }

    private ApiException invalidCredentials() {
        return new ApiException(HttpStatus.UNAUTHORIZED, "UNAUTHORIZED", "账号或密码错误");
    }
}
