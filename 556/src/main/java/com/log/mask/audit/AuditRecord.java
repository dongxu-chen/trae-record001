package com.log.mask.audit;

public class AuditRecord {
    private long id;
    private long timestamp;
    private String operator;
    private String dataType;
    private String reason;
    private MaskAction action;
    private String originalPreview;
    private String maskedPreview;
    private String source;

    public long getId() { return id; }
    public void setId(long id) { this.id = id; }

    public long getTimestamp() { return timestamp; }
    public void setTimestamp(long timestamp) { this.timestamp = timestamp; }

    public String getOperator() { return operator; }
    public void setOperator(String operator) { this.operator = operator; }

    public String getDataType() { return dataType; }
    public void setDataType(String dataType) { this.dataType = dataType; }

    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }

    public MaskAction getAction() { return action; }
    public void setAction(MaskAction action) { this.action = action; }

    public String getOriginalPreview() { return originalPreview; }
    public void setOriginalPreview(String originalPreview) { this.originalPreview = originalPreview; }

    public String getMaskedPreview() { return maskedPreview; }
    public void setMaskedPreview(String maskedPreview) { this.maskedPreview = maskedPreview; }

    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }

    @Override
    public String toString() {
        return String.format("AuditRecord#%d [%s] %s by %s: %s -> %s (原因: %s)",
            id, dataType, action.getLabel(), operator, originalPreview, maskedPreview, reason);
    }
}
