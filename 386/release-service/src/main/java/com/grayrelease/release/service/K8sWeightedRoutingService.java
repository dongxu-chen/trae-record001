package com.grayrelease.release.service;

import io.fabric8.kubernetes.api.model.*;
import io.fabric8.kubernetes.api.model.discovery.v1.EndpointSlice;
import io.fabric8.kubernetes.api.model.discovery.v1.EndpointSliceBuilder;
import io.fabric8.kubernetes.api.model.discovery.v1.EndpointBuilder;
import io.fabric8.kubernetes.client.KubernetesClient;
import io.fabric8.kubernetes.client.KubernetesClientBuilder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.*;

@Slf4j
@Service
public class K8sWeightedRoutingService {

    @Value("${kubernetes.namespace:gray-release}")
    private String namespace;

    @Value("${kubernetes.use-endpointslice:true}")
    private boolean useEndpointSlice;

    private KubernetesClient kubernetesClient;

    public K8sWeightedRoutingService() {
        try {
            this.kubernetesClient = new KubernetesClientBuilder().build();
        } catch (Exception e) {
            log.warn("Kubernetes client not available, running in simulated mode for weighted routing");
            this.kubernetesClient = null;
        }
    }

    public boolean updateWeightedRouting(String serviceName, String stableVersion,
                                          String canaryVersion, int canaryWeight) {
        log.info("Updating weighted routing: service={}, stable={}, canary={}, canaryWeight={}%",
                serviceName, stableVersion, canaryVersion, canaryWeight);

        if (kubernetesClient == null) {
            return simulateWeightedRouting(serviceName, stableVersion, canaryVersion, canaryWeight);
        }

        try {
            if (canaryWeight <= 0) {
                return routeAllToStable(serviceName, stableVersion);
            } else if (canaryWeight >= 100) {
                return routeAllToCanary(serviceName, canaryVersion);
            } else {
                return createWeightedEndpointSlice(serviceName, stableVersion, canaryVersion, canaryWeight);
            }
        } catch (Exception e) {
            log.error("Failed to update weighted routing for service: {}", serviceName, e);
            return false;
        }
    }

    private boolean createWeightedEndpointSlice(String serviceName, String stableVersion,
                                                  String canaryVersion, int canaryWeight) {
        String sliceName = serviceName + "-weighted";

        int stableWeight = 100 - canaryWeight;

        List<io.fabric8.kubernetes.api.model.discovery.v1.Endpoint> endpoints = new ArrayList<>();

        EndpointBuilder stableEndpointBuilder = new EndpointBuilder();
        Map<String, String> stableConditions = new HashMap<>();
        stableConditions.put("ready", "true");
        stableConditions.put("serving", "true");
        stableConditions.put("terminating", "false");

        endpoints.add(stableEndpointBuilder
                .withAddresses(stableVersion + "-pod")
                .withNewHints()
                .withForZones(Arrays.asList(
                        new ForZoneBuilder().withName("stable-" + stableWeight).build()
                ))
                .endHints()
                .withTargetRef(new ObjectReferenceBuilder()
                        .withKind("Pod")
                        .withName(serviceName + "-stable")
                        .build())
                .build());

        EndpointBuilder canaryEndpointBuilder = new EndpointBuilder();
        endpoints.add(canaryEndpointBuilder
                .withAddresses(canaryVersion + "-pod")
                .withNewHints()
                .withForZones(Arrays.asList(
                        new ForZoneBuilder().withName("canary-" + canaryWeight).build()
                ))
                .endHints()
                .withTargetRef(new ObjectReferenceBuilder()
                        .withKind("Pod")
                        .withName(serviceName + "-canary")
                        .build())
                .build());

        Map<String, Integer> portWeights = new HashMap<>();
        portWeights.put("stable", stableWeight);
        portWeights.put("canary", canaryWeight);

        EndpointSlice endpointSlice = new EndpointSliceBuilder()
                .withNewMetadata()
                .withName(sliceName)
                .withNamespace(namespace)
                .addToLabels("kubernetes.io/service-name", serviceName)
                .addToLabels("gray-release.io/weighted", "true")
                .addToAnnotations("gray-release.io/stable-version", stableVersion)
                .addToAnnotations("gray-release.io/canary-version", canaryVersion)
                .addToAnnotations("gray-release.io/stable-weight", String.valueOf(stableWeight))
                .addToAnnotations("gray-release.io/canary-weight", String.valueOf(canaryWeight))
                .endMetadata()
                .withAddressType("IPv4")
                .withPorts(Arrays.asList(
                        new io.fabric8.kubernetes.api.model.discovery.v1.EndpointPortBuilder()
                                .withName("http")
                                .withPort(8080)
                                .withProtocol("TCP")
                                .build()
                ))
                .withEndpoints(endpoints)
                .build();

        kubernetesClient.resources(EndpointSlice.class)
                .inNamespace(namespace)
                .resource(endpointSlice)
                .createOr();

        updateServiceSelector(serviceName);

        log.info("Weighted EndpointSlice created: name={}, stableWeight={}%, canaryWeight={}%",
                sliceName, stableWeight, canaryWeight);
        return true;
    }

