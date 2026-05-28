package com.ratelimit.center.interceptor;

import com.alibaba.csp.sentinel.Entry;
import com.alibaba.csp.sentinel.EntryType;
import com.alibaba.csp.sentinel.SphU;
import com.alibaba.csp.sentinel.Tracer;
import com.alibaba.csp.sentinel.context.ContextUtil;
import com.alibaba.csp.sentinel.slots.block.BlockException;
import com.ratelimit.center.common.RateLimitConstants;
import com.ratelimit.center.service.MetricService;
import com.ratelimit.center.service.RateLimitLogService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.servlet.HandlerInterceptor;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@Slf4j
@Component
public class RateLimitInterceptor implements HandlerInterceptor {

    @Autowired
    private MetricService metricService;

    @Autowired
    private RateLimitLogService rateLimitLogService;

    @Value("${spring.application.name:rate-limit-center}")
    private String serviceName;

    private static final String ENTRY_ATTR = "__sentinel_entry";
    private static final String START_TIME_ATTR = "__start_time";

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String resourceName = getResourceName(request);
        String origin = getOrigin(request);

        ContextUtil.enter(resourceName, origin);

        long startTime = System.currentTimeMillis();
        request.setAttribute(START_TIME_ATTR, startTime);

        try {
            Entry entry = SphU.entry(resourceName, EntryType.IN);
            request.setAttribute(ENTRY_ATTR, entry);

            metricService.recordPass(resourceName, serviceName);

            return true;
        } catch (BlockException e) {
            long rt = System.currentTimeMillis() - startTime;
            String ruleType = getRuleType(e);

            metricService.recordBlock(resourceName, serviceName, ruleType);
            rateLimitLogService.logAsync(
                    serviceName,
                    resourceName,
                    origin,
                    ruleType,
                    0, 1, rt, e.getClass().getSimpleName(),
                    getClientIp(request),
                    request.getRequestURI(),
                    request.getMethod(),
                    getRequestParams(request)
            );

            throw e;
        } catch (Exception e) {
            Tracer.trace(e);
            metricService.recordException(resourceName, serviceName, e.getClass().getSimpleName());
            throw e;
        }
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
        Entry entry = (Entry) request.getAttribute(ENTRY_ATTR);
        Long startTime = (Long) request.getAttribute(START_TIME_ATTR);

        if (entry != null) {
            entry.exit();
        }

        ContextUtil.exit();

        if (startTime != null && entry != null) {
            long rt = System.currentTimeMillis() - startTime;
            String resourceName = getResourceName(request);
            String origin = getOrigin(request);

            metricService.recordRt(resourceName, serviceName, rt);
            rateLimitLogService.logAsync(
                    serviceName,
                    resourceName,
                    origin,
                    "pass",
                    1, 0, rt, null,
                    getClientIp(request),
                    request.getRequestURI(),
                    request.getMethod(),
                    getRequestParams(request)
            );
        }
    }

    private String getResourceName(HttpServletRequest request) {
        return request.getMethod() + ":" + request.getRequestURI();
    }

    private String getOrigin(HttpServletRequest request) {
        String origin = request.getHeader("X-Origin");
        if (!StringUtils.hasText(origin)) {
            origin = getClientIp(request);
        }
        return origin;
    }

    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (!StringUtils.hasText(ip) || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (!StringUtils.hasText(ip) || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("WL-Proxy-Client-IP");
        }
        if (!StringUtils.hasText(ip) || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("HTTP_CLIENT_IP");
        }
        if (!StringUtils.hasText(ip) || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("HTTP_X_FORWARDED_FOR");
        }
        if (!StringUtils.hasText(ip) || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        return ip;
    }

    private String getRequestParams(HttpServletRequest request) {
        try {
            java.util.Map<String, String[]> paramMap = request.getParameterMap();
            if (paramMap == null || paramMap.isEmpty()) {
                return null;
            }
            return com.alibaba.fastjson.JSON.toJSONString(paramMap);
        } catch (Exception e) {
            return null;
        }
    }

    private String getRuleType(BlockException e) {
        if (e instanceof com.alibaba.csp.sentinel.slots.block.flow.FlowException) {
            return RateLimitConstants.RULE_TYPE_FLOW;
        } else if (e instanceof com.alibaba.csp.sentinel.slots.block.degrade.DegradeException) {
            return RateLimitConstants.RULE_TYPE_DEGRADE;
        } else if (e instanceof com.alibaba.csp.sentinel.slots.block.flow.param.ParamFlowException) {
            return RateLimitConstants.RULE_TYPE_PARAM_FLOW;
        } else if (e instanceof com.alibaba.csp.sentinel.slots.system.SystemBlockException) {
            return RateLimitConstants.RULE_TYPE_SYSTEM;
        } else if (e instanceof com.alibaba.csp.sentinel.slots.block.authority.AuthorityException) {
            return RateLimitConstants.RULE_TYPE_AUTHORITY;
        }
        return "unknown";
    }
}
