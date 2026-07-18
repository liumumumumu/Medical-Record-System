package com.medicalrecord.backend.report;

import com.medicalrecord.backend.ai.AiAnalysisResult;
import com.medicalrecord.backend.ai.RecordGenerationInfo;
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
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.util.unit.DataSize;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.nio.file.StandardCopyOption;
import java.math.BigInteger;

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
                    .collect(java.util.stream.Collectors.joining("\n"))
                    + "\n"
                    + document.getTables().stream()
                    .map(table -> table.getText())
                    .collect(java.util.stream.Collectors.joining("\n"));
            assertThat(text).contains(
                    "人工编辑后的病历内容",
                    "就诊科室",
                    "内科",
                    "医生签名",
                    "AI 辅助分析（与正式病历分离）",
                    CaseMapper.DISCLAIMER
            );
            assertThat(countOccurrences(text, CaseMapper.DISCLAIMER)).isEqualTo(1);
            assertThat(document.getDocument().getBody().getSectPr().getPgSz().getW())
                    .isEqualTo(BigInteger.valueOf(12240));
            assertThat(document.getDocument().getBody().getSectPr().getPgMar().getLeft())
                    .isEqualTo(BigInteger.valueOf(1440));
            assertThat(document.getTables().getFirst().getCTTbl().getTblPr().getTblW().getW())
                    .isEqualTo(BigInteger.valueOf(9360));
            assertThat(document.getTables().getFirst().getCTTbl().getTblPr().getTblInd().getW())
                    .isEqualTo(BigInteger.valueOf(120));
        }
    }

    @Test
    void writesRepresentativePreviewWhenRequested() throws Exception {
        String previewPath = System.getProperty("record.preview.path", "").trim();
        Assumptions.assumeTrue(!previewPath.isBlank());
        CaseRepository repository = mock(CaseRepository.class);
        CaseDocument caseDocument = previewCase();
        when(repository.findByCaseIdAndOwnerId("preview_1", "user_1"))
                .thenReturn(Optional.of(caseDocument));
        when(repository.save(any(CaseDocument.class))).thenAnswer(invocation -> invocation.getArgument(0));
        ReportDownload download = new ReportService(repository, storage())
                .generateOrLoad("preview_1", "user_1");
        Path target = Path.of(previewPath).toAbsolutePath();
        Files.createDirectories(target.getParent());
        try (var input = download.resource().getInputStream()) {
            Files.copy(input, target, StandardCopyOption.REPLACE_EXISTING);
        }
        assertThat(target).isRegularFile();
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

    private CaseDocument previewCase() {
        CaseDocument document = new CaseDocument(
                "preview_1",
                "user_1",
                new CaseInput(
                        "刘某", Gender.FEMALE, 72, Department.INTERNAL, LocalDate.of(2026, 7, 16),
                        "慢性咳嗽15年，双下肢水肿半年，加重1周。",
                        "患者慢性咳嗽15年，活动后气急10余年。1周前感冒后咳嗽、气急加重，咯黄痰，双下肢再度水肿。",
                        "35年前行阑尾切除术；40年前有肺结核史并接受抗结核治疗。",
                        "否认药物过敏史。",
                        "T 36.5℃，P 98次/分，R 28次/分，BP 130/70mmHg。",
                        "口唇轻度发绀，颈静脉怒张，桶状胸；两肺呼吸音低，右下肺细湿啰音；双下肢Ⅰ度凹陷性水肿。",
                        "白细胞8.9×10^9/L；胸片示两肺透亮度增加、肺纹理紊乱；心电图示持续心房颤动。",
                        "慢性支气管炎急性发作；慢性阻塞性肺气肿；慢性肺源性心脏病。",
                        "当地医院已给予抗感染及利尿治疗1周。",
                        "阿米卡星、氢氯噻嗪（既往已使用）。",
                        List.of()
                ),
                List.of(),
                "job_preview",
                JobStatus.COMPLETED,
                Instant.now()
        );
        String generatedRecord = """
                住院病历

                一、基本信息
                姓名：刘某
                性别：女
                年龄：72岁
                就诊科室：内科
                就诊日期：2026-07-16

                二、主诉
                慢性咳嗽15年，双下肢水肿半年，加重1周。

                三、现病史
                患者慢性咳嗽15年，活动后气急10余年。1周前感冒后咳嗽、气急加重，咯黄痰，双下肢再度水肿。

                四、既往史
                35年前行阑尾切除术；40年前有肺结核史并接受抗结核治疗。

                五、过敏史
                否认药物过敏史。

                六、生命体征与体格检查
                生命体征：T 36.5℃，P 98次/分，R 28次/分，BP 130/70mmHg。
                体格检查：口唇轻度发绀，颈静脉怒张，桶状胸；两肺呼吸音低，右下肺细湿啰音；双下肢Ⅰ度凹陷性水肿。

                七、辅助检查
                白细胞8.9×10^9/L；胸片示两肺透亮度增加、肺纹理紊乱；心电图示持续心房颤动。

                八、初步诊断（医生输入）
                慢性支气管炎急性发作；慢性阻塞性肺气肿；慢性肺源性心脏病。

                九、既往治疗记录（患者已接受）
                当地医院已给予抗感染及利尿治疗1周。

                十、用药记录（患者已使用）
                阿米卡星、氢氯噻嗪（既往已使用）。
                """;
        document.setResult(new CaseResult(new AiAnalysisResult(
                generatedRecord,
                List.of("慢性咳嗽", "气急", "下肢水肿"),
                List.of("肺气肿", "心房颤动"),
                "慢性阻塞性肺疾病相关表现",
                List.of("慢性支气管炎急性发作", "慢性肺源性心脏病"),
                "症状、体征及检查表现支持上述辅助方向，仍需执业医师结合完整资料判断。",
                "建议由临床医生结合血气分析、肺功能及心功能检查进一步评估。",
                "课程项目辅助分析",
                "diagnosis-2.0.0",
                0.86,
                false,
                null,
                new RecordGenerationInfo(
                        "transformer",
                        "IDEA-CCNL/Randeng-T5-77M-MultiTask-Chinese",
                        "record-gen-t5-v1.2.0",
                        false,
                        List.of()
                )
        ), Instant.now()));
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
