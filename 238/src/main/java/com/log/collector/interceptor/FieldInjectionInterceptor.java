package com.log.collector.interceptor;

import org.apache.flume.Context;
import org.apache.flume.Event;
import org.apache.flume.interceptor.Interceptor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

public class FieldInjectionInterceptor implements Interceptor {

    private static final Logger logger = LoggerFactory.getLogger(FieldInjectionInterceptor.class);

    private final Set<String> injectFields;
    private final String hostname;
    private final String agentId;

    private FieldInjectionInterceptor(Builder builder) {
        this.injectFields = builder.injectFields;
        this.hostname = builder.hostname;
        this.agentId = builder.agentId;
    }

    @Override
    public void initialize() {
    }

    @Override
    public Event intercept(Event event) {
        for (String field : injectFields) {
            injectField(event, field);
        }
        return event;
    }

    private void injectField(Event event, String field) {
        switch (field.toLowerCase()) {
            case "collect_timestamp":
                event.getHeaders().put("collect_timestamp", String.valueOf(System.currentTimeMillis()));
                break;
            case "collect_time":
                event.getHeaders().put("collect_time", String.valueOf(System.nanoTime()));
                break;
            case "hostname":
                event.getHeaders().put("hostname", hostname);
                break;
            case "agent_id":
                event.getHeaders().put("agent_id", agentId);
                break;
            case "trace_id":
                if (!event.getHeaders().containsKey("trace_id")) {
                    event.getHeaders().put("trace_id", generateTraceId());
                }
                break;
            case "span_id":
                event.getHeaders().put("span_id", generateSpanId());
                break;
            case "topic":
                String topic = event.getHeaders().get("topic");
                if (topic != null) {
                    event.getHeaders().put("kafka_topic", topic);
                }
                break;
            case "partition":
                String partition = event.getHeaders().get("partition");
                if (partition != null) {
                    event.getHeaders().put("kafka_partition", partition);
                }
                break;
            case "offset":
                String offset = event.getHeaders().get("offset");
                if (offset != null) {
                    event.getHeaders().put("kafka_offset", offset);
                }
                break;
            case "uuid":
                event.getHeaders().put("uuid", UUID.randomUUID().toString());
                break;
            case "ip":
                event.getHeaders().put("collector_ip", getLocalIp());
                break;
            default:
                break;
        }
    }

    private String generateTraceId() {
        return UUID.randomUUID().toString().replace("-", "");
    }

    private String generateSpanId() {
        return Long.toHexString(System.nanoTime());
    }

    private String getLocalIp() {
        try {
            return InetAddress.getLocalHost().getHostAddress();
        } catch (UnknownHostException e) {
            return "unknown";
        }
    }

    @Override
    public List<Event> intercept(List<Event> events) {
        List<Event> intercepted = new ArrayList<>();
        for (Event event : events) {
            intercepted.add(intercept(event));
        }
        return intercepted;
    }

    @Override
    public void close() {
    }

    public static class Builder implements Interceptor.Builder {

        private Set<String> injectFields = new HashSet<>();
        private String hostname;
        private String agentId;

        @Override
        public Interceptor build() {
            return new FieldInjectionInterceptor(this);
        }

        @Override
        public void configure(Context context) {
            String fieldsStr = context.getString("fields", "collect_timestamp,hostname,agent_id");
            String[] fields = fieldsStr.split(",");
            for (String field : fields) {
                injectFields.add(field.trim().toLowerCase());
            }

            hostname = context.getString("hostname", getDefaultHostname());
            agentId = context.getString("agentId", "flume-agent-01");

            logger.info("FieldInjectionInterceptor configured - fields: {}, hostname: {}, agentId: {}",
                    injectFields, hostname, agentId);
        }

        private String getDefaultHostname() {
            try {
                return InetAddress.getLocalHost().getHostName();
            } catch (UnknownHostException e) {
                return "unknown-host";
            }
        }
    }
}
