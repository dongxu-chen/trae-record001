package com.datasecurity.masking.label;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FileLabel extends DataLabel {

    private String fileName;

    private String filePath;

    private String fileType;

    private long fileSize;

    private SensitivityLevel overallLevel;

    private List<FieldLabel> sensitiveFields;

    private int sensitiveFieldCount;

    public FileLabel(String fileName, String fileType) {
        super("file_" + System.currentTimeMillis(), fileName, SensitivityLevel.PUBLIC);
        this.fileName = fileName;
        this.fileType = fileType;
        this.sensitiveFields = new ArrayList<>();
        this.setDataType("FILE");
    }

    public void addSensitiveField(FieldLabel field) {
        if (sensitiveFields == null) {
            sensitiveFields = new ArrayList<>();
        }
        sensitiveFields.add(field);
        sensitiveFieldCount = sensitiveFields.size();
        recalculateOverallLevel();
    }

    private void recalculateOverallLevel() {
        if (sensitiveFields == null || sensitiveFields.isEmpty()) {
            this.overallLevel = SensitivityLevel.PUBLIC;
            return;
        }

        SensitivityLevel maxLevel = SensitivityLevel.PUBLIC;
        for (FieldLabel field : sensitiveFields) {
            if (field.getSensitivityLevel().isMoreSensitiveThan(maxLevel)) {
                maxLevel = field.getSensitivityLevel();
            }
        }
        this.overallLevel = maxLevel;
        this.setSensitivityLevel(maxLevel);
    }
}
