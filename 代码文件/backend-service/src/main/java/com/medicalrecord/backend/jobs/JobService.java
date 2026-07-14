package com.medicalrecord.backend.jobs;

import com.medicalrecord.backend.common.ApiException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

@Service
public class JobService {
    private final JobRepository jobRepository;

    public JobService(JobRepository jobRepository) {
        this.jobRepository = jobRepository;
    }

    public JobResponse getJob(String jobId, String ownerId) {
        JobDocument job = jobRepository.findByJobIdAndOwnerId(jobId, ownerId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "JOB_NOT_FOUND", "任务不存在"));
        return JobResponse.from(job);
    }
}