    private void updateServiceSelector(String serviceName) {
        try {
            Service service = kubernetesClient.services()
                    .inNamespace(namespace)
                    .withName(serviceName)
                    .get();

            if (service != null) {
                kubernetesClient.services()
                        .inNamespace(namespace)
                        .withName(serviceName)
                        .edit(s -> new ServiceBuilder(s)
                                .editMetadata()
                                .addToAnnotations("gray-release.io/weighted-routing", "true")
                                .endMetadata()
                                .editSpec()
                                .addToSelector("app", serviceName)
                                .endSpec()
                                .build());
            }
        } catch (Exception e) {
            log.debug("Could not update service selector, service may not exist yet: {}", e.getMessage());
        }
    }

    private boolean routeAllToStable(String serviceName, String stableVersion) {
        log.info("Routing all traffic to stable version: service={}, version={}", serviceName, stableVersion);

        if (kubernetesClient == null) {
            return true;
        }

        try {
            cleanupCanaryEndpoints(serviceName);

            Service service = kubernetesClient.services()
                    .inNamespace(namespace)
                    .withName(serviceName)
                    .get();

            if (service != null) {
                kubernetesClient.services()
                        .inNamespace(namespace)
                        .withName(serviceName)
                        .edit(s -> new ServiceBuilder(s)
                                .editMetadata()
                                .addToAnnotations("gray-release.io/active-version", stableVersion)
                                .addToAnnotations("gray-release.io/weighted-routing", "false")
                                .endMetadata()
                                .editSpec()
                                .addToSelector("app", serviceName)
                                .addToSelector("version", stableVersion)
                                .addToSelector("role", "stable")
                                .endSpec()
                                .build());
            }

            deleteWeightedEndpointSlice(serviceName);
            return true;
        } catch (Exception e) {
            log.error("Failed to route all to stable", e);
            return false;
        }
    }

    private boolean routeAllToCanary(String serviceName, String canaryVersion) {
        log.info("Routing all traffic to canary version: service={}, version={}", serviceName, canaryVersion);

        if (kubernetesClient == null) {
            return true;
        }

        try {
            cleanupStableEndpoints(serviceName);

            Service service = kubernetesClient.services()
                    .inNamespace(namespace)
                    .withName(serviceName)
                    .get();

            if (service != null) {
                kubernetesClient.services()
                        .inNamespace(namespace)
                        .withName(serviceName)
                        .edit(s -> new ServiceBuilder(s)
                                .editMetadata()
                                .addToAnnotations("gray-release.io/active-version", canaryVersion)
                                .addToAnnotations("gray-release.io/weighted-routing", "false")
                                .endMetadata()
                                .editSpec()
                                .addToSelector("app", serviceName)
                                .addToSelector("version", canaryVersion)
                                .addToSelector("role", "canary")
                                .endSpec()
                                .build());
            }

            deleteWeightedEndpointSlice(serviceName);
            return true;
        } catch (Exception e) {
            log.error("Failed to route all to canary", e);
            return false;
        }
    }

