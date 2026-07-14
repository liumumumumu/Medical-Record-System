package com.medicalrecord.backend.jobs;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.Optional;

public interface JobRepository extends MongoRepository<JobDocument, String> {
    Optional<JobDocument> findByJobIdAndOwnerId(String jobId, String ownerId);
}
