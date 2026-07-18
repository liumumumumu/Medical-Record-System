package com.medicalrecord.backend.report;

import com.medicalrecord.backend.ai.AiAnalysisResult;
import com.medicalrecord.backend.ai.RecordGenerationInfo;
import com.medicalrecord.backend.cases.CaseDocument;
import com.medicalrecord.backend.cases.CaseInput;
import com.medicalrecord.backend.cases.CaseMapper;
import com.medicalrecord.backend.cases.CaseRepository;
import com.medicalrecord.backend.common.ApiException;
import com.medicalrecord.backend.files.FileStorageService;
import org.apache.poi.wp.usermodel.HeaderFooterType;
import org.apache.poi.xwpf.usermodel.LineSpacingRule;
import org.apache.poi.xwpf.usermodel.ParagraphAlignment;
import org.apache.poi.xwpf.usermodel.TableRowAlign;
import org.apache.poi.xwpf.usermodel.TextAlignment;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFFooter;
import org.apache.poi.xwpf.usermodel.XWPFHeader;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFRun;
import org.apache.poi.xwpf.usermodel.XWPFTable;
import org.apache.poi.xwpf.usermodel.XWPFTableCell;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTBorder;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTPageMar;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTPageSz;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTPPr;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTR;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTShd;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTSimpleField;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTSectPr;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTblBorders;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTblGrid;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTblGridCol;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTblLayoutType;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTblPr;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTblWidth;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTcPr;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.STBorder;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.STTblLayoutType;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.STTblWidth;
import org.springframework.core.io.UrlResource;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.OutputStream;
import java.math.BigInteger;
import java.net.MalformedURLException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;

@Service
public class ReportService {
    // standard_business_brief preset; Chinese font is a named 宋体 override.
    private static final String CHINESE_FONT = "宋体";
    private static final String HEADING_BLUE = "2E74B5";
    private static final String DARK_BLUE = "1F4D78";
    private static final String MUTED = "666666";
    private static final String TABLE_FILL = "F2F4F7";
    private static final String TABLE_BORDER = "D7DCE2";
    private static final int CONTENT_WIDTH_DXA = 9360;
    private static final int TABLE_INDENT_DXA = 120;
    private static final int[] PATIENT_TABLE_WIDTHS = {1200, 3480, 1200, 3480};

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
        String downloadName = safeDownloadName(caseDocument.getInput().patientName()) + "-住院病历.docx";

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
        configurePage(document);
        configureDocumentProperties(document, caseDocument);
        addRunningHeaderAndFooter(document);

        addTitleBlock(document);
        addPatientTable(document, input, analysis.recordGeneration());
        addHeading(document, "病历正文", 16, HEADING_BLUE, 16, 8);
        String officialRecord = hasText(caseDocument.getEditedRecord())
                ? caseDocument.getEditedRecord()
                : analysis.generatedRecord();
        addGeneratedRecord(document, officialRecord);
        addSignature(document);

        XWPFParagraph pageBreakHeading = addHeading(
                document,
                "AI 辅助分析（与正式病历分离）",
                16,
                HEADING_BLUE,
                16,
                8
        );
        pageBreakHeading.setPageBreak(true);
        addGenerationProvenance(document, analysis.recordGeneration());
        addAnalysisField(document, "识别症状", joinOrMissing(analysis.symptoms()));
        addAnalysisField(document, "医学术语", joinOrMissing(analysis.medicalTerms()));
        addAnalysisField(document, "辅助判断", value(analysis.diagnosisTop1()));
        addAnalysisField(document, "候选方向", joinOrMissing(analysis.diagnosisCandidates()));
        addAnalysisField(document, "判断依据", value(analysis.diagnosisReason()));
        addAnalysisField(document, "处理建议", treatmentAdvice(analysis.treatmentAdvice()));

