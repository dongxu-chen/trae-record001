package com.configcenter.service;

import com.configcenter.dto.ConfigDTO;
import com.configcenter.dto.Result;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class ConfigSyncService {

    private final GitConfigService gitConfigService;
    private final ConfigValidationService validationService;

    private static final Pattern PLACEHOLDER_PATTERN = Pattern.compile("\\$\\{([^:}]+)(?::([^}]*))?\\}");

    public ConfigSyncService(GitConfigService gitConfigService, ConfigValidationService validationService) {
        this.gitConfigService = gitConfigService;
        this.validationService = validationService;
    }

    public SyncResult syncConfig(String application, String sourceProfile, String targetProfile,
                                 Map<String, String> placeholderValues, String operator) throws Exception {

        ConfigDTO sourceConfig = gitConfigService.getConfig(application, sourceProfile, null);
        if (sourceConfig == null) {
            return SyncResult.error("源配置不存在: " + application + "/" + sourceProfile);
        }

        String syncedContent = replacePlaceholders(sourceConfig.getContent(), placeholderValues);

        ConfigValidationService.ValidationResult validationResult =
                validationService.validate(syncedContent, sourceConfig.getFormat());

        if (!validationResult.isValid()) {
            return SyncResult.error("同步后配置校验失败: " + String.join("; ", validationResult.getErrors()));
        }

        ConfigDiffService.DiffResult diffResult = new ConfigDiffService().compareConfigs(
                getCurrentTargetContent(application, targetProfile),
                syncedContent,
                sourceConfig.getFormat()
        );

        ConfigDTO targetConfig = new ConfigDTO();
        targetConfig.setApplication(application);
        targetConfig.setProfile(targetProfile);
        targetConfig.setContent(syncedContent);
        targetConfig.setFormat(sourceConfig.getFormat());
        targetConfig.setDescription("Sync from " + sourceProfile + " to " + targetProfile);
        targetConfig.setCreatedBy(operator != null ? operator : "sync-service");

        ConfigDTO publishedConfig = gitConfigService.publishConfig(targetConfig);

        SyncResult result = new SyncResult();
        result.setSuccess(true);
        result.setSourceProfile(sourceProfile);
        result.setTargetProfile(targetProfile);
        result.setApplication(application);
        result.setNewVersion(publishedConfig.getVersion());
        result.setDiff(diffResult);
        result.setReplacedPlaceholders(getReplacedPlaceholders(sourceConfig.getContent(), placeholderValues));

        return result;
    }

    private String getCurrentTargetContent(String application, String profile) {
        try {
            ConfigDTO config = gitConfigService.getConfig(application, profile, null);
            return config != null ? config.getContent() : "";
        } catch (Exception e) {
            return "";
        }
    }

    public String replacePlaceholders(String content, Map<String, String> placeholderValues) {
        if (content == null || placeholderValues == null) {
            return content;
        }

        String result = content;
        for (Map.Entry<String, String> entry : placeholderValues.entrySet()) {
            String placeholder = "${" + entry.getKey() + "}";
            String placeholderWithDefault = "${" + entry.getKey() + ":";

            result = result.replace(placeholder, entry.getValue());

            Pattern pattern = Pattern.compile("\\$\\{" + Pattern.quote(entry.getKey()) + ":([^}]*)\\}");
            Matcher matcher = pattern.matcher(result);
            StringBuffer sb = new StringBuffer();
            while (matcher.find()) {
                matcher.appendReplacement(sb, Matcher.quoteReplacement(entry.getValue()));
            }
            matcher.appendTail(sb);
            result = sb.toString();
        }

        return result;
    }

    public Set<String> extractPlaceholders(String content) {
        Set<String> placeholders = new LinkedHashSet<>();
        if (content == null) {
            return placeholders;
        }

        Matcher matcher = PLACEHOLDER_PATTERN.matcher(content);
        while (matcher.find()) {
            placeholders.add(matcher.group(1));
        }

        return placeholders;
    }

    private Map<String, String> getReplacedPlaceholders(String content, Map<String, String> values) {
        Map<String, String> replaced = new HashMap<>();
        Set<String> placeholders = extractPlaceholders(content);

        for (String placeholder : placeholders) {
            if (values.containsKey(placeholder)) {
                replaced.put(placeholder, values.get(placeholder));
            }
        }

        return replaced;
    }

    public PreviewResult previewSync(String application, String sourceProfile, String targetProfile,
                                     Map<String, String> placeholderValues) throws Exception {

        ConfigDTO sourceConfig = gitConfigService.getConfig(application, sourceProfile, null);
        if (sourceConfig == null) {
            PreviewResult result = new PreviewResult();
            result.setSuccess(false);
            result.setMessage("源配置不存在: " + application + "/" + sourceProfile);
            return result;
        }

        String syncedContent = replacePlaceholders(sourceConfig.getContent(), placeholderValues);
        Set<String> requiredPlaceholders = extractPlaceholders(sourceConfig.getContent());
        Set<String> missingPlaceholders = new LinkedHashSet<>();

        for (String placeholder : requiredPlaceholders) {
            if (placeholderValues == null || !placeholderValues.containsKey(placeholder)) {
                missingPlaceholders.add(placeholder);
            }
        }

        ConfigValidationService.ValidationResult validationResult =
                validationService.validate(syncedContent, sourceConfig.getFormat());

        ConfigDiffService.DiffResult diffResult = new ConfigDiffService().compareConfigs(
                getCurrentTargetContent(application, targetProfile),
                syncedContent,
                sourceConfig.getFormat()
        );

        PreviewResult result = new PreviewResult();
        result.setSuccess(true);
        result.setSourceProfile(sourceProfile);
        result.setTargetProfile(targetProfile);
        result.setApplication(application);
        result.setSourceContent(sourceConfig.getContent());
        result.setTargetContentPreview(syncedContent);
        result.setFormat(sourceConfig.getFormat());
        result.setRequiredPlaceholders(requiredPlaceholders);
        result.setMissingPlaceholders(missingPlaceholders);
        result.setDiff(diffResult);
        result.setValidationPassed(validationResult.isValid());
        result.setValidationErrors(validationResult.getErrors());

        return result;
    }

    public BatchSyncResult batchSyncConfigs(List<SyncRequest> requests, String operator) {
        BatchSyncResult batchResult = new BatchSyncResult();
        batchResult.setTotal(requests.size());
        List<SyncResult> results = new ArrayList<>();

        int successCount = 0;
        int failedCount = 0;

        for (SyncRequest request : requests) {
            try {
                SyncResult result = syncConfig(
                        request.getApplication(),
                        request.getSourceProfile(),
                        request.getTargetProfile(),
                        request.getPlaceholderValues(),
                        operator
                );
                results.add(result);
                if (result.isSuccess()) {
                    successCount++;
                } else {
                    failedCount++;
                }
            } catch (Exception e) {
                SyncResult result = new SyncResult();
                result.setSuccess(false);
                result.setApplication(request.getApplication());
                result.setSourceProfile(request.getSourceProfile());
                result.setTargetProfile(request.getTargetProfile());
                result.setMessage(e.getMessage());
                results.add(result);
                failedCount++;
            }
        }

        batchResult.setSuccessCount(successCount);
        batchResult.setFailedCount(failedCount);
        batchResult.setResults(results);

        return batchResult;
    }

    public static class SyncResult {
        private boolean success;
        private String message;
        private String application;
        private String sourceProfile;
        private String targetProfile;
        private String newVersion;
        private ConfigDiffService.DiffResult diff;
        private Map<String, String> replacedPlaceholders;

        public static SyncResult error(String message) {
            SyncResult result = new SyncResult();
            result.setSuccess(false);
            result.setMessage(message);
            return result;
        }

        public boolean isSuccess() { return success; }
        public void setSuccess(boolean success) { this.success = success; }
        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }
        public String getApplication() { return application; }
        public void setApplication(String application) { this.application = application; }
        public String getSourceProfile() { return sourceProfile; }
        public void setSourceProfile(String sourceProfile) { this.sourceProfile = sourceProfile; }
        public String getTargetProfile() { return targetProfile; }
        public void setTargetProfile(String targetProfile) { this.targetProfile = targetProfile; }
        public String getNewVersion() { return newVersion; }
        public void setNewVersion(String newVersion) { this.newVersion = newVersion; }
        public ConfigDiffService.DiffResult getDiff() { return diff; }
        public void setDiff(ConfigDiffService.DiffResult diff) { this.diff = diff; }
        public Map<String, String> getReplacedPlaceholders() { return replacedPlaceholders; }
        public void setReplacedPlaceholders(Map<String, String> replacedPlaceholders) { this.replacedPlaceholders = replacedPlaceholders; }
    }

    public static class PreviewResult {
        private boolean success;
        private String message;
        private String application;
        private String sourceProfile;
        private String targetProfile;
        private String sourceContent;
        private String targetContentPreview;
        private String format;
        private Set<String> requiredPlaceholders;
        private Set<String> missingPlaceholders;
        private ConfigDiffService.DiffResult diff;
        private boolean validationPassed;
        private List<String> validationErrors;

        public boolean isSuccess() { return success; }
        public void setSuccess(boolean success) { this.success = success; }
        public String getMessage() { return message; }
        public void setMessage(String message) { this.message = message; }
        public String getApplication() { return application; }
        public void setApplication(String application) { this.application = application; }
        public String getSourceProfile() { return sourceProfile; }
        public void setSourceProfile(String sourceProfile) { this.sourceProfile = sourceProfile; }
        public String getTargetProfile() { return targetProfile; }
        public void setTargetProfile(String targetProfile) { this.targetProfile = targetProfile; }
        public String getSourceContent() { return sourceContent; }
        public void setSourceContent(String sourceContent) { this.sourceContent = sourceContent; }
        public String getTargetContentPreview() { return targetContentPreview; }
        public void setTargetContentPreview(String targetContentPreview) { this.targetContentPreview = targetContentPreview; }
        public String getFormat() { return format; }
        public void setFormat(String format) { this.format = format; }
        public Set<String> getRequiredPlaceholders() { return requiredPlaceholders; }
        public void setRequiredPlaceholders(Set<String> requiredPlaceholders) { this.requiredPlaceholders = requiredPlaceholders; }
        public Set<String> getMissingPlaceholders() { return missingPlaceholders; }
        public void setMissingPlaceholders(Set<String> missingPlaceholders) { this.missingPlaceholders = missingPlaceholders; }
        public ConfigDiffService.DiffResult getDiff() { return diff; }
        public void setDiff(ConfigDiffService.DiffResult diff) { this.diff = diff; }
        public boolean isValidationPassed() { return validationPassed; }
        public void setValidationPassed(boolean validationPassed) { this.validationPassed = validationPassed; }
        public List<String> getValidationErrors() { return validationErrors; }
        public void setValidationErrors(List<String> validationErrors) { this.validationErrors = validationErrors; }
    }

    public static class BatchSyncResult {
        private int total;
        private int successCount;
        private int failedCount;
        private List<SyncResult> results;

        public int getTotal() { return total; }
        public void setTotal(int total) { this.total = total; }
        public int getSuccessCount() { return successCount; }
        public void setSuccessCount(int successCount) { this.successCount = successCount; }
        public int getFailedCount() { return failedCount; }
        public void setFailedCount(int failedCount) { this.failedCount = failedCount; }
        public List<SyncResult> getResults() { return results; }
        public void setResults(List<SyncResult> results) { this.results = results; }
    }

    public static class SyncRequest {
        private String application;
        private String sourceProfile;
        private String targetProfile;
        private Map<String, String> placeholderValues;

        public String getApplication() { return application; }
        public void setApplication(String application) { this.application = application; }
        public String getSourceProfile() { return sourceProfile; }
        public void setSourceProfile(String sourceProfile) { this.sourceProfile = sourceProfile; }
        public String getTargetProfile() { return targetProfile; }
        public void setTargetProfile(String targetProfile) { this.targetProfile = targetProfile; }
        public Map<String, String> getPlaceholderValues() { return placeholderValues; }
        public void setPlaceholderValues(Map<String, String> placeholderValues) { this.placeholderValues = placeholderValues; }
    }
}
