package com.datasecurity.masking.service;

import com.datasecurity.masking.enums.MaskStrategy;
import com.datasecurity.masking.enums.SensitiveType;
import com.datasecurity.masking.model.DatabaseConfig;
import com.datasecurity.masking.model.MaskPolicy;
import com.datasecurity.masking.model.SensitiveField;
import com.datasecurity.masking.proxy.DataMaskingProxy;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

@Service
public class DataMaskingService {

    @Autowired
    private MetadataService metadataService;

    @Autowired
    private DataMaskingProxy dataMaskingProxy;

    public List<SensitiveField> scanDatabase(DatabaseConfig config) {
        return metadataService.scanDatabase(config);
    }

    public List<SensitiveField> getSensitiveFields(String databaseId) {
        return metadataService.getSensitiveFields(databaseId);
    }

    public void refreshMetadata(DatabaseConfig config) {
        metadataService.refreshMetadata(config);
    }

    public List<Map<String, Object>> maskQueryResult(List<Map<String, Object>> result, String databaseId) {
        return dataMaskingProxy.maskResult(result, databaseId);
    }

    public Map<String, Object> maskRow(Map<String, Object> row, String databaseId) {
        return dataMaskingProxy.maskRow(row, databaseId);
    }

    public MaskPolicy createDefaultPolicy(SensitiveType sensitiveType, MaskStrategy strategy) {
        return MaskPolicy.builder()
                .sensitiveType(sensitiveType)
                .strategy(strategy)
                .maskChar("*")
                .keepStart(3)
                .keepEnd(4)
                .build();
    }
}
