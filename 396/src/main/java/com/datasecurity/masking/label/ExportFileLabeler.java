package com.datasecurity.masking.label;

import com.datasecurity.masking.enums.SensitiveType;
import com.datasecurity.masking.recognizer.SensitiveFieldRecognizer;
import com.datasecurity.masking.rule.CustomMaskRule;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.io.*;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Component
public class ExportFileLabeler {

    @Autowired
    private SensitiveFieldRecognizer fieldRecognizer;

    @Autowired
    private LabelPropagationEngine labelPropagationEngine;

    public FileLabel analyzeExcelFile(String filePath) throws IOException {
        File file = new File(filePath);
        String fileName = file.getName();
        String fileType = getFileType(fileName);

        FileLabel fileLabel = new FileLabel(fileName, fileType);
        fileLabel.setFilePath(filePath);
        fileLabel.setFileSize(file.length());

        try (FileInputStream fis = new FileInputStream(file);
             Workbook workbook = new XSSFWorkbook(fis)) {

            int sheetCount = workbook.getNumberOfSheets();
            for (int i = 0; i < sheetCount; i++) {
                Sheet sheet = workbook.getSheetAt(i);
                analyzeSheet(sheet, fileLabel, i);
            }
        }

        log.info("Analyzed Excel file: {}, sensitivity level: {}, sensitive fields: {}",
                fileName, fileLabel.getOverallLevel(), fileLabel.getSensitiveFieldCount());

        return fileLabel;
    }

    public FileLabel analyzeCSVFile(String filePath) throws IOException {
        File file = new File(filePath);
        String fileName = file.getName();

        FileLabel fileLabel = new FileLabel(fileName, "CSV");
        fileLabel.setFilePath(filePath);
        fileLabel.setFileSize(file.length());

        try (BufferedReader reader = new BufferedReader(new FileReader(file))) {
            String headerLine = reader.readLine();
            if (headerLine != null) {
                String[] headers = headerLine.split(",");
                for (String header : headers) {
                    String columnName = header.trim().replace("\"", "");
                    analyzeColumn(columnName, null, fileLabel, 0);
                }
            }

            String dataLine;
            int rowCount = 0;
            while ((dataLine = reader.readLine()) != null && rowCount < 100) {
                String[] values = dataLine.split(",");
                for (int i = 0; i < values.length; i++) {
                    String value = values[i].trim().replace("\"", "");
                    if (value != null && !value.isEmpty()) {
                        CustomMaskRule rule = fieldRecognizer.recognizeRuleByValue(value);
                        if (rule != null) {
                            SensitiveType type = com.datasecurity.masking.enums.SensitiveType.valueOf(
                                    rule.getId().replace("builtin_", "").toUpperCase());
                            SensitivityLevel level = determineSensitivityLevel(type);
                            FieldLabel fieldLabel = new FieldLabel("csv", "col_" + i, type, level);
                            fileLabel.addSensitiveField(fieldLabel);
                        }
                    }
                }
                rowCount++;
            }
        }

        log.info("Analyzed CSV file: {}, sensitivity level: {}, sensitive fields: {}",
                fileName, fileLabel.getOverallLevel(), fileLabel.getSensitiveFieldCount());

        return fileLabel;
    }

    public FileLabel analyzeContent(String content, String contentType) {
        FileLabel fileLabel = new FileLabel("content_" + System.currentTimeMillis(), contentType);

        String[] lines = content.split("\n");
        if (lines.length > 0) {
            String[] headers = lines[0].split(",|\t");
            for (String header : headers) {
                String columnName = header.trim();
                analyzeColumn(columnName, null, fileLabel, 0);
            }

            for (int i = 1; i < Math.min(lines.length, 100); i++) {
                String[] values = lines[i].split(",|\t");
                for (String value : values) {
                    String trimmedValue = value.trim();
                    if (!trimmedValue.isEmpty()) {
                        CustomMaskRule rule = fieldRecognizer.recognizeRuleByValue(trimmedValue);
                        if (rule != null) {
                            SensitiveType type = SensitiveType.valueOf(
                                    rule.getId().replace("builtin_", "").toUpperCase());
                            SensitivityLevel level = determineSensitivityLevel(type);
                            FieldLabel fieldLabel = new FieldLabel("content", "field", type, level);
                            fileLabel.addSensitiveField(fieldLabel);
                        }
                    }
                }
            }
        }

        return fileLabel;
    }

