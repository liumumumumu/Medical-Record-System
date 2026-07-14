package com.medicalrecord.backend.files;

import com.medicalrecord.backend.common.ApiException;
import com.medicalrecord.backend.config.StorageProperties;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.util.unit.DataSize;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class FileStorageServiceTest {
    @TempDir
    Path tempDir;

    @Test
    void storesUsingGeneratedPathAndKeepsSafeDisplayName() {
        FileStorageService service = service();
        MockMultipartFile file = new MockMultipartFile(
                "attachments", "../检查结果.pdf", "application/pdf", "%PDF-1.4\ntest".getBytes());

        AttachmentMetadata metadata = service.storeAttachments("case_123", List.of(file)).getFirst();

        assertThat(metadata.originalFileName()).isEqualTo("检查结果.pdf");
        assertThat(metadata.path()).startsWith("case_123");
        assertThat(metadata.path()).doesNotContain("..");
        assertThat(service.loadAttachment(metadata).resource().exists()).isTrue();
    }

    @Test
    void rejectsMismatchedMimeType() {
        FileStorageService service = service();
        MockMultipartFile file = new MockMultipartFile(
                "attachments", "report.pdf", "image/png", "not-pdf".getBytes());

        assertThatThrownBy(() -> service.storeAttachments("case_123", List.of(file)))
                .isInstanceOf(ApiException.class)
                .extracting(exception -> ((ApiException) exception).getCode())
                .isEqualTo("UNSUPPORTED_FILE_TYPE");
    }

    @Test
    void rejectsSpoofedPdfContent() {
        FileStorageService service = service();
        MockMultipartFile file = new MockMultipartFile(
                "attachments", "report.pdf", "application/pdf", "plain text".getBytes());

        assertThatThrownBy(() -> service.storeAttachments("case_123", List.of(file)))
                .isInstanceOf(ApiException.class)
                .extracting(exception -> ((ApiException) exception).getCode())
                .isEqualTo("UNSUPPORTED_FILE_TYPE");
    }

    @Test
    void extractsTextFromDocxForAiContext() throws Exception {
        byte[] content;
        try (XWPFDocument document = new XWPFDocument();
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            document.createParagraph().createRun().setText("血常规提示白细胞轻度升高");
            document.write(output);
            content = output.toByteArray();
        }
        MockMultipartFile file = new MockMultipartFile(
                "attachments",
                "检查结果.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                content
        );

        AttachmentMetadata metadata = service().storeAttachments("case_docx", List.of(file)).getFirst();

        assertThat(metadata.parseStatus()).isEqualTo("parsed");
        assertThat(metadata.extractedText()).contains("白细胞轻度升高");
        assertThat(metadata.parseError()).isNull();
    }

    @Test
    void extractsTextFromPdfForAiContext() {
        byte[] content = minimalPdf("white blood cell mildly elevated");
        MockMultipartFile file = new MockMultipartFile(
                "attachments", "lab.pdf", "application/pdf", content);

        AttachmentMetadata metadata = service().storeAttachments("case_pdf", List.of(file)).getFirst();

        assertThat(metadata.parseStatus()).isEqualTo("parsed");
        assertThat(metadata.extractedText()).contains("white blood cell mildly elevated");
    }

    @Test
    void marksImagesAsMetadataOnlyWhenOcrIsUnavailable() {
        byte[] pngHeader = new byte[]{
                (byte) 0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A
        };
        MockMultipartFile file = new MockMultipartFile(
                "attachments", "exam.png", "image/png", pngHeader);

        AttachmentMetadata metadata = service().storeAttachments("case_image", List.of(file)).getFirst();

        assertThat(metadata.parseStatus()).isEqualTo("metadata_only");
        assertThat(metadata.parseError()).contains("OCR");
    }

    private FileStorageService service() {
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

    private byte[] minimalPdf(String text) {
        String stream = "BT /F1 12 Tf 72 720 Td (" + text + ") Tj ET";
        List<String> objects = List.of(
                "<< /Type /Catalog /Pages 2 0 R >>",
                "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                        + "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
                "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
                "<< /Length " + stream.getBytes(StandardCharsets.ISO_8859_1).length
                        + " >>\nstream\n" + stream + "\nendstream"
        );
        StringBuilder pdf = new StringBuilder("%PDF-1.4\n");
        List<Integer> offsets = new ArrayList<>();
        for (int index = 0; index < objects.size(); index++) {
            offsets.add(pdf.toString().getBytes(StandardCharsets.ISO_8859_1).length);
            pdf.append(index + 1).append(" 0 obj\n")
                    .append(objects.get(index)).append("\nendobj\n");
        }
        int xrefOffset = pdf.toString().getBytes(StandardCharsets.ISO_8859_1).length;
        pdf.append("xref\n0 ").append(objects.size() + 1)
                .append("\n0000000000 65535 f \n");
        for (Integer offset : offsets) {
            pdf.append(String.format("%010d 00000 n %n", offset));
        }
        pdf.append("trailer\n<< /Size ").append(objects.size() + 1)
                .append(" /Root 1 0 R >>\nstartxref\n")
                .append(xrefOffset).append("\n%%EOF\n");
        return pdf.toString().getBytes(StandardCharsets.ISO_8859_1);
    }
}
