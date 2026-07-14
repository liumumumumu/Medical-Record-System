package com.medicalrecord.backend.security;

import org.springframework.data.mongodb.repository.MongoRepository;

public interface RevokedTokenRepository extends MongoRepository<RevokedTokenDocument, String> {
}
