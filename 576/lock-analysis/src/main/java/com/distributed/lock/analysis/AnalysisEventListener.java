package com.distributed.lock.analysis;

import com.distributed.lock.core.LockEvent;
import com.distributed.lock.core.LockEventListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class AnalysisEventListener implements LockEventListener {

    private final LockAnalysisService analysisService;

    @Autowired
    public AnalysisEventListener(LockAnalysisService analysisService) {
        this.analysisService = analysisService;
    }

    @Override
    public void onEvent(LockEvent event) {
        analysisService.analyzeEvent(event);
    }
}