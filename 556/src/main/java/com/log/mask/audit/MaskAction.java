package com.log.mask.audit;

public enum MaskAction {
    MASK_COMPLETE("完全脱敏", "数据安全合规要求，完全遮盖敏感信息"),
    MASK_PARTIAL("部分脱敏", "业务需要部分可见，保留前后若干位"),
    MASK_DYNAMIC("动态脱敏", "根据访问者权限动态调整脱敏程度"),
    DISCOVER("敏感发现", "扫描发现未脱敏的敏感数据"),
    RULE_ADD("规则新增", "新增自定义脱敏规则"),
    RULE_REMOVE("规则删除", "删除脱敏规则"),
    RULE_MODIFY("规则修改", "修改脱敏规则配置");

    private final String label;
    private final String defaultReason;

    MaskAction(String label, String defaultReason) {
        this.label = label;
        this.defaultReason = defaultReason;
    }

    public String getLabel() { return label; }
    public String getDefaultReason() { return defaultReason; }
}
