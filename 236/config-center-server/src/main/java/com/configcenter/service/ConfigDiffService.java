package com.configcenter.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLFactory;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class ConfigDiffService {

    private final ObjectMapper yamlMapper = new ObjectMapper(new YAMLFactory());
    private final ObjectMapper jsonMapper = new ObjectMapper();

    public DiffResult compareConfigs(String oldContent, String newContent, String format) {
        try {
            Map<String, Object> oldMap = parseConfig(oldContent, format);
            Map<String, Object> newMap = parseConfig(newContent, format);

            List<DiffItem> diffItems = new ArrayList<>();
            compareMaps("", oldMap, newMap, diffItems);

            DiffResult result = new DiffResult();
            result.setHasChanges(!diffItems.isEmpty());
            result.setDiffItems(diffItems);
            result.setOldContent(oldContent);
            result.setNewContent(newContent);
            result.setChangeCount(diffItems.size());

            int addCount = 0, modifyCount = 0, deleteCount = 0;
            for (DiffItem item : diffItems) {
                switch (item.getType()) {
                    case ADD: addCount++; break;
                    case MODIFY: modifyCount++; break;
                    case DELETE: deleteCount++; break;
                }
            }
            result.setAddCount(addCount);
            result.setModifyCount(modifyCount);
            result.setDeleteCount(deleteCount);

            return result;
        } catch (Exception e) {
            DiffResult result = new DiffResult();
            result.setHasChanges(true);
            result.setError("Diff计算失败: " + e.getMessage());
            return result;
        }
    }

    private Map<String, Object> parseConfig(String content, String format) throws Exception {
        if (content == null || content.trim().isEmpty()) {
            return new HashMap<>();
        }
        ObjectMapper mapper = "json".equalsIgnoreCase(format) ? jsonMapper : yamlMapper;
        JsonNode node = mapper.readTree(content);
        return mapper.convertValue(node, new TypeReference<Map<String, Object>>() {});
    }

    @SuppressWarnings("unchecked")
    private void compareMaps(String prefix, Map<String, Object> oldMap, Map<String, Object> newMap, List<DiffItem> diffItems) {
        Set<String> allKeys = new HashSet<>();
        if (oldMap != null) allKeys.addAll(oldMap.keySet());
        if (newMap != null) allKeys.addAll(newMap.keySet());

        for (String key : allKeys) {
            String fullPath = prefix.isEmpty() ? key : prefix + "." + key;
            Object oldValue = oldMap != null ? oldMap.get(key) : null;
            Object newValue = newMap != null ? newMap.get(key) : null;

            if (oldValue == null && newValue != null) {
                diffItems.add(new DiffItem(fullPath, null, String.valueOf(newValue), DiffType.ADD));
            } else if (oldValue != null && newValue == null) {
                diffItems.add(new DiffItem(fullPath, String.valueOf(oldValue), null, DiffType.DELETE));
            } else if (oldValue instanceof Map && newValue instanceof Map) {
                compareMaps(fullPath, (Map<String, Object>) oldValue, (Map<String, Object>) newValue, diffItems);
            } else if (oldValue instanceof List && newValue instanceof List) {
                compareLists(fullPath, (List<Object>) oldValue, (List<Object>) newValue, diffItems);
            } else if (!Objects.equals(oldValue, newValue)) {
                diffItems.add(new DiffItem(fullPath, String.valueOf(oldValue), String.valueOf(newValue), DiffType.MODIFY));
            }
        }
    }

    private void compareLists(String prefix, List<Object> oldList, List<Object> newList, List<DiffItem> diffItems) {
        String oldStr = oldList.toString();
        String newStr = newList.toString();
        if (!oldStr.equals(newStr)) {
            diffItems.add(new DiffItem(prefix, oldStr, newStr, DiffType.MODIFY));
        }
    }

    public String generateHighlightedDiff(DiffResult diffResult) {
        if (diffResult.getError() != null) {
            return diffResult.getError();
        }

        StringBuilder sb = new StringBuilder();
        sb.append("配置变更摘要: ").append(diffResult.getChangeCount()).append(" 处变更\n");
        sb.append("新增: ").append(diffResult.getAddCount()).append("  ");
        sb.append("修改: ").append(diffResult.getModifyCount()).append("  ");
        sb.append("删除: ").append(diffResult.getDeleteCount()).append("\n\n");

        for (DiffItem item : diffResult.getDiffItems()) {
            switch (item.getType()) {
                case ADD:
                    sb.append("[新增] ").append(item.getPath()).append("\n");
                    sb.append("  + 值: ").append(item.getNewValue()).append("\n\n");
                    break;
                case MODIFY:
                    sb.append("[修改] ").append(item.getPath()).append("\n");
                    sb.append("  - 原值: ").append(item.getOldValue()).append("\n");
                    sb.append("  + 新值: ").append(item.getNewValue()).append("\n\n");
                    break;
                case DELETE:
                    sb.append("[删除] ").append(item.getPath()).append("\n");
                    sb.append("  - 值: ").append(item.getOldValue()).append("\n\n");
                    break;
            }
        }

        return sb.toString();
    }

    public enum DiffType {
        ADD, MODIFY, DELETE
    }

    public static class DiffItem {
        private String path;
        private String oldValue;
        private String newValue;
        private DiffType type;

        public DiffItem() {}

        public DiffItem(String path, String oldValue, String newValue, DiffType type) {
            this.path = path;
            this.oldValue = oldValue;
            this.newValue = newValue;
            this.type = type;
        }

        public String getPath() { return path; }
        public void setPath(String path) { this.path = path; }
        public String getOldValue() { return oldValue; }
        public void setOldValue(String oldValue) { this.oldValue = oldValue; }
        public String getNewValue() { return newValue; }
        public void setNewValue(String newValue) { this.newValue = newValue; }
        public DiffType getType() { return type; }
        public void setType(DiffType type) { this.type = type; }
    }

    public static class DiffResult {
        private boolean hasChanges;
        private List<DiffItem> diffItems = new ArrayList<>();
        private String oldContent;
        private String newContent;
        private int changeCount;
        private int addCount;
        private int modifyCount;
        private int deleteCount;
        private String error;
        private String highlightedDiff;

        public boolean isHasChanges() { return hasChanges; }
        public void setHasChanges(boolean hasChanges) { this.hasChanges = hasChanges; }
        public List<DiffItem> getDiffItems() { return diffItems; }
        public void setDiffItems(List<DiffItem> diffItems) { this.diffItems = diffItems; }
        public String getOldContent() { return oldContent; }
        public void setOldContent(String oldContent) { this.oldContent = oldContent; }
        public String getNewContent() { return newContent; }
        public void setNewContent(String newContent) { this.newContent = newContent; }
        public int getChangeCount() { return changeCount; }
        public void setChangeCount(int changeCount) { this.changeCount = changeCount; }
        public int getAddCount() { return addCount; }
        public void setAddCount(int addCount) { this.addCount = addCount; }
        public int getModifyCount() { return modifyCount; }
        public void setModifyCount(int modifyCount) { this.modifyCount = modifyCount; }
        public int getDeleteCount() { return deleteCount; }
        public void setDeleteCount(int deleteCount) { this.deleteCount = deleteCount; }
        public String getError() { return error; }
        public void setError(String error) { this.error = error; }
        public String getHighlightedDiff() { return highlightedDiff; }
        public void setHighlightedDiff(String highlightedDiff) { this.highlightedDiff = highlightedDiff; }
    }
}
