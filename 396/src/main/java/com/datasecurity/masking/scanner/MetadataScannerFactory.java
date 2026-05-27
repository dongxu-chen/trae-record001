package com.datasecurity.masking.scanner;

import com.datasecurity.masking.model.DatabaseConfig;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class MetadataScannerFactory {

    @Autowired
    private List<MetadataScanner> scanners;

    public MetadataScanner getScanner(DatabaseConfig config) {
        for (MetadataScanner scanner : scanners) {
            if (scanner.support(config)) {
                return scanner;
            }
        }
        throw new IllegalArgumentException("No scanner found for database type: " + config.getType());
    }
}