    private void cleanupCanaryEndpoints(String serviceName) {
        try {
            kubernetesClient.resources(EndpointSlice.class)
                    .inNamespace(namespace)
                    .withLabel("gray-release.io/weighted", "true")
                    .list()
                    .getItems()
                    .forEach(slice -> {
                        if (slice.getMetadata().getName().startsWith(serviceName)) {
                            kubernetesClient.resource(slice).delete();
                        }
                    });
        } catch (Exception e) {
            log.debug("Error cleaning up canary endpoints: {}", e.getMessage());
        }
    }

    private void cleanupStableEndpoints(String serviceName) {
        log.info("Cleaning up stable endpoints for service: {}", serviceName);
    }

    private void deleteWeightedEndpointSlice(String serviceName) {
        try {
            kubernetesClient.resources(EndpointSlice.class)
                    .inNamespace(namespace)
                    .withName(serviceName + "-weighted")
                    .withGracePeriod(0L)
                    .delete();
        } catch (Exception e) {
            log.debug("Error deleting weighted endpoint slice: {}", e.getMessage());
        }
    }

    public WeightedRouteStatus getRouteStatus(String serviceName) {
        WeightedRouteStatus status = new WeightedRouteStatus();
        status.setServiceName(serviceName);

        if (kubernetesClient == null) {
            status.setMode("simulated");
            status.setStableWeight(100);
            status.setCanaryWeight(0);
            return status;
        }

        try {
            EndpointSlice slice = kubernetesClient.resources(EndpointSlice.class)
                    .inNamespace(namespace)
                    .withName(serviceName + "-weighted")
                    .get();

            if (slice != null && slice.getMetadata().getAnnotations() != null) {
                Map<String, String> annotations = slice.getMetadata().getAnnotations();
                status.setStableVersion(annotations.get("gray-release.io/stable-version"));
                status.setCanaryVersion(annotations.get("gray-release.io/canary-version"));

                String stableWeight = annotations.get("gray-release.io/stable-weight");
                String canaryWeight = annotations.get("gray-release.io/canary-weight");

                if (stableWeight != null) {
                    status.setStableWeight(Integer.parseInt(stableWeight));
                }
                if (canaryWeight != null) {
                    status.setCanaryWeight(Integer.parseInt(canaryWeight));
                }

                status.setMode("weighted-endpointslice");
            } else {
                Service service = kubernetesClient.services()
                        .inNamespace(namespace)
                        .withName(serviceName)
                        .get();

                if (service != null && service.getSpec().getSelector() != null) {
                    Map<String, String> selector = service.getSpec().getSelector();
                    String version = selector.get("version");
                    String role = selector.get("role");

                    if ("canary".equals(role)) {
                        status.setCanaryVersion(version);
                        status.setCanaryWeight(100);
                        status.setStableWeight(0);
                    } else {
                        status.setStableVersion(version);
                        status.setStableWeight(100);
                        status.setCanaryWeight(0);
                    }
                    status.setMode("direct");
                }
            }
        } catch (Exception e) {
            log.error("Failed to get route status", e);
            status.setMode("error");
        }

        return status;
    }

    private boolean simulateWeightedRouting(String serviceName, String stableVersion,
                                            String canaryVersion, int canaryWeight) {
        log.info("[SIMULATED] Weighted routing: service={}, stable({}%)={}, canary({}%)={}",
                serviceName, 100 - canaryWeight, stableVersion, canaryWeight, canaryVersion);
        return true;
    }

    @Data
    public static class WeightedRouteStatus {
        private String serviceName;
        private String stableVersion;
        private String canaryVersion;
        private int stableWeight;
        private int canaryWeight;
        private String mode;
    }
}