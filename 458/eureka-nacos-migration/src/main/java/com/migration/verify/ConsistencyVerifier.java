package com.migration.verify;

import com.migration.client.EurekaClient;
import com.migration.client.NacosClient;
import com.migration.model.ConsistencyCheckResult;
import com.migration.model.ConsistencyCheckResult.MetadataDiff;
import com.migration.model.ConsistencyCheckResult.MetadataDiff.DiffType;
import com.migration.model.ConsistencyCheckResult.ServiceDifference;
import com.migration.model.ConsistencyCheckResult.ServiceDifference.DifferenceType;
import com.migration.model.ServiceInstance;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Component
public class ConsistencyVerifier {

    private final EurekaClient eurekaClient;
    private final NacosClient nacosClient;
    private final List<String> ignoredMetadataKeys = Arrays.asList("migratedFrom", "migratedAt");

    public ConsistencyVerifier(EurekaClient eurekaClient, NacosClient nacosClient) {
        this.eurekaClient = eurekaClient;
        this.nacosClient = nacosClient;
    }

    public ConsistencyCheckResult verify(Map<String, List<ServiceInstance>> expectedSnapshot) {
        String checkId = UUID.randomUUID().toString();
        long startTime = System.currentTimeMillis();

        List<ServiceDifference> differences = new ArrayList<>();
        List<String> alerts = new ArrayList<>();
        int matchedServices = 0;
        int onlyInEureka = 0;
        int onlyInNacos = 0;
        int mismatched = 0;

        List<String> eurekaServiceIds = eurekaClient.getAllServiceIds();
        List<String> nacosServiceIds = nacosClient.getAllServiceIds();

        Set<String> allServiceIds = new HashSet<>();
        allServiceIds.addAll(eurekaServiceIds);
        allServiceIds.addAll(nacosServiceIds);

        for (String serviceId : allServiceIds) {
            List<ServiceInstance> eurekaInstances = eurekaClient.getInstances(serviceId);
            List<ServiceInstance> nacosInstances = nacosClient.getInstances(serviceId);

            boolean eurekaHas = !eurekaInstances.isEmpty();
            boolean nacosHas = !nacosInstances.isEmpty();

            if (eurekaHas && !nacosHas) {
                onlyInEureka++;
                String detail = "Service only exists in Eureka with " + eurekaInstances.size() + " instances";
                differences.add(ServiceDifference.builder()
                        .serviceId(serviceId)
                        .type(DifferenceType.ONLY_IN_EUREKA)
                        .eurekaInstances(String.valueOf(eurekaInstances.size()))
                        .nacosInstances("0")
                        .detail(detail)
                        .build());
                alerts.add("[ALERT] Service '" + serviceId + "': " + detail);
            } else if (!eurekaHas && nacosHas) {
                onlyInNacos++;
                String detail = "Service only exists in Nacos with " + nacosInstances.size() + " instances";
                differences.add(ServiceDifference.builder()
                        .serviceId(serviceId)
                        .type(DifferenceType.ONLY_IN_NACOS)
                        .eurekaInstances("0")
                        .nacosInstances(String.valueOf(nacosInstances.size()))
                        .detail(detail)
                        .build());
                alerts.add("[ALERT] Service '" + serviceId + "': " + detail);
            } else if (eurekaHas && nacosHas) {
                ServiceDifference instanceDiff = compareInstances(serviceId, eurekaInstances, nacosInstances);
                if (instanceDiff != null) {
                    mismatched++;
                    differences.add(instanceDiff);
                    if (instanceDiff.getType() == DifferenceType.METADATA_MISMATCH && instanceDiff.getMetadataDiffs() != null) {
                        for (MetadataDiff md : instanceDiff.getMetadataDiffs()) {
                            alerts.add("[ALERT] Metadata mismatch - service=" + serviceId
                                    + ", instance=" + md.getInstanceKey()
                                    + ", key=" + md.getKey()
                                    + ", eureka=" + md.getEurekaValue()
                                    + ", nacos=" + md.getNacosValue()
                                    + ", type=" + md.getDiffType());
                        }
                    } else {
                        alerts.add("[ALERT] Service '" + serviceId + "': " + instanceDiff.getDetail());
                    }
                } else {
                    matchedServices++;
                }
            }
        }

        boolean consistent = differences.isEmpty();
        ConsistencyCheckResult result = ConsistencyCheckResult.builder()
                .checkId(checkId)
                .timestamp(startTime)
                .consistent(consistent)
                .totalServices(allServiceIds.size())
                .matchedServices(matchedServices)
                .mismatchedServices(mismatched)
                .onlyInEureka(onlyInEureka)
                .onlyInNacos(onlyInNacos)
                .differences(differences)
                .alerts(alerts)
                .build();

        log.info("Consistency check {}: {} - matched={}, mismatched={}, onlyEureka={}, onlyNacos={}, alerts={}",
                checkId, consistent ? "PASSED" : "FAILED",
                matchedServices, mismatched, onlyInEureka, onlyInNacos, alerts.size());

        if (!alerts.isEmpty()) {
            for (String alert : alerts) {
                log.warn(alert);
            }
        }

        return result;
    }

