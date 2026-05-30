package com.tracing.staining.sampler;

import com.tracing.staining.context.StainingContext;
import jakarta.servlet.http.HttpServletRequest;

public interface TraceSampler {

    boolean shouldSample(HttpServletRequest request, StainingContext context);

    boolean shouldStain(HttpServletRequest request, StainingContext context);

    String assignStainingColor(HttpServletRequest request, StainingContext context);
}
