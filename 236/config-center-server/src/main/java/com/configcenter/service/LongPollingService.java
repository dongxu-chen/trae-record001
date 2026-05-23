package com.configcenter.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.servlet.AsyncContext;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Map;
import java.util.concurrent.*;

@Service
public class LongPollingService {

    @Value("${config.long-polling.timeout:30000}")
    private long timeout;

    private final Map<String, CopyOnWriteArrayList<PollingRequest>> pollingRequests = new ConcurrentHashMap<>();

    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);

    public void addPollingRequest(String application, String profile, String currentVersion,
                                  HttpServletRequest request, HttpServletResponse response) {
        String key = getKey(application, profile);
        PollingRequest pollingRequest = new PollingRequest(application, profile, currentVersion, request, response);

        pollingRequests.computeIfAbsent(key, k -> new CopyOnWriteArrayList<>()).add(pollingRequest);

        scheduler.schedule(() -> {
            pollingRequest.timeout();
            removeRequest(key, pollingRequest);
        }, timeout, TimeUnit.MILLISECONDS);
    }

    public void notifyConfigChange(String application, String profile, String newVersion) {
        String key = getKey(application, profile);
        CopyOnWriteArrayList<PollingRequest> requests = pollingRequests.get(key);

        if (requests != null && !requests.isEmpty()) {
            for (PollingRequest request : requests) {
                if (!request.getCurrentVersion().equals(newVersion)) {
                    request.complete(newVersion);
                }
            }
            requests.clear();
        }
    }

    private void removeRequest(String key, PollingRequest request) {
        CopyOnWriteArrayList<PollingRequest> requests = pollingRequests.get(key);
        if (requests != null) {
            requests.remove(request);
        }
    }

    private String getKey(String application, String profile) {
        return application + "/" + profile;
    }

    public static class PollingRequest {
        private final String application;
        private final String profile;
        private final String currentVersion;
        private final AsyncContext asyncContext;
        private final long createTime;
        private volatile boolean completed = false;

        public PollingRequest(String application, String profile, String currentVersion,
                              HttpServletRequest request, HttpServletResponse response) {
            this.application = application;
            this.profile = profile;
            this.currentVersion = currentVersion;
            this.asyncContext = request.startAsync(request, response);
            this.asyncContext.setTimeout(0);
            this.createTime = System.currentTimeMillis();
        }

        public void complete(String newVersion) {
            if (!completed) {
                synchronized (this) {
                    if (!completed) {
                        try {
                            HttpServletResponse response = (HttpServletResponse) asyncContext.getResponse();
                            response.setContentType("application/json;charset=UTF-8");
                            response.getWriter().write("{\"changed\":true,\"newVersion\":\"" + newVersion + "\"}");
                            response.getWriter().flush();
                        } catch (IOException e) {
                        } finally {
                            asyncContext.complete();
                            completed = true;
                        }
                    }
                }
            }
        }

        public void timeout() {
            if (!completed) {
                synchronized (this) {
                    if (!completed) {
                        try {
                            HttpServletResponse response = (HttpServletResponse) asyncContext.getResponse();
                            response.setContentType("application/json;charset=UTF-8");
                            response.getWriter().write("{\"changed\":false}");
                            response.getWriter().flush();
                        } catch (IOException e) {
                        } finally {
                            asyncContext.complete();
                            completed = true;
                        }
                    }
                }
            }
        }

        public String getApplication() {
            return application;
        }

        public String getProfile() {
            return profile;
        }

        public String getCurrentVersion() {
            return currentVersion;
        }

        public long getCreateTime() {
            return createTime;
        }

        public boolean isCompleted() {
            return completed;
        }
    }
}
