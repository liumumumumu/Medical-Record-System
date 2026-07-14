package com.medicalrecord.backend.report;

import com.medicalrecord.backend.ai.AiAnalysisResult;
import com.medicalrecord.backend.cases.CaseDocument;
import com.medicalrecord.backend.cases.CaseInput;
import com.medicalrecord.backend.cases.CaseMapper;
import com.medicalrecord.backend.cases.CaseRepository;
import com.medicalrecord.backend.common.ApiException;
import com.medicalrecord.backend.files.FileStorageService;
import org.apache.poi.xwpf.usermodel.ParagraphAlignment;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFRun;
import org.springframework.core.io.UrlResource;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.OutputStream;
import java.net.MalformedURLException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;

@Service
public class ReportService {
    private final CaseRepository caseRepository;
    private final FileStorageService fileStorageService;

    public ReportService(CaseRepository caseRepository, FileStorageService fileStorageService) {
        this.caseRepository = caseRepository;
        this.fileStorageService = fileStorageService;
    }

    public synchronized ReportDownload generateOrLoad(String caseId, String ownerId) {
        CaseDocument caseDocument = caseRepository.findByCaseIdAndOwnerId(caseId, ownerId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "CASE_NOT_FOUND", "病例不存在"));
        if (caseDocument.getResult() == null) {
            throw new ApiException(HttpStatus.CONFLICT, "RESULT_NOT_READY", "分析结果尚未生成");
        }

        ReportMetadata cached = caseDocument.getReport();
        if (cached != null && cached.sourceRevision() == caseDocument.getContentRevision()) {
            Path cachedPath = fileStorageService.resolveReport(cached.path());
            if (Files.isRegularFile(cachedPath)) {
                return asDownload(cachedPath, cached.fileName());
            }
        }

