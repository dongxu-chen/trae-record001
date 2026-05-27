package com.grayrelease.release.strategy;

import com.grayrelease.common.dto.ReleaseRequest;
import com.grayrelease.common.dto.ReleaseResponse;
import com.grayrelease.common.model.ReleaseRecord;

public interface ReleaseStrategyHandler {

    ReleaseResponse execute(ReleaseRequest request);

    ReleaseResponse progress(String releaseId, int step);

    ReleaseResponse complete(String releaseId);

    ReleaseResponse rollback(String releaseId, String reason);

    boolean supports(com.grayrelease.common.enums.ReleaseStrategy strategy);
}