    public ConsistencyCheckResult quickVerify() {
        Map<String, List<ServiceInstance>> eurekaSnapshot = new HashMap<>();
        List<String> eurekaServiceIds = eurekaClient.getAllServiceIds();
        for (String serviceId : eurekaServiceIds) {
            eurekaSnapshot.put(serviceId, eurekaClient.getInstances(serviceId));
        }
        return verify(eurekaSnapshot);
    }

    public ConsistencyCheckResult verifyWithMetadataCheck(Map<String, List<ServiceInstance>> expectedSnapshot) {
        return verify(expectedSnapshot);
    }

    public List<MetadataDiff> compareInstanceMetadata(String serviceId, String instanceKey) {
        List<ServiceInstance> eurekaInstances = eurekaClient.getInstances(serviceId);
        List<ServiceInstance> nacosInstances = nacosClient.getInstances(serviceId);

        ServiceInstance eurekaInst = findInstance(eurekaInstances, instanceKey);
        ServiceInstance nacosInst = findInstance(nacosInstances, instanceKey);

        if (eurekaInst == null || nacosInst == null) {
            return Collections.emptyList();
        }

        return compareMetadata(eurekaInst, nacosInst, instanceKey);
    }

    private ServiceDifference compareInstances(String serviceId,
                                                List<ServiceInstance> eurekaInstances,
                                                List<ServiceInstance> nacosInstances) {
        if (eurekaInstances.size() != nacosInstances.size()) {
            return ServiceDifference.builder()
                    .serviceId(serviceId)
                    .type(DifferenceType.INSTANCE_COUNT_MISMATCH)
                    .eurekaInstances(String.valueOf(eurekaInstances.size()))
                    .nacosInstances(String.valueOf(nacosInstances.size()))
                    .detail(String.format("Instance count mismatch: Eureka=%d, Nacos=%d",
                            eurekaInstances.size(), nacosInstances.size()))
                    .build();
        }

        Map<String, ServiceInstance> eurekaMap = eurekaInstances.stream()
                .collect(Collectors.toMap(i -> i.getHost() + ":" + i.getPort(), i -> i, (a, b) -> a));

        Map<String, ServiceInstance> nacosMap = nacosInstances.stream()
                .collect(Collectors.toMap(i -> i.getHost() + ":" + i.getPort(), i -> i, (a, b) -> a));

        for (Map.Entry<String, ServiceInstance> entry : eurekaMap.entrySet()) {
            ServiceInstance nacosInst = nacosMap.get(entry.getKey());
            if (nacosInst == null) {
                return ServiceDifference.builder()
                        .serviceId(serviceId)
                        .type(DifferenceType.INSTANCE_COUNT_MISMATCH)
                        .eurekaInstances(entry.getKey())
                        .nacosInstances("MISSING")
                        .detail("Instance " + entry.getKey() + " exists in Eureka but not in Nacos")
                        .build();
            }

            List<MetadataDiff> metadataDiffs = compareMetadata(entry.getValue(), nacosInst, entry.getKey());
            if (!metadataDiffs.isEmpty()) {
                return ServiceDifference.builder()
                        .serviceId(serviceId)
                        .type(DifferenceType.METADATA_MISMATCH)
                        .eurekaInstances(entry.getValue().getMetadata().toString())
                        .nacosInstances(nacosInst.getMetadata().toString())
                        .detail("Metadata mismatch for instance " + entry.getKey() + ": " + metadataDiffs.size() + " differences")
                        .metadataDiffs(metadataDiffs)
                        .build();
            }

            if (!statusMatches(entry.getValue(), nacosInst)) {
                return ServiceDifference.builder()
                        .serviceId(serviceId)
                        .type(DifferenceType.STATUS_MISMATCH)
                        .eurekaInstances(entry.getValue().getStatus())
                        .nacosInstances(nacosInst.getStatus())
                        .detail("Status mismatch for instance " + entry.getKey())
                        .build();
            }
        }

        return null;
    }

