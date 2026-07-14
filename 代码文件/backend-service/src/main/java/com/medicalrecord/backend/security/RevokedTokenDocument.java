package com.medicalrecord.backend.security;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

@Document("revoked_tokens")
public class RevokedTokenDocument {
    @Id
    private String tokenHash;

    @Indexed(expireAfter = "0s")
    private Instant expiresAt;

    public RevokedTokenDocument() {
    }

    public RevokedTokenDocument(String tokenHash, Instant expiresAt) {
        this.tokenHash = tokenHash;
        this.expiresAt = expiresAt;
    }

    public String getTokenHash() {
        return tokenHash;
    }

    public Instant getExpiresAt() {
        return expiresAt;
    }
}
