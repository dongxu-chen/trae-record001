package com.flink.recommender.cost;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NetworkCostModel {

    private double costPerGbInTraffic;
    private double costPerGbOutTraffic;
    private double costPerGbIntraDcTraffic;
    private double costPerGbCrossRackTraffic;
    private double costPerGbCrossAzTraffic;

    private double avgBytesPerRecordIn;
    private double avgBytesPerRecordOut;
    private double crossRackTrafficRatio;
    private double crossAzTrafficRatio;
    private double intraDcTrafficRatio;

    private long recordsPerSecond;
    private long networkInBytesPerSec;
    private long networkOutBytesPerSec;

    public static NetworkCostModel getDefaultModel() {
        return NetworkCostModel.builder()
                .costPerGbInTraffic(0.0)
                .costPerGbOutTraffic(0.08)
                .costPerGbIntraDcTraffic(0.01)
                .costPerGbCrossRackTraffic(0.02)
                .costPerGbCrossAzTraffic(0.05)
                .avgBytesPerRecordIn(512)
                .avgBytesPerRecordOut(256)
                .crossRackTrafficRatio(0.3)
                .crossAzTrafficRatio(0.1)
                .intraDcTrafficRatio(0.6)
                .recordsPerSecond(10000)
                .networkInBytesPerSec(0)
                .networkOutBytesPerSec(0)
                .build();
    }

    public static NetworkCostModel getHighTrafficModel() {
        NetworkCostModel model = getDefaultModel();
        model.setAvgBytesPerRecordIn(2048);
        model.setAvgBytesPerRecordOut(1024);
        model.setCrossRackTrafficRatio(0.4);
        model.setCrossAzTrafficRatio(0.2);
        model.setRecordsPerSecond(50000);
        return model;
    }

    public static NetworkCostModel getLowTrafficModel() {
        NetworkCostModel model = getDefaultModel();
        model.setAvgBytesPerRecordIn(256);
        model.setAvgBytesPerRecordOut(128);
        model.setCrossRackTrafficRatio(0.2);
        model.setCrossAzTrafficRatio(0.05);
        model.setRecordsPerSecond(1000);
        return model;
    }
}