    private List<MetadataDiff> compareMetadata(ServiceInstance eurekaInst, ServiceInstance nacosInst, String instanceKey) {
        List<MetadataDiff> diffs = new ArrayList<>();

        Map<String, String> eurekaMeta = eurekaInst.getMetadata() != null ? eurekaInst.getMetadata() : Collections.emptyMap();
        Map<String, String> nacosMeta = nacosInst.getMetadata() != null ? nacosInst.getMetadata() : Collections.emptyMap();

        Map<String, String> filteredEurekaMeta = eurekaMeta.entrySet().stream()
                .filter(e -> !ignoredMetadataKeys.contains(e.getKey()))
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));

        Map<String, String> filteredNacosMeta = nacosMeta.entrySet().stream()
                .filter(e -> !ignoredMetadataKeys.contains(e.getKey()))
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));

        Set<String> allKeys = new HashSet<>();
        allKeys.addAll(filteredEurekaMeta.keySet());
        allKeys.addAll(filteredNacosMeta.keySet());

        for (String key : allKeys) {
            boolean inEureka = filteredEurekaMeta.containsKey(key);
            boolean inNacos = filteredNacosMeta.containsKey(key);

            if (inEureka && !inNacos) {
                diffs.add(MetadataDiff.builder()
                        .instanceKey(instanceKey)
                        .key(key)
                        .eurekaValue(filteredEurekaMeta.get(key))
                        .nacosValue(null)
                        .diffType(DiffType.MISSING_IN_NACOS)
                        .build());
            } else if (!inEureka && inNacos) {
                diffs.add(MetadataDiff.builder()
                        .instanceKey(instanceKey)
                        .key(key)
                        .eurekaValue(null)
                        .nacosValue(filteredNacosMeta.get(key))
                        .diffType(DiffType.MISSING_IN_EUREKA)
                        .build());
            } else if (inEureka && inNacos) {
                String eVal = filteredEurekaMeta.get(key);
                String nVal = filteredNacosMeta.get(key);
                if (!Objects.equals(eVal, nVal)) {
                    diffs.add(MetadataDiff.builder()
                            .instanceKey(instanceKey)
                            .key(key)
                            .eurekaValue(eVal)
                            .nacosValue(nVal)
                            .diffType(DiffType.VALUE_MISMATCH)
                            .build());
                }
            }
        }

        return diffs;
    }

    private boolean metadataMatches(ServiceInstance eurekaInst, ServiceInstance nacosInst) {
        return compareMetadata(eurekaInst, nacosInst, "check").isEmpty();
    }

    private boolean statusMatches(ServiceInstance eurekaInst, ServiceInstance nacosInst) {
        String eurekaStatus = eurekaInst.getStatus();
        String nacosStatus = nacosInst.getStatus();

        if ("UP".equals(eurekaStatus) && "UP".equals(nacosStatus)) return true;
        if ("DOWN".equals(eurekaStatus) && "DOWN".equals(nacosStatus)) return true;
        if ("OUT_OF_SERVICE".equals(eurekaStatus) && "DOWN".equals(nacosStatus)) return true;
        if ("STARTING".equals(eurekaStatus) && "DOWN".equals(nacosStatus)) return true;

        return eurekaStatus.equals(nacosStatus);
    }

    private ServiceInstance findInstance(List<ServiceInstance> instances, String instanceKey) {
        for (ServiceInstance inst : instances) {
            String key = inst.getHost() + ":" + inst.getPort();
            if (key.equals(instanceKey)) {
                return inst;
            }
        }
        return null;
    }

    public List<String> getIgnoredMetadataKeys() {
        return ignoredMetadataKeys;
    }
}
