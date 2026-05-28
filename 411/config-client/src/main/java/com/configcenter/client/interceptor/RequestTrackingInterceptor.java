package com.configcenter.client.interceptor;

import com.configcenter.client.config.GracefulRefreshHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@Component
public class RequestTrackingInterceptor implements HandlerInterceptor {

    private static final Logger logger = LoggerFactory.getLogger(RequestTrackingInterceptor.class);

    private final GracefulRefreshHandler gracefulRefreshHandler;

    public RequestTrackingInterceptor(GracefulRefreshHandler gracefulRefreshHandler) {
        this.gracefulRefreshHandler = gracefulRefreshHandler;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        gracefulRefreshHandler.incrementRequest();
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response,
                                 Object handler, Exception ex) {
        gracefulRefreshHandler.decrementRequest();
    }
}
