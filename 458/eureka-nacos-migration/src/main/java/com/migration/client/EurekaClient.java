package com.migration.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.migration.model.ServiceInstance;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.*;

@Slf4j
@Component
public class EurekaClient {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    @Value("${eureka.client.service-url.defaultZone}")
    private String eurekaServerUrl;

    public EurekaClient(RestTemplate restTemplate, ObjectMapper objectMapper) {
        this.restTemplate = restTemplate;
        this.objectMapper = objectMapper;
    }

    public List<String> getAllServiceIds() {
        try {
            String url = eurekaServerUrl + "apps";
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            JsonNode root = objectMapper.readTree(response.getBody());
            JsonNode applications = root.path("applications").path("application");

            List<String> serviceIds = new ArrayList<>();
            if (applications.isArray()) {
                for (JsonNode app : applications) {
                    String name = app.path("name").asText();
                    if (!name.isEmpty()) {
                        serviceIds.add(name);
                    }
                }
            }
            log.info("Fetched {} service IDs from Eureka", serviceIds.size());
            return serviceIds;
        } catch (Exception e) {
            log.error("Failed to fetch service IDs from Eureka", e);
            return Collections.emptyList();
        }
    }

    public List<ServiceInstance> getInstances(String serviceId) {
        try {
            String url = eurekaServerUrl + "apps/" + serviceId.toUpperCase();
            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);
            JsonNode root = objectMapper.readTree(response.getBody());
            JsonNode instanceNodes = root.path("application").path("instance");

            List<ServiceInstance> instances = new ArrayList<>();
            if (instanceNodes.isArray()) {
                for (JsonNode inst : instanceNodes) {
                    instances.add(parseEurekaInstance(inst, serviceId));
                }
            } else if (instanceNodes.isObject()) {
                instances.add(parseEurekaInstance(instanceNodes, serviceId));
            }
            return instances;
        } catch (Exception e) {
            log.error("Failed to fetch instances for service {} from Eureka", serviceId, e);
            return Collections.emptyList();
        }
    }

    public List<ServiceInstance> getAllInstances() {
        List<String> serviceIds = getAllServiceIds();
        List<ServiceInstance> allInstances = new ArrayList<>();
        for (String serviceId : serviceIds) {
            allInstances.addAll(getInstances(serviceId));
        }
        return allInstances;
    }

    public boolean registerInstance(ServiceInstance instance) {
        try {
            String url = eurekaServerUrl + "apps/" + instance.getServiceId().toUpperCase();
            Map<String, Object> body = buildEurekaRegistrationBody(instance);
            restTemplate.postForEntity(url, body, String.class);
            log.info("Registered instance {} in Eureka", instance.getInstanceId());
            return true;
        } catch (Exception e) {
            log.error("Failed to register instance {} in Eureka", instance.getInstanceId(), e);
            return false;
        }
    }

    public boolean deregisterInstance(String serviceId, String instanceId) {
        try {
            String url = eurekaServerUrl + "apps/" + serviceId.toUpperCase() + "/" + instanceId;
            restTemplate.delete(url);
            log.info("Deregistered instance {} from Eureka", instanceId);
            return true;
        } catch (Exception e) {
            log.error("Failed to deregister instance {} from Eureka", instanceId, e);
            return false;
        }
    }

    public boolean sendHeartbeat(String serviceId, String instanceId) {
        try {
            String url = eurekaServerUrl + "apps/" + serviceId.toUpperCase() + "/" + instanceId;
            restTemplate.put(url, null);
            return true;
        } catch (Exception e) {
            log.warn("Heartbeat failed for {} in Eureka", instanceId);
            return false;
        }
    }

    public boolean isAvailable() {
        try {
            String url = eurekaServerUrl + "apps";
            restTemplate.getForEntity(url, String.class);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private ServiceInstance parseEurekaInstance(JsonNode inst, String serviceId) {
        Map<String, String> metadata = new HashMap<>();
        JsonNode metadataNode = inst.path("metadata");
        if (metadataNode.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> fields = metadataNode.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                metadata.put(field.getKey(), field.getValue().asText());
            }
        }

        return ServiceInstance.builder()
                .serviceId(serviceId)
                .instanceId(inst.path("instanceId").asText())
                .host(inst.path("hostName").asText())
                .port(inst.path("port").path("$").asInt())
                .scheme(inst.path("securePort").path("$").asInt() > 0 ? "https" : "http")
                .status(inst.path("status").asText())
                .metadata(metadata)
                .registrySource("EUREKA")
                .build();
    }

    private Map<String, Object> buildEurekaRegistrationBody(ServiceInstance instance) {
        Map<String, Object> instanceInfo = new HashMap<>();
        instanceInfo.put("instanceId", instance.getInstanceId());
        instanceInfo.put("hostName", instance.getHost());
        instanceInfo.put("app", instance.getServiceId());
        instanceInfo.put("ipAddr", instance.getHost());
        instanceInfo.put("status", "UP");
        instanceInfo.put("port", Map.of("$", instance.getPort(), "@enabled", true));
        instanceInfo.put("securePort", Map.of("$", 443, "@enabled", false));
        instanceInfo.put("metadata", instance.getMetadata() != null ? instance.getMetadata() : Collections.emptyMap());

        return Map.of("instance", instanceInfo);
    }
}
