package com.loganalytics.functions;

import com.loganalytics.model.NginxLogEvent;
import org.apache.flink.api.common.functions.FlatMapFunction;
import org.apache.flink.api.java.tuple.Tuple2;
import org.apache.flink.util.Collector;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class DimensionExtractor implements FlatMapFunction<NginxLogEvent, Tuple2<String, NginxLogEvent>> {

    private final Set<String> enabledDimensions;
    private final Set<String> apiWhitelist;
    private final boolean enableApiWhitelist;

    public DimensionExtractor() {
        this(defaultEnabledDimensions(), null, false);
    }

    public DimensionExtractor(Set<String> enabledDimensions, Set<String> apiWhitelist, boolean enableApiWhitelist) {
        this.enabledDimensions = enabledDimensions != null ? enabledDimensions : defaultEnabledDimensions();
        this.apiWhitelist = apiWhitelist != null ? apiWhitelist : new HashSet<>();
        this.enableApiWhitelist = enableApiWhitelist;
    }

    private static Set<String> defaultEnabledDimensions() {
        Set<String> dims = new HashSet<>();
        dims.add("all");
        dims.add("api");
        dims.add("status");
        dims.add("api_status");
        dims.add("api_method");
        dims.add("host");
        dims.add("method");
        return dims;
    }

    @Override
    public void flatMap(NginxLogEvent event, Collector<Tuple2<String, NginxLogEvent>> out) {
        if (event == null) {
            return;
        }

        List<String> keys = generateDimensionKeys(event);
        for (String key : keys) {
            out.collect(Tuple2.of(key, event));
        }
    }

    private List<String> generateDimensionKeys(NginxLogEvent event) {
        List<String> keys = new ArrayList<>();

        String path = event.getPath();
        String method = event.getMethod();
        int status = event.getStatus();
        String host = event.getHost();
        String remoteAddr = event.getRemoteAddr();

        if (enabledDimensions.contains("all")) {
            keys.add("all:total");
        }

        if (enabledDimensions.contains("api") && path != null && !path.isEmpty()) {
            if (!enableApiWhitelist || apiWhitelist.contains(path) || apiWhitelist.isEmpty()) {
                keys.add("api:" + path);
            }
        }

        if (enabledDimensions.contains("status")) {
            keys.add("status:" + status);
        }

        if (enabledDimensions.contains("api_status") && path != null && !path.isEmpty()) {
            if (!enableApiWhitelist || apiWhitelist.contains(path) || apiWhitelist.isEmpty()) {
                keys.add("api_status:" + path + "|" + status);
            }
        }

        if (enabledDimensions.contains("api_method") && path != null && !path.isEmpty() && method != null && !method.isEmpty()) {
            if (!enableApiWhitelist || apiWhitelist.contains(path) || apiWhitelist.isEmpty()) {
                keys.add("api_method:" + path + "|" + method);
            }
        }

        if (enabledDimensions.contains("method") && method != null && !method.isEmpty()) {
            keys.add("method:" + method);
        }

        if (enabledDimensions.contains("host") && host != null && !host.isEmpty()) {
            keys.add("host:" + host);
        }

        if (enabledDimensions.contains("ip") && remoteAddr != null && !remoteAddr.isEmpty()) {
            keys.add("ip:" + remoteAddr);
        }

        if (enabledDimensions.contains("status_method") && method != null && !method.isEmpty()) {
            keys.add("status_method:" + status + "|" + method);
        }

        return keys;
    }

    public static class Builder {
        private Set<String> enabledDimensions = new HashSet<>();
        private Set<String> apiWhitelist = new HashSet<>();
        private boolean enableApiWhitelist = false;

        public Builder enableAll() {
            enabledDimensions.add("all");
            return this;
        }

        public Builder enableApi() {
            enabledDimensions.add("api");
            return this;
        }

        public Builder enableStatus() {
            enabledDimensions.add("status");
            return this;
        }

        public Builder enableApiStatus() {
            enabledDimensions.add("api_status");
            return this;
        }

        public Builder enableApiMethod() {
            enabledDimensions.add("api_method");
            return this;
        }

        public Builder enableMethod() {
            enabledDimensions.add("method");
            return this;
        }

        public Builder enableHost() {
            enabledDimensions.add("host");
            return this;
        }

        public Builder enableIp() {
            enabledDimensions.add("ip");
            return this;
        }

        public Builder enableStatusMethod() {
            enabledDimensions.add("status_method");
            return this;
        }

        public Builder withApiWhitelist(Set<String> apis) {
            this.apiWhitelist.addAll(apis);
            this.enableApiWhitelist = true;
            return this;
        }

        public DimensionExtractor build() {
            return new DimensionExtractor(enabledDimensions, apiWhitelist, enableApiWhitelist);
        }
    }
}
