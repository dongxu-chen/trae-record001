package com.servicetopology.k8s;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.servicetopology.config.DiscoveryProperties;
import com.servicetopology.model.ServiceNode;
import com.servicetopology.neo4j.ServiceNodeRepository;
import io.fabric8.kubernetes.api.model.Service;
import io.fabric8.kubernetes.api.model.ServicePort;
import io.fabric8.kubernetes.client.KubernetesClient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
@ConditionalOnProperty(name = "kubernetes.discovery.enabled", havingValue = "true", matchIfMissing = true)
public class KubernetesServiceDiscovery {

    private final KubernetesClient kubernetesClient;
    private final ServiceNodeRepository serviceNodeRepository;
    private final DiscoveryProperties discoveryProperties;
    private final ObjectMapper objectMapper;

    @Scheduled(fixedRateString = "${kubernetes.discovery.scan-interval:30000}")
    public void discoverServices() {
        log.info("Starting Kubernetes service discovery...");
        
        List<String> namespaces = discoveryProperties.getKubernetes().getNamespaces();
        List<ServiceNode> discoveredNodes = new ArrayList<>();

        for (String namespace : namespaces) {
            try {
                List<Service> services = kubernetesClient.services()
                    .inNamespace(namespace)
                    .list()
                    .getItems();

                log.debug("Found {} services in namespace {}", services.size(), namespace);

                for (Service service : services) {
                    ServiceNode node = convertToServiceNode(service);
                    discoveredNodes.add(node);
                }
            } catch (Exception e) {
                log.error("Error discovering services in namespace {}: {}", namespace, e.getMessage());
            }
        }

        saveDiscoveredServices(discoveredNodes);
        log.info("Kubernetes service discovery completed. Discovered {} services.", discoveredNodes.size());
    }

    private ServiceNode convertToServiceNode(Service service) {
        String namespace = service.getMetadata().getNamespace();
        String name = service.getMetadata().getName();
        String id = namespace + "-" + name;

        Map<String, String> labels = service.getMetadata().getLabels();
        Map<String, String> annotations = service.getMetadata().getAnnotations();

        String serviceType = service.getSpec() != null ? service.getSpec().getType() : "Unknown";
        String clusterIp = service.getSpec() != null ? service.getSpec().getClusterIP() : "";
        String ports = service.getSpec() != null && service.getSpec().getPorts() != null
            ? service.getSpec().getPorts().stream()
                .map(this::formatPort)
                .collect(Collectors.joining(","))
            : "";

        String language = detectLanguage(labels, annotations);
        String version = detectVersion(labels, annotations);

        String now = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);

        return ServiceNode.builder()
            .id(id)
            .name(name)
            .namespace(namespace)
            .type("KUBERNETES_SERVICE")
            .language(language)
            .version(version)
            .serviceType(serviceType)
            .clusterIp(clusterIp)
            .ports(ports)
            .labels(toJson(labels))
            .annotations(toJson(annotations))
            .status("ACTIVE")
            .discoveredAt(LocalDateTime.now())
            .lastUpdated(LocalDateTime.now())
            .build();
    }

    private String formatPort(ServicePort port) {
        return port.getName() != null
            ? port.getName() + ":" + port.getPort() + "/" + port.getProtocol()
            : port.getPort() + "/" + port.getProtocol();
    }

    private String detectLanguage(Map<String, String> labels, Map<String, String> annotations) {
        if (labels != null) {
            for (Map.Entry<String, String> entry : labels.entrySet()) {
                String key = entry.getKey().toLowerCase();
                String value = entry.getValue().toLowerCase();
                
                if (key.contains("language") || key.contains("lang") || key.contains("runtime")) {
                    return value;
                }
                
                if (value.contains("java") || value.contains("spring")) return "Java";
                if (value.contains("python")) return "Python";
                if (value.contains("node") || value.contains("javascript")) return "Node.js";
                if (value.contains("go") || value.contains("golang")) return "Go";
                if (value.contains("rust")) return "Rust";
                if (value.contains("csharp") || value.contains("dotnet")) return "C#";
                if (value.contains("ruby")) return "Ruby";
                if (value.contains("php")) return "PHP";
            }
        }
        return "Unknown";
    }

    private String detectVersion(Map<String, String> labels, Map<String, String> annotations) {
        if (labels != null) {
            String version = labels.get("version");
            if (version != null) return version;
            
            version = labels.get("app.kubernetes.io/version");
            if (version != null) return version;
        }
        return "latest";
    }

    private String toJson(Map<String, String> map) {
        if (map == null || map.isEmpty()) {
            return "{}";
        }
        try {
            return objectMapper.writeValueAsString(map);
        } catch (JsonProcessingException e) {
            return "{}";
        }
    }

    private void saveDiscoveredServices(List<ServiceNode> discoveredNodes) {
        for (ServiceNode node : discoveredNodes) {
            Optional<ServiceNode> existing = serviceNodeRepository.findById(node.getId());
            
            if (existing.isPresent()) {
                ServiceNode existingNode = existing.get();
                existingNode.setLastUpdated(LocalDateTime.now());
                existingNode.setStatus("ACTIVE");
                existingNode.setLabels(node.getLabels());
                existingNode.setAnnotations(node.getAnnotations());
                existingNode.setPorts(node.getPorts());
                serviceNodeRepository.save(existingNode);
            } else {
                serviceNodeRepository.save(node);
            }
        }
    }

    public List<ServiceNode> getAllDiscoveredServices() {
        return serviceNodeRepository.findAllServices();
    }

    public List<ServiceNode> getServicesByNamespace(String namespace) {
        return serviceNodeRepository.findAllByNamespace(namespace);
    }

    public Optional<ServiceNode> getServiceById(String id) {
        return serviceNodeRepository.findById(id);
    }

    public Optional<ServiceNode> getServiceByName(String name, String namespace) {
        return serviceNodeRepository.findByServiceName(name, namespace);
    }

    public void triggerDiscovery() {
        discoverServices();
    }
}
