package com.log.mask.discovery;

import java.util.ArrayList;
import java.util.List;

public class SensitiveDataItem {
    private final String typeName;
    private final String category;
    private final SensitiveLevel level;
    private final int startPosition;
    private final int endPosition;
    private final String maskedPreview;
    private final int originalLength;

    public SensitiveDataItem(String typeName, String category, SensitiveLevel level,
                             int startPosition, int endPosition, String maskedPreview, int originalLength) {
        this.typeName = typeName;
        this.category = category;
        this.level = level;
        this.startPosition = startPosition;
        this.endPosition = endPosition;
        this.maskedPreview = maskedPreview;
        this.originalLength = originalLength;
    }

    public String getTypeName() { return typeName; }
    public String getCategory() { return category; }
    public SensitiveLevel getLevel() { return level; }
    public int getStartPosition() { return startPosition; }
    public int getEndPosition() { return endPosition; }
    public String getMaskedPreview() { return maskedPreview; }
    public int getOriginalLength() { return originalLength; }

    @Override
    public String toString() {
        return String.format("[%s] %s (%s) 位置:%d-%d 预览:%s", 
            level.getLabel(), typeName, category, startPosition, endPosition, maskedPreview);
    }
}
