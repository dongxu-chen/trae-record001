package com.tracing.staining.context;

import com.tracing.staining.constant.TraceConstant;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
public class BizTagInjector {

    private static final List<String> STANDARD_BIZ_TAG_HEADERS = Arrays.asList(
            "X-Biz-Order-Id",
            "X-Biz-Product-Id",
            "X-Biz-Merchant-Id",
            "X-Biz-Store-Id",
            "X-Biz-Channel",
            "X-Biz-Source",
            "X-Biz-Version",
            "X-Biz-Env"
    );

    private static final List<String> CUSTOM_BIZ_TAG_PREFIXES = Arrays.asList(
            "X-Biz-",
            "X-Custom-"
    );

    public void injectBizTags(HttpServletRequest request, StainingContext context) {
        if (context == null) {
            return;
        }

        String mainBizTag = request.getHeader(TraceConstant.STAINING_BIZ_TAG);
        if (mainBizTag != null && !mainBizTag.trim().isEmpty()) {
            context.setBizTag(mainBizTag);
            context.addBizTag("bizTag", mainBizTag);
            log.debug("Main biz tag injected: {}", mainBizTag);
        }

        String bizTagVersion = request.getHeader(TraceConstant.STAINING_BIZ_TAG_VERSION);
        if (bizTagVersion != null) {
            context.setBizTagVersion(bizTagVersion);
            context.addBizTag("bizTagVersion", bizTagVersion);
        }

        for (String headerName : STANDARD_BIZ_TAG_HEADERS) {
            String value = request.getHeader(headerName);
            if (value != null && !value.trim().isEmpty()) {
                context.addBizTag(headerName, value);
                log.debug("Standard biz tag injected: {}={}", headerName, value);
            }
        }

        Collections.list(request.getHeaderNames()).stream()
                .filter(name -> CUSTOM_BIZ_TAG_PREFIXES.stream().anyMatch(name::startsWith))
                .forEach(name -> {
                    String value = request.getHeader(name);
                    if (value != null && !value.trim().isEmpty()) {
                        context.addBizTag(name, value);
                        log.debug("Custom biz tag injected: {}={}", name, value);
                    }
                });

        if (context.getBizTags() != null && !context.getBizTags().isEmpty()) {
            log.info("Biz tags injected: total={}, mainTag={}, tags={}",
                    context.getBizTags().size(),
                    context.getBizTag(),
                    context.getBizTags());
        }
    }

    public static Map<String, String> extractBizTagsFromContext(StainingContext context) {
        if (context == null || context.getBizTags() == null) {
            return Collections.emptyMap();
        }
        return new HashMap<>(context.getBizTags());
    }

    public void addBizTag(StainingContext context, String key, String value) {
        if (context != null && key != null && value != null) {
            context.addBizTag(key, value);
        }
    }
}
