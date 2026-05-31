package com.flink.recommender.cost;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.*;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RackTopology {

    private List<RackInfo> racks = new ArrayList<>();
    private int availabilityZones;
    private int racksPerAz;
    private int taskManagersPerRack;
    private double crossRackBandwidthGbps;
    private double intraRackBandwidthGbps;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RackInfo {
        private String rackId;
        private String availabilityZone;
        private List<String> taskManagers = new ArrayList<>();
        private int networkSwitchCapacityGbps;
        private double currentUtilization;
    }

    public static RackTopology getDefaultTopology(int numTaskManagers) {
        RackTopology topology = new RackTopology();
        topology.setAvailabilityZones(2);
        topology.setRacksPerAz(4);
        topology.setTaskManagersPerRack(4);
        topology.setCrossRackBandwidthGbps(10);
        topology.setIntraRackBandwidthGbps(25);

        int taskManagerIndex = 0;
        for (int az = 0; az < topology.getAvailabilityZones(); az++) {
            for (int rack = 0; rack < topology.getRacksPerAz(); rack++) {
                RackInfo rackInfo = new RackInfo();
                rackInfo.setRackId("rack-" + az + "-" + rack);
                rackInfo.setAvailabilityZone("az-" + az);
                rackInfo.setNetworkSwitchCapacityGbps(40);
                rackInfo.setCurrentUtilization(0.3);

                for (int tm = 0; tm < topology.getTaskManagersPerRack()
                        && taskManagerIndex < numTaskManagers; tm++) {
                    rackInfo.getTaskManagers().add("taskmanager-" + taskManagerIndex);
                    taskManagerIndex++;
                }

                topology.getRacks().add(rackInfo);
            }
        }

        return topology;
    }

    public Map<String, String> getTaskManagerToRackMapping() {
        Map<String, String> mapping = new HashMap<>();
        for (RackInfo rack : racks) {
            for (String tm : rack.getTaskManagers()) {
                mapping.put(tm, rack.getRackId());
            }
        }
        return mapping;
    }

    public Map<String, String> getTaskManagerToAzMapping() {
        Map<String, String> mapping = new HashMap<>();
        for (RackInfo rack : racks) {
            for (String tm : rack.getTaskManagers()) {
                mapping.put(tm, rack.getAvailabilityZone());
            }
        }
        return mapping;
    }

    public double calculateCrossRackTrafficRatio(int numTaskManagers) {
        if (numTaskManagers <= 1) return 0;

        int totalRacks = getRacksWithTaskManagers();
        if (totalRacks <= 1) return 0;

        int tmsPerRack = (int) Math.ceil((double) numTaskManagers / totalRacks);
        double intraRackCombinations = tmsPerRack * (tmsPerRack - 1) / 2.0 * totalRacks;
        double totalCombinations = numTaskManagers * (numTaskManagers - 1) / 2.0;

        return 1 - (intraRackCombinations / totalCombinations);
    }

    public double calculateCrossAzTrafficRatio(int numTaskManagers) {
        if (numTaskManagers <= 1 || availabilityZones <= 1) return 0;

        int tmsPerAz = (int) Math.ceil((double) numTaskManagers / availabilityZones);
        double intraAzCombinations = tmsPerAz * (tmsPerAz - 1) / 2.0 * availabilityZones;
        double totalCombinations = numTaskManagers * (numTaskManagers - 1) / 2.0;

        return 1 - (intraAzCombinations / totalCombinations);
    }

    private int getRacksWithTaskManagers() {
        return (int) racks.stream()
                .filter(r -> !r.getTaskManagers().isEmpty())
                .count();
    }

    public List<String> getTaskManagersInSameRack(String taskManager) {
        for (RackInfo rack : racks) {
            if (rack.getTaskManagers().contains(taskManager)) {
                List<String> result = new ArrayList<>(rack.getTaskManagers());
                result.remove(taskManager);
                return result;
            }
        }
        return Collections.emptyList();
    }

    public boolean areInSameRack(String tm1, String tm2) {
        Map<String, String> mapping = getTaskManagerToRackMapping();
        String rack1 = mapping.get(tm1);
        String rack2 = mapping.get(tm2);
        return rack1 != null && rack1.equals(rack2);
    }

    public boolean areInSameAz(String tm1, String tm2) {
        Map<String, String> mapping = getTaskManagerToAzMapping();
        String az1 = mapping.get(tm1);
        String az2 = mapping.get(tm2);
        return az1 != null && az1.equals(az2);
    }

    public double estimateNetworkCostPerGb(
            String sourceTm,
            String destTm,
            NetworkCostModel costModel) {

        if (areInSameRack(sourceTm, destTm)) {
            return 0;
        } else if (areInSameAz(sourceTm, destTm)) {
            return costModel.getCostPerGbCrossRackTraffic();
        } else {
            return costModel.getCostPerGbCrossAzTraffic();
        }
    }
}
