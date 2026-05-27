package com.grayrelease.release.service;

import io.fabric8.kubernetes.api.model.apps.Deployment;
import io.fabric8.kubernetes.api.model.apps.DeploymentBuilder;
import io.fabric8.kubernetes.api.model.Service;
import io.fabric8.kubernetes.api.model.ServiceBuilder;
import io.fabric8.kubernetes.client.KubernetesClient;
import io.fabric8.kubernetes.client.KubernetesClientBuilder;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
public class K8sDeploymentService {

    @Value("${kubernetes.namespace:gray-release}")
    private String namespace;

    private KubernetesClient kubernetesClient;

    public K8sDeploymentService() {
        try {
            this.kubernetesClient = new KubernetesClientBuilder().build();
        } catch (Exception e) {
            log.warn("Kubernetes client not available, running in simulated mode");
            this.kubernetesClient = null;
        }
    }

    public boolean deployCanaryVersion(String serviceName, String version, String image) {
        log.info("Deploying canary version: service={}, version={}, image={}", serviceName, version, image);

        if (kubernetesClient == null) {
            return simulateDeployment(serviceName, version, image, "canary");
        }

        try {
            String deploymentName = serviceName + "-canary-" + version;
            Map<String, String> labels = new HashMap<>();
            labels.put("app", serviceName);
            labels.put("version", version);
            labels.put("role", "canary");

            Deployment deployment = new DeploymentBuilder()
                    .withNewMetadata()
                    .withName(deploymentName)
                    .withNamespace(namespace)
                    .addToLabels(labels)
                    .endMetadata()
                    .withNewSpec()
                    .withReplicas(1)
                    .withNewSelector()
                    .addToMatchLabels(labels)
                    .endSelector()
                    .withNewTemplate()
                    .withNewMetadata()
                    .addToLabels(labels)
                    .endMetadata()
                    .withNewSpec()
                    .addNewContainer()
                    .withName(serviceName)
                    .withImage(image)
                    .addNewPort()
                    .withContainerPort(8080)
                    .endPort()
                    .endContainer()
                    .endSpec()
                    .endTemplate()
                    .endSpec()
                    .build();

            kubernetesClient.apps().deployments()
                    .inNamespace(namespace)
                    .resource(deployment)
                    .createOr();

            log.info("Canary deployment created: {}", deploymentName);
            return true;
        } catch (Exception e) {
            log.error("Failed to deploy canary version", e);
            return false;
        }
    }

    public boolean deployGreenVersion(String serviceName, String version, String image) {
        log.info("Deploying green version: service={}, version={}, image={}", serviceName, version, image);

        if (kubernetesClient == null) {
            return simulateDeployment(serviceName, version, image, "green");
        }

        try {
            String deploymentName = serviceName + "-green-" + version;
            Map<String, String> labels = new HashMap<>();
            labels.put("app", serviceName);
            labels.put("version", version);
            labels.put("role", "green");

            Deployment deployment = new DeploymentBuilder()
                    .withNewMetadata()
                    .withName(deploymentName)
                    .withNamespace(namespace)
                    .addToLabels(labels)
                    .endMetadata()
                    .withNewSpec()
                    .withReplicas(2)
                    .withNewSelector()
                    .addToMatchLabels(labels)
                    .endSelector()
                    .withNewTemplate()
                    .withNewMetadata()
                    .addToLabels(labels)
                    .endMetadata()
                    .withNewSpec()
                    .addNewContainer()
                    .withName(serviceName)
                    .withImage(image)
                    .addNewPort()
                    .withContainerPort(8080)
                    .endPort()
                    .endContainer()
                    .endSpec()
                    .endTemplate()
                    .endSpec()
                    .build();

            kubernetesClient.apps().deployments()
                    .inNamespace(namespace)
                    .resource(deployment)
                    .createOr();

            log.info("Green deployment created: {}", deploymentName);
            return true;
        } catch (Exception e) {
            log.error("Failed to deploy green version", e);
            return false;
        }
    }

    public void promoteCanaryToStable(String serviceName, String version) {
        log.info("Promoting canary to stable: service={}, version={}", serviceName, version);

        if (kubernetesClient == null) {
            return;
        }

        try {
            String canaryDeployment = serviceName + "-canary-" + version;
            String stableDeployment = serviceName + "-stable";

            kubernetesClient.apps().deployments()
                    .inNamespace(namespace)
                    .withName(canaryDeployment)
                    .edit(d -> new DeploymentBuilder(d)
                            .editMetadata()
                            .withName(stableDeployment)
                            .removeFromLabels("role")
                            .addToLabels("role", "stable")
                            .endMetadata()
                            .build());

            log.info("Canary promoted to stable: service={}, version={}", serviceName, version);
        } catch (Exception e) {
            log.error("Failed to promote canary to stable", e);
        }
    }

    public void promoteGreenToStable(String serviceName, String version) {
        log.info("Promoting green to stable: service={}, version={}", serviceName, version);

        if (kubernetesClient == null) {
            return;
        }

        try {
            String greenDeployment = serviceName + "-green-" + version;
            String stableDeployment = serviceName + "-stable";

            kubernetesClient.apps().deployments()
                    .inNamespace(namespace)
                    .withName(greenDeployment)
                    .edit(d -> new DeploymentBuilder(d)
                            .editMetadata()
                            .withName(stableDeployment)
                            .removeFromLabels("role")
                            .addToLabels("role", "stable")
                            .endMetadata()
                            .build());

            log.info("Green promoted to stable: service={}, version={}", serviceName, version);
        } catch (Exception e) {
            log.error("Failed to promote green to stable", e);
        }
    }

    public void rollbackCanaryVersion(String serviceName, String version) {
        log.info("Rolling back canary version: service={}, version={}", serviceName, version);

        if (kubernetesClient == null) {
            return;
        }

        try {
            String deploymentName = serviceName + "-canary-" + version;

            kubernetesClient.apps().deployments()
                    .inNamespace(namespace)
                    .withName(deploymentName)
                    .withGracePeriod(0L)
                    .delete();

            log.info("Canary deployment deleted: {}", deploymentName);
        } catch (Exception e) {
            log.error("Failed to rollback canary version", e);
        }
    }

    public void rollbackGreenVersion(String serviceName, String version) {
        log.info("Rolling back green version: service={}, version={}", serviceName, version);

        if (kubernetesClient == null) {
            return;
        }

        try {
            String deploymentName = serviceName + "-green-" + version;

            kubernetesClient.apps().deployments()
                    .inNamespace(namespace)
                    .withName(deploymentName)
                    .withGracePeriod(0L)
                    .delete();

            log.info("Green deployment deleted: {}", deploymentName);
        } catch (Exception e) {
            log.error("Failed to rollback green version", e);
        }
    }

    public void scaleDownBlueVersion(String serviceName, String version) {
        log.info("Scaling down blue version: service={}, version={}", serviceName, version);

        if (kubernetesClient == null) {
            return;
        }

        try {
            String deploymentName = serviceName + "-blue-" + version;

            kubernetesClient.apps().deployments()
                    .inNamespace(namespace)
                    .withName(deploymentName)
                    .scale(0, true);

            log.info("Blue deployment scaled to 0: {}", deploymentName);
        } catch (Exception e) {
            log.error("Failed to scale down blue version", e);
        }
    }

    private boolean simulateDeployment(String serviceName, String version, String image, String role) {
        log.info("Simulating {} deployment: service={}, version={}, image={}", role, serviceName, version, image);
        return true;
    }
}