        if (cached != null) {
            fileStorageService.deleteReport(cached.path());
        }
        return generate(caseDocument);
    }

    private ReportDownload generate(CaseDocument caseDocument) {
        String directoryName = caseDocument.getCaseId();
        Path directory = fileStorageService.reportRoot().resolve(directoryName).normalize();
        if (!directory.startsWith(fileStorageService.reportRoot())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "INVALID_FILE_PATH", "报告路径不合法");
        }
        String storedName = "revision-" + caseDocument.getContentRevision() + ".docx";
        Path target = directory.resolve(storedName).normalize();
        String downloadName = safeDownloadName(caseDocument.getInput().patientName()) + "-病历报告.docx";

        try {
            Files.createDirectories(directory);
            try (XWPFDocument document = buildDocument(caseDocument);
                 OutputStream output = Files.newOutputStream(target)) {
                document.write(output);
            }
            String relativePath = fileStorageService.reportRoot().relativize(target).toString();
            caseDocument.setReport(new ReportMetadata(
                    downloadName,
                    relativePath,
                    caseDocument.getContentRevision(),
                    Instant.now()
            ));
            caseDocument.touch(Instant.now());
            caseRepository.save(caseDocument);
            return asDownload(target, downloadName);
        } catch (IOException exception) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "REPORT_GENERATION_FAILED", "报告生成失败");
        }
    }

    private XWPFDocument buildDocument(CaseDocument caseDocument) {
        CaseInput input = caseDocument.getInput();
        AiAnalysisResult analysis = caseDocument.getResult().analysis();
        XWPFDocument document = new XWPFDocument();

        XWPFParagraph title = document.createParagraph();
        title.setAlignment(ParagraphAlignment.CENTER);
        XWPFRun titleRun = title.createRun();
        titleRun.setText("医疗病历生成与分析报告");
        titleRun.setBold(true);
        titleRun.setFontFamily("宋体");
        titleRun.setFontSize(18);

        addSection(document, "一、患者摘要",
                "姓名：" + input.patientName() + "\n"
                        + "性别：" + (input.gender().value().equals("male") ? "男" : "女") + "\n"
                        + "年龄：" + input.age() + " 岁\n"
                        + "科室：" + departmentText(input) + "\n"
                        + "就诊日期：" + value(input.visitDate() == null ? null : input.visitDate().toString()));
        addSection(document, "二、原始病历信息",
                "主诉：" + value(input.chiefComplaint()) + "\n"
                        + "现病史：" + value(input.presentIllness()) + "\n"
                        + "既往病史：" + value(input.pastHistory()) + "\n"
                        + "过敏史：" + value(input.allergyHistory()) + "\n"
                        + "生命体征：" + value(input.vitalSigns()) + "\n"
                        + "体格检查：" + value(input.physicalExam()) + "\n"
                        + "辅助检查：" + value(input.auxiliaryExam()));
        addSection(document, "三、结构化病历",
                hasText(caseDocument.getEditedRecord()) ? caseDocument.getEditedRecord() : analysis.generatedRecord());
        addSection(document, "四、辅助分析",
                "识别症状：" + String.join("、", analysis.symptoms()) + "\n"
                        + "医学术语：" + String.join("、", analysis.medicalTerms()) + "\n"
                        + "辅助判断：" + value(analysis.diagnosisTop1()) + "\n"
                        + "候选方向：" + String.join("、", analysis.diagnosisCandidates()) + "\n"
                        + "判断依据：" + value(analysis.diagnosisReason()) + "\n"
                        + "处理建议：" + treatmentAdvice(analysis.treatmentAdvice()));
        addSection(document, "五、使用说明", CaseMapper.DISCLAIMER);
        return document;
    }

    private void addSection(XWPFDocument document, String heading, String content) {
        XWPFParagraph headingParagraph = document.createParagraph();
        XWPFRun headingRun = headingParagraph.createRun();
        headingRun.setText(heading);
        headingRun.setBold(true);
        headingRun.setFontFamily("宋体");
        headingRun.setFontSize(13);

        XWPFParagraph contentParagraph = document.createParagraph();
        String[] lines = value(content).split("\\n", -1);
        for (int i = 0; i < lines.length; i++) {
            XWPFRun run = contentParagraph.createRun();
            run.setText(lines[i]);
            run.setFontFamily("宋体");
            run.setFontSize(11);
            if (i < lines.length - 1) {
                run.addBreak();
            }
        }
    }

    private ReportDownload asDownload(Path path, String fileName) {
        try {
            return new ReportDownload(new UrlResource(path.toUri()), fileName, Files.size(path));
        } catch (MalformedURLException exception) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "REPORT_GENERATION_FAILED", "报告路径不可用");
        } catch (IOException exception) {
            throw new ApiException(HttpStatus.NOT_FOUND, "FILE_NOT_FOUND", "报告文件不存在");
        }
    }

    private String safeDownloadName(String patientName) {
        String value = patientName == null ? "患者" : patientName.replaceAll("[\\\\/:*?\"<>|]", "_").trim();
        return value.isBlank() ? "患者" : value;
    }

    private String departmentText(CaseInput input) {
        if (input.department() == null) {
            return "未提供";
        }
        return switch (input.department().value()) {
            case "internal" -> "内科";
            case "surgery" -> "外科";
            case "pediatrics" -> "儿科";
            case "emergency" -> "急诊";
            default -> "其他";
        };
    }

    private String treatmentAdvice(String advice) {
        if (!hasText(advice)) {
            return "未提供";
        }
        String sanitized = advice
                .replace("本结果仅用于课程演示和辅助分析，不替代医生诊断。", "")
                .replace("本结果仅供课程演示，不替代执业医师判断。", "")
                .replace(CaseMapper.DISCLAIMER, "")
                .strip();
        return sanitized.isBlank() ? "未提供" : sanitized;
    }

    private String value(String value) {
        return hasText(value) ? value : "未提供";
    }

    private boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
