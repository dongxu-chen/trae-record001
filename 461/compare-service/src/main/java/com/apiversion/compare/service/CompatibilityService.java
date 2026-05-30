package com.apiversion.compare.service;

import com.apiversion.compare.dto.CompatibilityReport;
import com.apiversion.compare.dto.DiffResponse;

public interface CompatibilityService {

    CompatibilityReport checkCompatibility(Long sourceVersionId, Long targetVersionId);

    CompatibilityReport generateReport(DiffResponse diffResponse);

    String generateUpgradeRecommendation(CompatibilityReport report);
}