        addHeading(document, "课程项目使用说明", 13, DARK_BLUE, 12, 6);
        addBodyParagraph(document, CaseMapper.DISCLAIMER, true);
        return document;
    }

    private void configurePage(XWPFDocument document) {
        CTSectPr section = document.getDocument().getBody().getSectPr();
        if (section == null) {
            section = document.getDocument().getBody().addNewSectPr();
        }
        CTPageSz size = section.getPgSz();
        if (size == null) {
            size = section.addNewPgSz();
        }
        size.setW(BigInteger.valueOf(12240));
        size.setH(BigInteger.valueOf(15840));
        CTPageMar margins = section.getPgMar();
        if (margins == null) {
            margins = section.addNewPgMar();
        }
        margins.setTop(BigInteger.valueOf(1440));
        margins.setRight(BigInteger.valueOf(1440));
        margins.setBottom(BigInteger.valueOf(1440));
        margins.setLeft(BigInteger.valueOf(1440));
        margins.setHeader(BigInteger.valueOf(708));
        margins.setFooter(BigInteger.valueOf(708));
    }

    private void configureDocumentProperties(XWPFDocument document, CaseDocument caseDocument) {
        document.getProperties().getCoreProperties().setTitle("住院病历");
        document.getProperties().getCoreProperties().setCreator("医疗病历生成与分析系统");
        document.getProperties().getCoreProperties().setDescription(
                "病例编号：" + caseDocument.getCaseId() + "；正式病历与 AI 辅助分析分栏呈现。"
        );
    }

    private void addRunningHeaderAndFooter(XWPFDocument document) {
        XWPFHeader header = document.createHeader(HeaderFooterType.DEFAULT);
        XWPFParagraph headerParagraph = header.createParagraph();
        headerParagraph.setAlignment(ParagraphAlignment.LEFT);
        headerParagraph.setSpacingAfter(0);
        XWPFRun headerRun = headerParagraph.createRun();
        setRun(headerRun, "住院病历 · 医疗病历生成与分析系统", 9, false, MUTED);

        XWPFFooter footer = document.createFooter(HeaderFooterType.DEFAULT);
        XWPFParagraph footerParagraph = footer.createParagraph();
        footerParagraph.setAlignment(ParagraphAlignment.RIGHT);
        XWPFRun prefix = footerParagraph.createRun();
        setRun(prefix, "第 ", 9, false, MUTED);
        CTSimpleField pageField = footerParagraph.getCTP().addNewFldSimple();
        pageField.setInstr("PAGE");
        CTR fieldRun = pageField.addNewR();
        fieldRun.addNewT().setStringValue("1");
        XWPFRun suffix = footerParagraph.createRun();
        setRun(suffix, " 页", 9, false, MUTED);
    }

    private void addTitleBlock(XWPFDocument document) {
        XWPFParagraph title = document.createParagraph();
        title.setAlignment(ParagraphAlignment.CENTER);
        title.setSpacingBefore(0);
        title.setSpacingAfter(80);
        title.setKeepNext(true);
        XWPFRun titleRun = title.createRun();
        setRun(titleRun, "住院病历", 22, true, "000000");

        XWPFParagraph subtitle = document.createParagraph();
        subtitle.setAlignment(ParagraphAlignment.CENTER);
        subtitle.setSpacingBefore(0);
        subtitle.setSpacingAfter(320);
        subtitle.setKeepNext(true);
        XWPFRun subtitleRun = subtitle.createRun();
        setRun(subtitleRun, "医疗病历生成与分析系统 · 课程项目", 11, false, MUTED);
    }

    private void addPatientTable(
            XWPFDocument document,
            CaseInput input,
            RecordGenerationInfo generation
    ) {
        XWPFTable table = document.createTable(3, 4);
        configureFixedTable(table, PATIENT_TABLE_WIDTHS);
        setCell(table.getRow(0).getCell(0), "姓名", true, PATIENT_TABLE_WIDTHS[0]);
        setCell(table.getRow(0).getCell(1), input.patientName(), false, PATIENT_TABLE_WIDTHS[1]);
        setCell(table.getRow(0).getCell(2), "性别", true, PATIENT_TABLE_WIDTHS[2]);
        setCell(table.getRow(0).getCell(3), input.gender().value().equals("male") ? "男" : "女", false,
                PATIENT_TABLE_WIDTHS[3]);
        setCell(table.getRow(1).getCell(0), "年龄", true, PATIENT_TABLE_WIDTHS[0]);
        setCell(table.getRow(1).getCell(1), input.age() + " 岁", false, PATIENT_TABLE_WIDTHS[1]);
        setCell(table.getRow(1).getCell(2), "就诊科室", true, PATIENT_TABLE_WIDTHS[2]);
        setCell(table.getRow(1).getCell(3), departmentText(input), false, PATIENT_TABLE_WIDTHS[3]);
        setCell(table.getRow(2).getCell(0), "就诊日期", true, PATIENT_TABLE_WIDTHS[0]);
        setCell(table.getRow(2).getCell(1), value(input.visitDate() == null ? null : input.visitDate().toString()), false,
                PATIENT_TABLE_WIDTHS[1]);
        setCell(table.getRow(2).getCell(2), "生成方式", true, PATIENT_TABLE_WIDTHS[2]);
        setCell(table.getRow(2).getCell(3), generationLabel(generation), false, PATIENT_TABLE_WIDTHS[3]);
        XWPFParagraph spacer = document.createParagraph();
        spacer.setSpacingAfter(0);
    }

    private void configureFixedTable(XWPFTable table, int[] widths) {
        table.setTableAlignment(TableRowAlign.LEFT);
        table.setWidth(CONTENT_WIDTH_DXA);
        table.setCellMargins(80, 120, 80, 120);
        table.setInsideHBorder(XWPFTable.XWPFBorderType.SINGLE, 4, 0, TABLE_BORDER);
        table.setInsideVBorder(XWPFTable.XWPFBorderType.SINGLE, 4, 0, TABLE_BORDER);
        table.setTopBorder(XWPFTable.XWPFBorderType.SINGLE, 4, 0, TABLE_BORDER);
        table.setBottomBorder(XWPFTable.XWPFBorderType.SINGLE, 4, 0, TABLE_BORDER);
        table.setLeftBorder(XWPFTable.XWPFBorderType.SINGLE, 4, 0, TABLE_BORDER);
        table.setRightBorder(XWPFTable.XWPFBorderType.SINGLE, 4, 0, TABLE_BORDER);

        CTTblPr properties = table.getCTTbl().getTblPr();
        if (properties == null) {
            properties = table.getCTTbl().addNewTblPr();
        }
        CTTblWidth tableWidth = properties.getTblW();
        if (tableWidth == null) {
            tableWidth = properties.addNewTblW();
        }
        tableWidth.setType(STTblWidth.DXA);
        tableWidth.setW(BigInteger.valueOf(CONTENT_WIDTH_DXA));
        CTTblWidth indent = properties.getTblInd();
        if (indent == null) {
            indent = properties.addNewTblInd();
        }
        indent.setType(STTblWidth.DXA);
        indent.setW(BigInteger.valueOf(TABLE_INDENT_DXA));
        CTTblLayoutType layout = properties.getTblLayout();
        if (layout == null) {
            layout = properties.addNewTblLayout();
        }
        layout.setType(STTblLayoutType.FIXED);

        CTTblGrid grid = table.getCTTbl().getTblGrid();
        if (grid == null) {
            grid = table.getCTTbl().addNewTblGrid();
        } else {
            while (grid.sizeOfGridColArray() > 0) {
                grid.removeGridCol(0);
            }
        }
        for (int width : widths) {
            CTTblGridCol column = grid.addNewGridCol();
            column.setW(BigInteger.valueOf(width));
        }
    }

    private void setCell(XWPFTableCell cell, String text, boolean label, int width) {
        cell.setVerticalAlignment(XWPFTableCell.XWPFVertAlign.CENTER);
        cell.setWidth(Integer.toString(width));
        CTTcPr properties = cell.getCTTc().getTcPr();
        if (properties == null) {
            properties = cell.getCTTc().addNewTcPr();
        }
        CTTblWidth cellWidth = properties.getTcW();
        if (cellWidth == null) {
            cellWidth = properties.addNewTcW();
        }
        cellWidth.setType(STTblWidth.DXA);
        cellWidth.setW(BigInteger.valueOf(width));
        if (label) {
            CTShd shading = properties.getShd();
            if (shading == null) {
                shading = properties.addNewShd();
            }
            shading.setFill(TABLE_FILL);
        }
        XWPFParagraph paragraph = cell.getParagraphs().getFirst();
        while (!paragraph.getRuns().isEmpty()) {
            paragraph.removeRun(0);
        }
        paragraph.setSpacingBefore(0);
        paragraph.setSpacingAfter(0);
        paragraph.setSpacingBetween(1.10, LineSpacingRule.AUTO);
        paragraph.setVerticalAlignment(TextAlignment.CENTER);
        XWPFRun run = paragraph.createRun();
        setRun(run, value(text), 10, label, label ? DARK_BLUE : "000000");
    }

    private void addGeneratedRecord(XWPFDocument document, String content) {
        String[] lines = value(content).replace("\r", "").split("\n", -1);
        boolean skippingDuplicatedBasicInfo = false;
        for (int index = 0; index < lines.length; index++) {
            String line = lines[index].strip();
            if (index == 0 && line.equals("住院病历")) {
                continue;
            }
            if (line.equals("一、基本信息")) {
                skippingDuplicatedBasicInfo = true;
                continue;
            }
            if (skippingDuplicatedBasicInfo && !line.startsWith("二、主诉")) {
                continue;
            }
            if (line.startsWith("二、主诉")) {
                skippingDuplicatedBasicInfo = false;
            }
            if (line.isBlank()) {
                XWPFParagraph spacer = document.createParagraph();
                spacer.setSpacingBefore(0);
                spacer.setSpacingAfter(40);
            } else if (line.matches("^[一二三四五六七八九十]+、.+")) {
                addHeading(document, line, 13, HEADING_BLUE, 12, 6);
            } else {
                addBodyParagraph(document, line, false);
            }
        }
    }

    private void addSignature(XWPFDocument document) {
        XWPFParagraph paragraph = document.createParagraph();
        paragraph.setSpacingBefore(320);
        paragraph.setSpacingAfter(120);
        XWPFRun run = paragraph.createRun();
        setRun(run, "医生签名：____________________    日期：____年__月__日", 11, false, "000000");
    }

    private void addGenerationProvenance(XWPFDocument document, RecordGenerationInfo generation) {
        addAnalysisField(document, "病历生成方式", generationLabel(generation));
        addAnalysisField(document, "生成模型版本", value(generation.modelVersion()));
        if (generation.fallbackUsed()) {
            addBodyParagraph(document, "提示：本次 Transformer 未能安全完成生成，正式病历已改用输入事实模板兜底。", true);
        }
        for (String warning : generation.warnings()) {
            addBodyParagraph(document, "生成提示：" + warning, true);
        }
    }

    private String generationLabel(RecordGenerationInfo generation) {
        if (generation == null || generation.backend().equals("unknown")) {
            return "历史病例未记录";
        }
        if (generation.backend().equals("transformer")) {
            return "Transformer 生成";
        }
        return generation.fallbackUsed() ? "模板安全兜底" : "模板生成";
    }

    private void addAnalysisField(XWPFDocument document, String label, String content) {
        XWPFParagraph paragraph = document.createParagraph();
        configureBodyParagraph(paragraph);
        XWPFRun labelRun = paragraph.createRun();
        setRun(labelRun, label + "：", 11, true, DARK_BLUE);
        XWPFRun contentRun = paragraph.createRun();
        setRun(contentRun, value(content), 11, false, "000000");
    }

    private XWPFParagraph addHeading(
            XWPFDocument document,
            String text,
            int size,
            String color,
            int beforePoints,
            int afterPoints
    ) {
        XWPFParagraph paragraph = document.createParagraph();
        paragraph.setSpacingBefore(beforePoints * 20);
        paragraph.setSpacingAfter(afterPoints * 20);
        paragraph.setSpacingBetween(1.10, LineSpacingRule.AUTO);
        paragraph.setKeepNext(true);
        XWPFRun run = paragraph.createRun();
        setRun(run, text, size, true, color);
        return paragraph;
    }

    private void addBodyParagraph(XWPFDocument document, String content, boolean muted) {
        XWPFParagraph paragraph = document.createParagraph();
        configureBodyParagraph(paragraph);
        XWPFRun run = paragraph.createRun();
        setRun(run, value(content), 11, false, muted ? MUTED : "000000");
    }

    private void configureBodyParagraph(XWPFParagraph paragraph) {
        paragraph.setAlignment(ParagraphAlignment.LEFT);
        paragraph.setSpacingBefore(0);
        paragraph.setSpacingAfter(120);
        paragraph.setSpacingBetween(1.10, LineSpacingRule.AUTO);
    }

    private void setRun(XWPFRun run, String text, int size, boolean bold, String color) {
        run.setText(text);
        run.setFontFamily(CHINESE_FONT);
        run.setFontSize(size);
        run.setBold(bold);
        run.setColor(color);
    }

    private String joinOrMissing(List<String> values) {
        return values == null || values.isEmpty() ? "未提供" : String.join("、", values);
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
