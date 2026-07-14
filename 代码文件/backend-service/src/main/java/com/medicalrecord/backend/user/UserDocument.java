package com.medicalrecord.backend.user;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

@Document("users")
public class UserDocument {
    @Id
    private String id;

    @Indexed(unique = true)
    private String username;

    private String passwordHash;
    private String displayName;
    private String role;
    private Instant createdAt;

    public UserDocument() {
    }

    public UserDocument(String id, String username, String passwordHash, String role, Instant createdAt) {
        this(id, username, passwordHash, username, role, createdAt);
    }

    public UserDocument(
            String id,
            String username,
            String passwordHash,
            String displayName,
            String role,
            Instant createdAt
    ) {
        this.id = id;
        this.username = username;
        this.passwordHash = passwordHash;
        this.displayName = displayName;
        this.role = role;
        this.createdAt = createdAt;
    }

    public String getId() {
        return id;
    }

    public String getUsername() {
        return username;
    }

    public String getPasswordHash() {
        return passwordHash;
    }

    public String getDisplayName() {
        return displayName == null || displayName.isBlank() ? username : displayName;
    }

    public String getRole() {
        return role;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
