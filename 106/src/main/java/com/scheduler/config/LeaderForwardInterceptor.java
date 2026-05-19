package com.scheduler.config;

import com.scheduler.raft.LeaderForwarder;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@Component
public class LeaderForwardInterceptor implements HandlerInterceptor {

    @Resource
    private LeaderForwarder leaderForwarder;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String requestURI = request.getRequestURI();

        if (requestURI.startsWith("/api/cluster/")) {
            return true;
        }

        if (requestURI.startsWith("/actuator/")) {
            return true;
        }

        if (!leaderForwarder.shouldForward()) {
            return true;
        }

        LeaderForwarder.ForwardResult result = leaderForwarder.forwardRequest(request, null);

        if (result.isSuccess()) {
            response.setStatus(result.getStatusCode());
            response.setContentType("application/json");
            response.getWriter().write(result.getResponse());
            return false;
        } else if (result.isForwarded()) {
            response.setStatus(503);
            response.getWriter().write("{\"code\":503,\"message\":\"" + result.getMessage() + "\"}");
            return false;
        }

        return true;
    }
}
