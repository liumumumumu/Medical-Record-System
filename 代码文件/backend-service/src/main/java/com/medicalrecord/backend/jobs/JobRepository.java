package com.medicalrecord.backend.jobs;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Optional;

public interface JobRepository extends MongoRepository<JobDocument, String> {
    Optional<JobDocument> findByJobIdAndOwnerId(String jobId, String ownerId);

    List<JobDocument> findByStatusInAndUpdatedAtBefore(Collection<JobStatus> statuses, Instant cutoff);
}
