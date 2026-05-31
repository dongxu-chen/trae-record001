package com.dlq.platform.analysis.analyzer;

import com.dlq.platform.analysis.model.AnalysisResult;
import com.dlq.platform.common.dto.DeadLetterAnalysisResult;
import com.dlq.platform.common.entity.DeadLetterMessage;

public interface DeadLetterAnalyzer {

    boolean support(DeadLetterMessage message);

    AnalysisResult analyze(DeadLetterMessage message);

    DeadLetterAnalysisResult analyzeToDto(DeadLetterMessage message);
}