    private void analyzeSheet(Sheet sheet, FileLabel fileLabel, int sheetIndex) {
        Row headerRow = sheet.getRow(0);
        if (headerRow == null) {
            return;
        }

        List<String> columnNames = new ArrayList<>();
        for (Cell cell : headerRow) {
            String columnName = getCellValueAsString(cell);
            columnNames.add(columnName);
            analyzeColumn(columnName, null, fileLabel, sheetIndex);
        }

        int sampleRowCount = Math.min(sheet.getLastRowNum(), 100);
        for (int rowIdx = 1; rowIdx <= sampleRowCount; rowIdx++) {
            Row row = sheet.getRow(rowIdx);
            if (row != null) {
                for (int colIdx = 0; colIdx < columnNames.size(); colIdx++) {
                    Cell cell = row.getCell(colIdx);
                    if (cell != null) {
                        String value = getCellValueAsString(cell);
                        if (value != null && !value.isEmpty()) {
                            CustomMaskRule rule = fieldRecognizer.recognizeRuleByValue(value);
                            if (rule != null) {
                                SensitiveType type = SensitiveType.valueOf(
                                        rule.getId().replace("builtin_", "").toUpperCase());
                                SensitivityLevel level = determineSensitivityLevel(type);
                                FieldLabel fieldLabel = new FieldLabel(
                                        "sheet" + sheetIndex,
                                        columnNames.get(colIdx),
                                        type,
                                        level
                                );
                                fileLabel.addSensitiveField(fieldLabel);
                            }
                        }
                    }
                }
            }
        }
    }

    private void analyzeColumn(String columnName, String comment, FileLabel fileLabel, int sheetIndex) {
        CustomMaskRule rule = fieldRecognizer.recognizeRuleByColumnName(columnName, comment);
        if (rule != null) {
            SensitiveType type = SensitiveType.valueOf(
                    rule.getId().replace("builtin_", "").toUpperCase());
            SensitivityLevel level = determineSensitivityLevel(type);
            FieldLabel fieldLabel = new FieldLabel(
                    "sheet" + sheetIndex,
                    columnName,
                    type,
                    level
            );
            fileLabel.addSensitiveField(fieldLabel);
        }
    }

    private String getCellValueAsString(Cell cell) {
        if (cell == null) {
            return null;
        }
        switch (cell.getCellType()) {
            case STRING:
                return cell.getStringCellValue();
            case NUMERIC:
                if (DateUtil.isCellDateFormatted(cell)) {
                    return cell.getDateCellValue().toString();
                }
                return String.valueOf((long) cell.getNumericCellValue());
            case BOOLEAN:
                return String.valueOf(cell.getBooleanCellValue());
            default:
                return null;
        }
    }

    private String getFileType(String fileName) {
        String lowerName = fileName.toLowerCase();
        if (lowerName.endsWith(".xlsx")) {
            return "XLSX";
        } else if (lowerName.endsWith(".xls")) {
            return "XLS";
        } else if (lowerName.endsWith(".csv")) {
            return "CSV";
        } else if (lowerName.endsWith(".txt")) {
            return "TXT";
        }
        return "UNKNOWN";
    }

    private SensitivityLevel determineSensitivityLevel(SensitiveType type) {
        switch (type) {
            case ID_CARD:
            case BANK_CARD:
                return SensitivityLevel.SECRET;
            case PHONE:
            case EMAIL:
            case NAME:
            case ADDRESS:
                return SensitivityLevel.CONFIDENTIAL;
            default:
                return SensitivityLevel.INTERNAL;
        }
    }

    public String generateSensitivityMark(FileLabel fileLabel) {
        StringBuilder sb = new StringBuilder();
        sb.append("【数据敏感等级：").append(fileLabel.getOverallLevel().getName()).append("】\n");
        sb.append("文件名称：").append(fileLabel.getFileName()).append("\n");
        sb.append("文件类型：").append(fileLabel.getFileType()).append("\n");
        sb.append("敏感字段数量：").append(fileLabel.getSensitiveFieldCount()).append("\n");

        if (fileLabel.getSensitiveFields() != null && !fileLabel.getSensitiveFields().isEmpty()) {
            sb.append("敏感字段列表：\n");
            for (FieldLabel field : fileLabel.getSensitiveFields()) {
                sb.append("  - ").append(field.getColumnName())
                        .append(" (").append(field.getSensitiveType().getDescription())
                        .append(" - ").append(field.getSensitivityLevel().getName()).append(")\n");
            }
        }

        return sb.toString();
    }
}
