package com.medicalrecord.backend.files;

import com.medicalrecord.backend.common.ApiException;
import com.medicalrecord.backend.common.IdGenerator;
import com.medicalrecord.backend.config.StorageProperties;
import jakarta.annotation.PostConstruct;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.poi.hwpf.HWPFDocument;
import org.apache.poi.hwpf.extractor.WordExtractor;
import org.apache.poi.xwpf.extractor.XWPFWordExtractor;
import org.apache.poi.xwpf.usermodel.XWPFDocument;

import java.io.IOException;
import java.io.InputStream;
import java.net.MalformedURLException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

@Service
public class FileStorageService {
    private static final Map<String, Set<String>> ALLOWED_TYPES = allowedTypes();
    private static final int MAX_EXTRACTED_TEXT_LENGTH = 12_000;

    private final StorageProperties properties;
    private Path uploadRoot;
    private Path reportRoot;

    public FileStorageService(StorageProperties properties) {
        this.properties = properties;
    }

    @PostConstruct
    public void initialize() {
        try {
            uploadRoot = properties.uploadDir().toAbsolutePath().normalize();
            reportRoot = properties.reportDir().toAbsolutePath().normalize();
            Files.createDirectories(uploadRoot);
            Files.createDirectories(reportRoot);
        } catch (IOException exception) {
            throw new IllegalStateException("无法创建本地文件存储目录", exception);
        }
    }

