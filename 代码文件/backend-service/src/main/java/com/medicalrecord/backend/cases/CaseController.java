package com.medicalrecord.backend.cases;

import com.medicalrecord.backend.files.StoredFileResource;
import com.medicalrecord.backend.report.ReportDownload;
import com.medicalrecord.backend.report.ReportService;
import com.medicalrecord.backend.security.AuthenticatedUser;
import com.medicalrecord.backend.security.SecurityUtils;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.core.io.Resource;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.nio.charset.StandardCharsets;
import java.util.List;

@Validated
@RestController
@RequestMapping("/api/v1/cases")
public class CaseController {
    private static final MediaType DOCX = MediaType.parseMediaType(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document");

    private final CaseService caseService;
    private final ReportService reportService;

    public CaseController(CaseService caseService, ReportService reportService) {
        this.caseService = caseService;
        this.reportService = reportService;
    }

    @PostMapping(consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<CreateCaseResponse> createJson(
            @Valid @RequestBody CreateCaseRequest request,
            Authentication authentication
    ) {
        AuthenticatedUser user = SecurityUtils.currentUser(authentication);
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(caseService.create(user.userId(), request, List.of()));
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<CreateCaseResponse> createMultipart(
            @Valid @RequestPart("case") CreateCaseRequest request,
            @RequestPart(value = "attachments", required = false) List<MultipartFile> attachments,
            Authentication authentication
    ) {
        AuthenticatedUser user = SecurityUtils.currentUser(authentication);
        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .body(caseService.create(user.userId(), request, attachments));
    }

    @GetMapping
    public CaseHistoryPageResponse history(
            @RequestParam(defaultValue = "") @jakarta.validation.constraints.Size(max = 100) String keyword,
            @RequestParam(defaultValue = "0") @Min(0) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size,
            Authentication authentication
    ) {
        AuthenticatedUser user = SecurityUtils.currentUser(authentication);
        return caseService.history(user.userId(), keyword, page, size);
    }

    @GetMapping("/{caseId}")
    public CaseDetailResponse detail(@PathVariable String caseId, Authentication authentication) {
        AuthenticatedUser user = SecurityUtils.currentUser(authentication);
        return caseService.detail(caseId, user.userId());
    }

    @GetMapping("/{caseId}/result")
    public CaseResultResponse result(@PathVariable String caseId, Authentication authentication) {
        AuthenticatedUser user = SecurityUtils.currentUser(authentication);
        return caseService.result(caseId, user.userId());
    }

    @PostMapping("/{caseId}/retry")
    public ResponseEntity<CreateCaseResponse> retry(@PathVariable String caseId, Authentication authentication) {
        AuthenticatedUser user = SecurityUtils.currentUser(authentication);
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(caseService.retry(caseId, user.userId()));
    }

    @PutMapping("/{caseId}/record")
    public CaseDetailResponse updateRecord(
            @PathVariable String caseId,
            @Valid @RequestBody UpdateRecordRequest request,
            Authentication authentication
    ) {
        AuthenticatedUser user = SecurityUtils.currentUser(authentication);
        return caseService.updateRecord(caseId, user.userId(), request);
    }

    @GetMapping("/{caseId}/attachments/{fileId}")
    public ResponseEntity<Resource> attachment(
            @PathVariable String caseId,
            @PathVariable String fileId,
            Authentication authentication
    ) {
        AuthenticatedUser user = SecurityUtils.currentUser(authentication);
        StoredFileResource file = caseService.attachment(caseId, fileId, user.userId());
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType(file.mimeType()))
                .contentLength(file.size())
                .header(HttpHeaders.CONTENT_DISPOSITION, attachmentDisposition(file.fileName()))
                .body(file.resource());
    }

    @GetMapping("/{caseId}/report")
    public ResponseEntity<Resource> report(@PathVariable String caseId, Authentication authentication) {
        AuthenticatedUser user = SecurityUtils.currentUser(authentication);
        ReportDownload report = reportService.generateOrLoad(caseId, user.userId());
        return ResponseEntity.ok()
                .contentType(DOCX)
                .contentLength(report.size())
                .header(HttpHeaders.CONTENT_DISPOSITION, attachmentDisposition(report.fileName()))
                .body(report.resource());
    }

    private String attachmentDisposition(String fileName) {
        return ContentDisposition.attachment()
                .filename(fileName, StandardCharsets.UTF_8)
                .build()
                .toString();
    }
}
