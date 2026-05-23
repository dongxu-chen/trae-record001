package com.shortlink.util;

import com.shortlink.dto.BatchCreateResult;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

@Slf4j
public class CsvUtil {

    private static final String[] CSV_HEADERS = {"originUrl", "customCode", "description", "expireDays"};
    private static final String[] EXPORT_HEADERS = {"原始URL", "短码", "短链接", "描述"};

    public static List<CsvRow> parseCsv(MultipartFile file) throws IOException {
        List<CsvRow> rows = new ArrayList<>();

        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {

            String line;
            int lineNumber = 0;
            boolean isFirstLine = true;

            while ((line = reader.readLine()) != null) {
                lineNumber++;

                if (isFirstLine) {
                    isFirstLine = false;
                    if (isHeaderLine(line)) {
                        continue;
                    }
                }

                if (StringUtils.isBlank(line)) {
                    continue;
                }

                String[] fields = parseCsvLine(line);
                CsvRow row = new CsvRow();
                row.setLineNumber(lineNumber);

                if (fields.length > 0) {
                    row.setOriginUrl(fields[0].trim());
                }
                if (fields.length > 1) {
                    row.setCustomCode(fields[1].trim());
                }
                if (fields.length > 2) {
                    row.setDescription(fields[2].trim());
                }
                if (fields.length > 3 && StringUtils.isNotBlank(fields[3])) {
                    try {
                        row.setExpireDays(Integer.parseInt(fields[3].trim()));
                    } catch (NumberFormatException e) {
                        log.warn("解析expireDays失败: {}", fields[3]);
                    }
                }

                rows.add(row);
            }
        }

        return rows;
    }

    private static boolean isHeaderLine(String line) {
        String lowerLine = line.toLowerCase();
        return lowerLine.contains("originurl") || lowerLine.contains("url") || lowerLine.contains("链接");
    }

    private static String[] parseCsvLine(String line) {
        List<String> fields = new ArrayList<>();
        StringBuilder currentField = new StringBuilder();
        boolean inQuotes = false;

        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);

            if (c == '"') {
                if (inQuotes && i + 1 < line.length() && line.charAt(i + 1) == '"') {
                    currentField.append('"');
                    i++;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (c == ',' && !inQuotes) {
                fields.add(currentField.toString());
                currentField = new StringBuilder();
            } else {
                currentField.append(c);
            }
        }
        fields.add(currentField.toString());

        return fields.toArray(new String[0]);
    }

    public static byte[] generateMappingCsv(List<BatchCreateResult.ShortLinkMapping> mappings) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (BufferedWriter writer = new BufferedWriter(
                new OutputStreamWriter(baos, StandardCharsets.UTF_8))) {

            writer.write('\ufeff');
            writer.write(String.join(",", EXPORT_HEADERS));
            writer.newLine();

            for (BatchCreateResult.ShortLinkMapping mapping : mappings) {
                writer.write(escapeCsvField(mapping.getOriginUrl()));
                writer.write(",");
                writer.write(escapeCsvField(mapping.getShortCode()));
                writer.write(",");
                writer.write(escapeCsvField(mapping.getShortUrl()));
                writer.write(",");
                writer.write(escapeCsvField(mapping.getDescription()));
                writer.newLine();
            }

            writer.flush();
        }
        return baos.toByteArray();
    }

    private static String escapeCsvField(String field) {
        if (field == null) {
            return "";
        }
        if (field.contains(",") || field.contains("\"") || field.contains("\n")) {
            return "\"" + field.replace("\"", "\"\"") + "\"";
        }
        return field;
    }

    @lombok.Data
    public static class CsvRow {
        private int lineNumber;
        private String originUrl;
        private String customCode;
        private String description;
        private Integer expireDays;
    }
}
