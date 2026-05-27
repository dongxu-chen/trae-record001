package com.datasecurity.masking.scanner;

import com.datasecurity.masking.model.DatabaseConfig;
import com.datasecurity.masking.model.SensitiveField;

import java.util.List;

public interface MetadataScanner {

    boolean support(DatabaseConfig config);

    List<SensitiveField> scan(DatabaseConfig config);
}
