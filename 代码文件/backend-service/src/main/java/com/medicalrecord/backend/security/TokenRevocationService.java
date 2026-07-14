package com.medicalrecord.backend.security;

import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

@Service
public class TokenRevocationService {
    private final RevokedTokenRepository repository;
    private final JwtService jwtService;

    public TokenRevocationService(RevokedTokenRepository repository, JwtService jwtService) {
        this.repository = repository;
        this.jwtService = jwtService;
    }

    public void revoke(String token) {
        repository.save(new RevokedTokenDocument(hash(token), jwtService.expiresAt(token)));
    }

    public boolean isRevoked(String token) {
        return repository.existsById(hash(token));
    }

    private String hash(String token) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(token.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }
}
