package com.shortlink.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class BatchCreateResult {

    private int totalCount;

    private int successCount;

    private int failCount;

    private List<ShortLinkMapping> successList = new ArrayList<>();

    private List<FailRecord> failList = new ArrayList<>();

    @Data
    public static class ShortLinkMapping {
        private String originUrl;
        private String shortCode;
        private String shortUrl;
        private String description;

        public ShortLinkMapping(String originUrl, String shortCode, String shortUrl, String description) {
            this.originUrl = originUrl;
            this.shortCode = shortCode;
            this.shortUrl = shortUrl;
            this.description = description;
        }
    }

    @Data
    public static class FailRecord {
        private String originUrl;
        private String customCode;
        private String errorMessage;
        private int rowNumber;

        public FailRecord(String originUrl, String customCode, String errorMessage, int rowNumber) {
            this.originUrl = originUrl;
            this.customCode = customCode;
            this.errorMessage = errorMessage;
            this.rowNumber = rowNumber;
        }
    }
}
