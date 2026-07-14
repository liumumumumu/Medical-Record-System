package com.medicalrecord.backend.report;

import com.medicalrecord.backend.ai.AiAnalysisResult;
import com.medicalrecord.backend.cases.CaseDocument;
import com.medicalrecord.backend.cases.CaseInput;
import com.medicalrecord.backend.cases.CaseRepository;
import com.medicalrecord.backend.cases.CaseResult;
import com.medicalrecord.backend.cases.CaseMapper;
import com.medicalrecord.backend.cases.Department;
import com.medicalrecord.backend.cases.Gender;
import com.medicalrecord.backend.config.StorageProperties;
import com.medicalrecord.backend.files.FileStorageService;
import com.medicalrecord.backend.jobs.JobStatus;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.util.unit.DataSize;

import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class ReportServiceTest {
    @TempDir
    Path tempDir;

    @Test
    void docxContainsEditedRecordAndDisclaimer() throws Exception {
        CaseRepository repository = mock(CaseRepository.class);
        CaseDocument caseDocument = completedCase();
        caseDocument.setEditedRecord("人工编辑后的病历内容");
        caseDocument.incrementContentRevision();
        when(repository.findByCaseIdAndOwnerId("case_1", "user_1")).thenReturn(Optional.of(caseDocument));
        when(repository.save(any(CaseDocument.class))).thenAnswer(invocation -> invocation.getArgument(0));
        FileStorageService storage = storage();
        ReportService service = new ReportService(repository, storage);

        ReportDownload download = service.generateOrLoad("case_1", "user_1");

        try (XWPFDocument document = new XWPFDocument(download.resource().getInputStream())) {
            String text = document.getParagraphs().stream()
                    .map(paragraph -> paragraph.getText())
                    .collect(java.util.stream.Collectors.joining("\n"));
            assertThat(text).contains("人工编辑后的病历内容", "科室：内科", CaseMapper.DISCLAIMER);
            assertThat(countOccurrences(text, CaseMapper.DISCLAIMER)).isEqualTo(1);
        }
    }

    private CaseDocument completedCase() {
        CaseDocument document = new CaseDocument(
                "case_1",
                "user_1",
                new CaseInput(
                        "张某", Gender.MALE, 32, Department.INTERNAL, null,
                        "发热咳嗽", "发热咳嗽 3 天", "无", "无",
                        null, null, null, null, null, null, List.of()),
                List.of(),
                "job_1",
                JobStatus.COMPLETED,
                Instant.now()
        );
        document.setResult(new CaseResult(new AiAnalysisResult(
                "AI 生成病历", List.of("发热"), List.of("白细胞"),
                "上呼吸道感染", List.of("上呼吸道感染"), "判断依据", "处理建议",
                "综合分析", "test-1.0", 0.82, false, null), Instant.now()));
        return document;
    }

    private FileStorageService storage() {
        FileStorageService service = new FileStorageService(new StorageProperties(
                tempDir.resolve("uploads"),
                tempDir.resolve("reports"),
                DataSize.ofMegabytes(10),
                DataSize.ofMegabytes(30),
                5
        ));
        service.initialize();
        return service;
    }

    private long countOccurrences(String text, String target) {
        return text.lines().filter(line -> line.contains(target)).count();
    }
}
