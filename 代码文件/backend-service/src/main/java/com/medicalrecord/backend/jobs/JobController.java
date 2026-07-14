package com.medicalrecord.backend.jobs;

import com.medicalrecord.backend.security.AuthenticatedUser;
import com.medicalrecord.backend.security.SecurityUtils;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/jobs")
public class JobController {
    private final JobService jobService;

    public JobController(JobService jobService) {
        this.jobService = jobService;
    }

    @GetMapping("/{jobId}")
    public JobResponse getJob(@PathVariable String jobId, Authentication authentication) {
        AuthenticatedUser user = SecurityUtils.currentUser(authentication);
        return jobService.getJob(jobId, user.userId());
    }
}
