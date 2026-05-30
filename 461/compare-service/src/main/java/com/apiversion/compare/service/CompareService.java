package com.apiversion.compare.service;

import com.apiversion.compare.dto.DiffRequest;
import com.apiversion.compare.dto.DiffResponse;

public interface CompareService {

    DiffResponse compareOpenApi(DiffRequest request);

    DiffResponse compareVersions(Long sourceVersionId, Long targetVersionId);

    DiffResponse compareOpenApiJson(String sourceOpenApi, String targetOpenApi);
}
