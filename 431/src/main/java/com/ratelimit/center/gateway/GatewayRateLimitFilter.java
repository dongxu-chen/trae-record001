package com.ratelimit.center.gateway;

import com.alibaba.csp.sentinel.Entry;
import com.alibaba.csp.sentinel.EntryType;
import com.alibaba.csp.sentinel.SphU;
import com.alibaba.csp.sentinel.Tracer;
import com.alibaba.csp.sentinel.context.ContextUtil;
import com.alibaba.csp.sentinel.slots.block.BlockException;
import com.alibaba.fastjson.JSON;
import com.ratelimit.center.common.Result;
import com.ratelimit.center.common.RateLimitConstants;
import com.ratelimit.center.service.MetricService;
import com.ratelimit.center.service.RateLimitLogService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.servlet.*;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.Arrays;
import java.util.List;

@Slf4j
@Component
public class GatewayRateLimitFilter implements Filter {

    @Autowired
    private MetricService metricService;

    @Autowired
    private RateLimitLogService rateLimitLogService;

    @Value("${rate-limit.gateway.enabled:true}")
    private boolean gatewayEnabled;

    @Value("${rate-limit.gateway.block-response-code:429}")
    private int blockResponseCode;

    @Value("${spring.application.name:rate-limit-center}")
    private String serviceName;

    @Value("${rate-limit.gateway.exclude-paths:}")
    private String excludePaths;

    private List<String> excludePathList;

    @Override
    public void init(FilterConfig filterConfig) throws ServletException {
        if (excludePaths != null && !excludePaths.trim().isEmpty()) {
            excludePathList = Arrays.asList(excludePaths.split(","));
        }
        log.info("Gateway rate limit filter initialized, enabled: {}, excludePaths: {}", gatewayEnabled, excludePathList);
    }

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest httpRequest = (HttpServletRequest) request;
        HttpServletResponse httpResponse = (HttpServletResponse) response;

        if (!gatewayEnabled) {
            chain.doFilter(request, response);
            return;
        }

        String path = httpRequest.getRequestURI();
        String method = httpRequest.getMethod();

        if (isExcluded(path)) {
            chain.doFilter(request, response);
            return;
        }

        String resourceName = buildResourceName(httpRequest);
        String origin = getOrigin(httpRequest);

        long startTime = System.currentTimeMillis();
        Entry entry = null;

        try {
            ContextUtil.enter(resourceName, origin);
            entry = SphU.entry(resourceName, EntryType.IN);

            metricService.recordPass(resourceName, serviceName);

            chain.doFilter(request, response);

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
                    getClientIp(httpRequest),
                    path,
                    method,
                    null
            );

            handleBlockedRequest(httpResponse, e);
            return;
        } catch (Exception e) {
            Tracer.trace(e);
            metricService.recordException(resourceName, serviceName, e.getClass().getSimpleName());
            throw e;
        } finally {
            if (entry != null) {
                entry.exit();
            }
            ContextUtil.exit();

            long rt = System.currentTimeMillis() - startTime;
            if (rt > 0) {
                metricService.recordRt(resourceName, serviceName, rt);
            }
        }
    }

    private void handleBlockedRequest(HttpServletResponse response, BlockException e) throws IOException {
        response.setStatus(blockResponseCode);
        response.setContentType("application/json;charset=UTF-8");

        Result<Void> result = Result.fail(blockResponseCode, getBlockMessage(e));
        String body = JSON.toJSONString(result);

        PrintWriter writer = response.getWriter();
        writer.write(body);
        writer.flush();
        writer.close();
    }

    private String getBlockMessage(BlockException e) {
        if (e instanceof com.alibaba.csp.sentinel.slots.block.flow.FlowException) {
            return "请求过于频繁，请稍后再试";
        } else if (e instanceof com.alibaba.csp.sentinel.slots.block.degrade.DegradeException) {
            return "服务暂不可用，请稍后再试";
        } else if (e instanceof com.alibaba.csp.sentinel.slots.block.flow.param.ParamFlowException) {
            return "请求参数访问频率过高";
        } else if (e instanceof com.alibaba.csp.sentinel.slots.system.SystemBlockException) {
            return "系统负载过高，请稍后再试";
        } else if (e instanceof com.alibaba.csp.sentinel.slots.block.authority.AuthorityException) {
            return "无权限访问";
        }
        return "请求被限流";
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

    private String buildResourceName(HttpServletRequest request) {
        String contextPath = request.getContextPath();
        String path = request.getRequestURI();
        if (contextPath != null && path.startsWith(contextPath)) {
            path = path.substring(contextPath.length());
        }
        return "gateway:" + request.getMethod() + ":" + path;
    }

    private String getOrigin(HttpServletRequest request) {
        String origin = request.getHeader("X-Origin");
        if (origin == null || origin.isEmpty()) {
            origin = getClientIp(request);
        }
        return origin;
    }

    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("Proxy-Client-IP");
        }
        if (ip == null || ip.isEmpty() || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        return ip;
    }

    private boolean isExcluded(String path) {
        if (excludePathList == null || excludePathList.isEmpty()) {
            return false;
        }
        for (String pattern : excludePathList) {
            if (path.startsWith(pattern.trim()) || path.matches(pattern.trim())) {
                return true;
            }
        }
        return false;
    }

    @Override
    public void destroy() {
        log.info("Gateway rate limit filter destroyed");
    }
}
