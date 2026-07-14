package com.medicalrecord.backend.report;

import org.springframework.core.io.Resource;

public record ReportDownload(Resource resource, String fileName, long size) {
}