    public List<AttachmentMetadata> storeAttachments(String caseId, List<MultipartFile> files) {
        List<MultipartFile> actualFiles = files == null
                ? List.of()
                : files.stream().filter(file -> file != null && !file.isEmpty()).toList();
        validateBatch(actualFiles);
        if (actualFiles.isEmpty()) {
            return List.of();
        }

        Path caseDirectory = safeResolve(uploadRoot, caseId);
        List<Path> createdPaths = new ArrayList<>();
        try {
            Files.createDirectories(caseDirectory);
            List<AttachmentMetadata> metadata = new ArrayList<>();
            for (MultipartFile file : actualFiles) {
                String originalName = sanitizeOriginalName(file.getOriginalFilename());
                String extension = extensionOf(originalName);
                validateType(extension, file.getContentType());
                validateContent(extension, file);
                String storedName = UUID.randomUUID().toString().replace("-", "") + "." + extension;
                Path target = safeResolve(caseDirectory, storedName);
                try (InputStream input = file.getInputStream()) {
                    Files.copy(input, target, StandardCopyOption.REPLACE_EXISTING);
                }
                createdPaths.add(target);
                ParseResult parseResult = extractText(extension, file);
                metadata.add(new AttachmentMetadata(
                        IdGenerator.fileId(),
                        originalName,
                        storedName,
                        canonicalMimeType(extension),
                        file.getSize(),
                        uploadRoot.relativize(target).toString(),
                        parseResult.status(),
                        parseResult.text(),
                        parseResult.error(),
                        Instant.now()
                ));
            }
            return List.copyOf(metadata);
        } catch (ApiException exception) {
            createdPaths.forEach(this::deleteQuietly);
            throw exception;
        } catch (IOException exception) {
            createdPaths.forEach(this::deleteQuietly);
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "FILE_STORAGE_ERROR", "附件保存失败");
        }
    }

    public StoredFileResource loadAttachment(AttachmentMetadata metadata) {
        Path path = safeResolve(uploadRoot, metadata.path());
        if (!Files.isRegularFile(path)) {
            throw new ApiException(HttpStatus.NOT_FOUND, "FILE_NOT_FOUND", "附件不存在或已被删除");
        }
        try {
            Resource resource = new UrlResource(path.toUri());
            return new StoredFileResource(
                    resource,
                    metadata.originalFileName(),
                    metadata.mimeType(),
                    metadata.size()
            );
        } catch (MalformedURLException exception) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "FILE_STORAGE_ERROR", "附件读取失败");
        }
    }

    public Path reportRoot() {
        return reportRoot;
    }

    public void deleteCaseAttachments(String caseId) {
        deleteDirectoryQuietly(safeResolve(uploadRoot, caseId));
    }

    public void deleteReport(String relativePath) {
        if (relativePath != null && !relativePath.isBlank()) {
            deleteQuietly(safeResolve(reportRoot, relativePath));
        }
    }

    public Path resolveReport(String relativePath) {
        return safeResolve(reportRoot, relativePath);
    }

    private void validateBatch(List<MultipartFile> files) {
        if (files.size() > properties.maxFiles()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "TOO_MANY_FILES",
                    "单次最多上传 " + properties.maxFiles() + " 个附件");
        }
        long total = 0;
        for (MultipartFile file : files) {
            if (file.getSize() > properties.maxFileSize().toBytes()) {
                throw new ApiException(HttpStatus.PAYLOAD_TOO_LARGE, "FILE_TOO_LARGE",
                        "单个附件不能超过 " + properties.maxFileSize().toMegabytes() + " MB");
            }
            total += file.getSize();
        }
        if (total > properties.maxTotalSize().toBytes()) {
            throw new ApiException(HttpStatus.PAYLOAD_TOO_LARGE, "FILE_TOO_LARGE",
                    "附件总大小不能超过 " + properties.maxTotalSize().toMegabytes() + " MB");
        }
    }

    private void validateType(String extension, String contentType) {
        Set<String> accepted = ALLOWED_TYPES.get(extension);
        if (accepted == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "UNSUPPORTED_FILE_TYPE",
                    "仅支持 PDF、DOC、DOCX、JPG、JPEG、PNG 文件");
        }
        if (contentType != null && !contentType.isBlank()
                && !accepted.contains(contentType.toLowerCase(Locale.ROOT))) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "UNSUPPORTED_FILE_TYPE", "附件扩展名与 MIME 类型不匹配");
        }
    }

    private void validateContent(String extension, MultipartFile file) {
        try {
            boolean valid = switch (extension) {
                case "pdf" -> hasMagic(file, new byte[]{'%', 'P', 'D', 'F', '-'});
                case "jpg", "jpeg" -> hasMagic(file, new byte[]{(byte) 0xFF, (byte) 0xD8, (byte) 0xFF});
                case "png" -> hasMagic(file, new byte[]{
                        (byte) 0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A});
                case "doc" -> hasMagic(file, new byte[]{
                        (byte) 0xD0, (byte) 0xCF, 0x11, (byte) 0xE0,
                        (byte) 0xA1, (byte) 0xB1, 0x1A, (byte) 0xE1});
                case "docx" -> isWordDocument(file);
                default -> false;
            };
            if (!valid) {
                throw new ApiException(HttpStatus.BAD_REQUEST, "UNSUPPORTED_FILE_TYPE",
                        "附件实际内容与文件类型不匹配");
            }
        } catch (IOException exception) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "UNSUPPORTED_FILE_TYPE", "无法识别附件实际类型");
        }
    }

    private boolean hasMagic(MultipartFile file, byte[] expected) throws IOException {
        try (InputStream input = file.getInputStream()) {
            byte[] actual = input.readNBytes(expected.length);
            if (actual.length != expected.length) {
                return false;
            }
            for (int i = 0; i < expected.length; i++) {
                if (actual[i] != expected[i]) {
                    return false;
                }
            }
            return true;
        }
    }

    private boolean isWordDocument(MultipartFile file) throws IOException {
        boolean contentTypes = false;
        boolean wordDocument = false;
        try (ZipInputStream zip = new ZipInputStream(file.getInputStream())) {
            ZipEntry entry;
            while ((entry = zip.getNextEntry()) != null) {
                if ("[Content_Types].xml".equals(entry.getName())) {
                    contentTypes = true;
                } else if ("word/document.xml".equals(entry.getName())) {
                    wordDocument = true;
                }
                if (contentTypes && wordDocument) {
                    return true;
                }
            }
        }
        return false;
    }

    private ParseResult extractText(String extension, MultipartFile file) {
        if (extension.equals("jpg") || extension.equals("jpeg") || extension.equals("png")) {
            return new ParseResult("metadata_only", null, "图片已保存；当前环境未配置 OCR，未提取图片文字");
        }
        try {
            String text = switch (extension) {
                case "pdf" -> extractPdf(file);
                case "docx" -> extractDocx(file);
                case "doc" -> extractDoc(file);
                default -> "";
            };
            String normalized = normalizeExtractedText(text);
            if (normalized.isBlank()) {
                return new ParseResult("failed", null, "文件中没有可提取的文本内容");
            }
            return new ParseResult("parsed", normalized, null);
        } catch (Exception exception) {
            return new ParseResult("failed", null, "文本提取失败：" + exception.getClass().getSimpleName());
        }
    }

    private String extractPdf(MultipartFile file) throws IOException {
        try (PDDocument document = Loader.loadPDF(file.getBytes())) {
            return new PDFTextStripper().getText(document);
        }
    }

    private String extractDocx(MultipartFile file) throws IOException {
        try (XWPFDocument document = new XWPFDocument(file.getInputStream());
             XWPFWordExtractor extractor = new XWPFWordExtractor(document)) {
            return extractor.getText();
        }
    }

    private String extractDoc(MultipartFile file) throws IOException {
        try (HWPFDocument document = new HWPFDocument(file.getInputStream());
             WordExtractor extractor = new WordExtractor(document)) {
            return extractor.getText();
        }
    }

    private String normalizeExtractedText(String text) {
        if (text == null) {
            return "";
        }
        String normalized = text.replace("\u0000", "")
                .replaceAll("[\\t\\x0B\\f\\r ]+", " ")
                .replaceAll(" *\\n *", "\n")
                .replaceAll("\\n{3,}", "\n\n")
                .strip();
        return normalized.length() <= MAX_EXTRACTED_TEXT_LENGTH
                ? normalized
                : normalized.substring(0, MAX_EXTRACTED_TEXT_LENGTH);
    }

    private String sanitizeOriginalName(String originalName) {
        if (originalName == null || originalName.isBlank()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "UNSUPPORTED_FILE_TYPE", "附件文件名不能为空");
        }
        String normalized = originalName.replace('\\', '/');
        String fileName = normalized.substring(normalized.lastIndexOf('/') + 1).replace("\u0000", "").trim();
        if (fileName.isBlank() || fileName.equals(".") || fileName.equals("..")) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "UNSUPPORTED_FILE_TYPE", "附件文件名不合法");
        }
        return fileName.length() > 180 ? fileName.substring(fileName.length() - 180) : fileName;
    }

    private String extensionOf(String fileName) {
        int separator = fileName.lastIndexOf('.');
        if (separator < 0 || separator == fileName.length() - 1) {
            return "";
        }
        return fileName.substring(separator + 1).toLowerCase(Locale.ROOT);
    }

    private String canonicalMimeType(String extension) {
        return switch (extension) {
            case "pdf" -> "application/pdf";
            case "doc" -> "application/msword";
            case "docx" -> "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
            case "jpg", "jpeg" -> "image/jpeg";
            case "png" -> "image/png";
            default -> "application/octet-stream";
        };
    }

    private Path safeResolve(Path root, String child) {
        Path resolved = root.resolve(child).normalize();
        if (!resolved.startsWith(root)) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "INVALID_FILE_PATH", "文件路径不合法");
        }
        return resolved;
    }

    private void deleteDirectoryQuietly(Path directory) {
        if (!Files.exists(directory)) {
            return;
        }
        try (var paths = Files.walk(directory)) {
            paths.sorted(Comparator.reverseOrder()).forEach(this::deleteQuietly);
        } catch (IOException ignored) {
            // Cleanup failures must not hide the original API outcome.
        }
    }

    private void deleteQuietly(Path path) {
        try {
            Files.deleteIfExists(path);
        } catch (IOException ignored) {
            // Cleanup failures are non-fatal and can be handled by periodic maintenance.
        }
    }

    private static Map<String, Set<String>> allowedTypes() {
        Map<String, Set<String>> types = new HashMap<>();
        types.put("pdf", ordered("application/pdf"));
        types.put("doc", ordered("application/msword", "application/octet-stream"));
        types.put("docx", ordered("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"));
        types.put("jpg", ordered("image/jpeg"));
        types.put("jpeg", ordered("image/jpeg"));
        types.put("png", ordered("image/png"));
        return Map.copyOf(types);
    }

    private static Set<String> ordered(String... values) {
        return Set.of(values);
    }

    private record ParseResult(String status, String text, String error) {
    }
}
