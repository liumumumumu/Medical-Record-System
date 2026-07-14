package com.medicalrecord.backend.security;

import com.medicalrecord.backend.config.JwtProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import java.util.UUID;

@Service
public class JwtService {
    private final JwtProperties properties;
    private final SecretKey key;

    public JwtService(JwtProperties properties) {
        this.properties = properties;
        this.key = Keys.hmacShaKeyFor(properties.secret().getBytes(StandardCharsets.UTF_8));
    }

    public String createToken(AuthenticatedUser user) {
        Instant issuedAt = Instant.now();
        Instant expiresAt = issuedAt.plus(properties.expiration());
        return Jwts.builder()
                .id(UUID.randomUUID().toString())
                .subject(user.userId())
                .claim("username", user.username())
                .claim("role", user.role())
                .issuedAt(Date.from(issuedAt))
                .expiration(Date.from(expiresAt))
                .signWith(key)
                .compact();
    }

    public AuthenticatedUser parseToken(String token) {
        Claims claims = claims(token);
        return new AuthenticatedUser(
                claims.getSubject(),
                claims.get("username", String.class),
                claims.get("role", String.class)
        );
    }

    public Instant expiresAt(String token) {
        return claims(token).getExpiration().toInstant();
    }

    private Claims claims(String token) {
        return Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    public long expiresInSeconds() {
        return properties.expiration().toSeconds();
    }
}
