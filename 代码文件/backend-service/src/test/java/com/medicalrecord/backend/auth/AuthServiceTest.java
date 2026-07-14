package com.medicalrecord.backend.auth;

import com.medicalrecord.backend.security.JwtService;
import com.medicalrecord.backend.user.UserDocument;
import com.medicalrecord.backend.user.UserRepository;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class AuthServiceTest {

    @Test
    void registersUserAndReturnsSession() {
        UserRepository repository = mock(UserRepository.class);
        PasswordEncoder encoder = mock(PasswordEncoder.class);
        JwtService jwtService = mock(JwtService.class);
        when(repository.findByUsername("doctor_new")).thenReturn(Optional.empty());
        when(encoder.encode("demo123")).thenReturn("hash");
        when(repository.save(any(UserDocument.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(jwtService.createToken(any())).thenReturn("token");
        when(jwtService.expiresInSeconds()).thenReturn(7200L);

        LoginResponse response = new AuthService(repository, encoder, jwtService).register(
                new RegisterRequest("doctor_new", "demo123", "新医生")
        );

        assertThat(response.token()).isEqualTo("token");
        assertThat(response.user().username()).isEqualTo("doctor_new");
        assertThat(response.user().displayName()).isEqualTo("新医生");
    }
}
