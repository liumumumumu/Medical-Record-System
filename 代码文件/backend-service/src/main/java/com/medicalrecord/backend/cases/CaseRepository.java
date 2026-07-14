package com.medicalrecord.backend.cases;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.data.mongodb.repository.Query;

import java.util.Optional;

public interface CaseRepository extends MongoRepository<CaseDocument, String> {
    Optional<CaseDocument> findByCaseIdAndOwnerId(String caseId, String ownerId);

    Page<CaseDocument> findByOwnerId(String ownerId, Pageable pageable);

    @Query("{ 'ownerId': ?0, '$or': ["
            + "{ 'input.patientName': { '$regex': ?1, '$options': 'i' } },"
            + "{ 'input.chiefComplaint': { '$regex': ?1, '$options': 'i' } }"
            + "] }")
    Page<CaseDocument> searchByOwnerId(String ownerId, String escapedKeyword, Pageable pageable);
}
