package com.dlq.platform.analysis.visualization;

import com.dlq.platform.common.enums.DeadReasonTypeEnum;
import com.dlq.platform.common.enums.MqTypeEnum;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

@Slf4j
@Service
@RequiredArgsConstructor
public class DeadLetterVisualizationService {

    public static class TimelineDataPoint {
        private String timestamp;
        private long count;
        private Map<String, Long> breakdown;

        public TimelineDataPoint(String timestamp, long count) {
            this.timestamp = timestamp;
            this.count = count;
            this.breakdown = new HashMap<>();
        }

        public String getTimestamp() { return timestamp; }
        public void setTimestamp(String timestamp) { this.timestamp = timestamp; }
        public long getCount() { return count; }
        public void setCount(long count) { this.count = count; }
        public Map<String, Long> getBreakdown() { return breakdown; }
        public void setBreakdown(Map<String, Long> breakdown) { this.breakdown = breakdown; }
    }

    public static class HeatmapCell {
        private int x;
        private int y;
        private long value;
        private String label;

        public HeatmapCell(int x, int y, long value, String label) {
            this.x = x;
            this.y = y;
            this.value = value;
            this.label = label;
        }

        public int getX() { return x; }
        public int getY() { return y; }
        public long getValue() { return value; }
        public String getLabel() { return label; }
    }

    public static class HeatmapData {
        private List<HeatmapCell> cells;
        private List<String> xLabels;
        private List<String> yLabels;
        private long maxValue;
        private long minValue;

        public HeatmapData() {
            this.cells = new ArrayList<>();
            this.xLabels = new ArrayList<>();
            this.yLabels = new ArrayList<>();
        }

        public List<HeatmapCell> getCells() { return cells; }
        public void setCells(List<HeatmapCell> cells) { this.cells = cells; }
        public List<String> getXLabels() { return xLabels; }
        public void setXLabels(List<String> xLabels) { this.xLabels = xLabels; }
        public List<String> getYLabels() { return yLabels; }
        public void setYLabels(List<String> yLabels) { this.yLabels = yLabels; }
        public long getMaxValue() { return maxValue; }
        public void setMaxValue(long maxValue) { this.maxValue = maxValue; }
        public long getMinValue() { return minValue; }
        public void setMinValue(long minValue) { this.minValue = minValue; }
    }

    public static class SankeyNode {
        private String name;
        private int category;

        public SankeyNode(String name, int category) {
            this.name = name;
            this.category = category;
        }

        public String getName() { return name; }
        public int getCategory() { return category; }
    }

    public static class SankeyLink {
        private int source;
        private int target;
        private long value;

        public SankeyLink(int source, int target, long value) {
            this.source = source;
            this.target = target;
            this.value = value;
        }

        public int getSource() { return source; }
        public int getTarget() { return target; }
        public long getValue() { return value; }
    }

    public static class SankeyData {
        private List<SankeyNode> nodes;
        private List<SankeyLink> links;

        public SankeyData() {
            this.nodes = new ArrayList<>();
            this.links = new ArrayList<>();
        }

        public List<SankeyNode> getNodes() { return nodes; }
        public void setNodes(List<SankeyNode> nodes) { this.nodes = nodes; }
        public List<SankeyLink> getLinks() { return links; }
        public void setLinks(List<SankeyLink> links) { this.links = links; }
    }

    public static class TimelineResult {
        private List<TimelineDataPoint> data;
        private Map<String, Object> summary;
        private String interval;
        private String startDate;
        private String endDate;

        public TimelineResult() {
            this.data = new ArrayList<>();
            this.summary = new HashMap<>();
        }

        public List<TimelineDataPoint> getData() { return data; }
        public void setData(List<TimelineDataPoint> data) { this.data = data; }
        public Map<String, Object> getSummary() { return summary; }
        public void setSummary(Map<String, Object> summary) { this.summary = summary; }
        public String getInterval() { return interval; }
        public void setInterval(String interval) { this.interval = interval; }
        public String getStartDate() { return startDate; }
        public void setStartDate(String startDate) { this.startDate = startDate; }
        public String getEndDate() { return endDate; }
        public void setEndDate(String endDate) { this.endDate = endDate; }
    }

    public TimelineResult generateTimeline(
            Map<LocalDateTime, Long> rawData,
            String interval,
            boolean includeBreakdown,
            Map<LocalDateTime, Map<String, Long>> breakdownData) {

        TimelineResult result = new TimelineResult();
        result.setInterval(interval);

        if (rawData == null || rawData.isEmpty()) {
            return result;
        }

        List<Map.Entry<LocalDateTime, Long>> sorted = rawData.entrySet().stream()
                .sorted(Map.Entry.comparingByKey())
                .collect(Collectors.toList());

        LocalDateTime start = sorted.get(0).getKey();
        LocalDateTime end = sorted.get(sorted.size() - 1).getKey();
        result.setStartDate(start.toString());
        result.setEndDate(end.toString());

        List<TimelineDataPoint> dataPoints = generateTimelinePoints(
                start, end, interval, rawData, breakdownData, includeBreakdown);
        result.setData(dataPoints);

        long totalCount = rawData.values().stream().mapToLong(Long::longValue).sum();
        double avgCount = dataPoints.stream().mapToLong(TimelineDataPoint::getCount).average().orElse(0);
        long peakCount = dataPoints.stream().mapToLong(TimelineDataPoint::getCount).max().orElse(0);
        String peakTime = dataPoints.stream()
                .max(Comparator.comparingLong(TimelineDataPoint::getCount))
                .map(TimelineDataPoint::getTimestamp)
                .orElse(null);

        Map<String, Object> summary = new HashMap<>();
        summary.put("totalCount", totalCount);
        summary.put("averageCount", Math.round(avgCount * 100.0) / 100.0);
        summary.put("peakCount", peakCount);
        summary.put("peakTime", peakTime);
        summary.put("dataPoints", dataPoints.size());
        result.setSummary(summary);

        return result;
    }

    private List<TimelineDataPoint> generateTimelinePoints(
            LocalDateTime start, LocalDateTime end, String interval,
            Map<LocalDateTime, Long> rawData,
            Map<LocalDateTime, Map<String, Long>> breakdownData,
            boolean includeBreakdown) {

        List<TimelineDataPoint> points = new ArrayList<>();
        DateTimeFormatter formatter = DateTimeFormatter.ISO_LOCAL_DATE_TIME;

        ChronoUnit chronoUnit = parseInterval(interval);
        long stepCount = chronoUnit.between(start, end) + 1;

        for (int i = 0; i <= stepCount; i++) {
            LocalDateTime currentTime = start.plus(i, chronoUnit);
            LocalDateTime bucketStart = truncateToInterval(currentTime, chronoUnit);
            LocalDateTime bucketEnd = bucketStart.plus(1, chronoUnit);

            long count = rawData.entrySet().stream()
                    .filter(e -> !e.getKey().isBefore(bucketStart) && e.getKey().isBefore(bucketEnd))
                    .mapToLong(Map.Entry::getValue)
                    .sum();

            TimelineDataPoint point = new TimelineDataPoint(
                    bucketStart.format(formatter),
                    count
            );

            if (includeBreakdown && breakdownData != null) {
                Map<String, Long> bucketBreakdown = new HashMap<>();
                breakdownData.entrySet().stream()
                        .filter(e -> !e.getKey().isBefore(bucketStart) && e.getKey().isBefore(bucketEnd))
                        .forEach(e -> e.getValue().forEach((k, v) ->
                                bucketBreakdown.merge(k, v, Long::sum)));
                point.setBreakdown(bucketBreakdown);
            }

            points.add(point);
        }

        return points;
    }

    private ChronoUnit parseInterval(String interval) {
        switch (interval.toLowerCase()) {
            case "hourly":
            case "hour":
                return ChronoUnit.HOURS;
            case "daily":
            case "day":
                return ChronoUnit.DAYS;
            case "weekly":
            case "week":
                return ChronoUnit.WEEKS;
            case "monthly":
            case "month":
                return ChronoUnit.MONTHS;
            default:
                return ChronoUnit.HOURS;
        }
    }

    private LocalDateTime truncateToInterval(LocalDateTime time, ChronoUnit unit) {
        switch (unit) {
            case HOURS:
                return time.truncatedTo(ChronoUnit.HOURS);
            case DAYS:
                return time.truncatedTo(ChronoUnit.DAYS);
            case WEEKS:
                return time.with(DayOfWeek.MONDAY).truncatedTo(ChronoUnit.DAYS);
            case MONTHS:
                return time.withDayOfMonth(1).truncatedTo(ChronoUnit.DAYS);
            default:
                return time.truncatedTo(ChronoUnit.HOURS);
        }
    }

    public HeatmapData generateHourlyHeatmap(Map<LocalDateTime, Long> rawData) {
        HeatmapData result = new HeatmapData();

        List<String> xLabels = IntStream.range(0, 24)
                .mapToObj(h -> String.format("%02d:00", h))
                .collect(Collectors.toList());
        result.setXLabels(xLabels);

        List<String> yLabels = Arrays.asList("周一", "周二", "周三", "周四", "周五", "周六", "周日");
        result.setYLabels(yLabels);

        long[][] heatmapMatrix = new long[7][24];
        long maxValue = 0;
        long minValue = Long.MAX_VALUE;

        for (Map.Entry<LocalDateTime, Long> entry : rawData.entrySet()) {
            LocalDateTime time = entry.getKey();
            int dayOfWeek = time.getDayOfWeek().getValue() - 1;
            int hour = time.getHour();
            heatmapMatrix[dayOfWeek][hour] += entry.getValue();
        }

        for (int day = 0; day < 7; day++) {
            for (int hour = 0; hour < 24; hour++) {
                long value = heatmapMatrix[day][hour];
                result.getCells().add(new HeatmapCell(
                        hour,
                        day,
                        value,
                        String.valueOf(value)
                ));
                maxValue = Math.max(maxValue, value);
                minValue = Math.min(minValue, value);
            }
        }

        result.setMaxValue(maxValue);
        result.setMinValue(minValue == Long.MAX_VALUE ? 0 : minValue);

        return result;
    }

    public HeatmapData generateTopicHeatmap(
            List<String> topics,
            Map<String, Map<LocalDateTime, Long>> topicData) {

        HeatmapData result = new HeatmapData();

        List<String> xLabels = IntStream.range(0, 24)
                .mapToObj(h -> String.format("%02d:00", h))
                .collect(Collectors.toList());
        result.setXLabels(xLabels);
        result.setYLabels(topics);

        long maxValue = 0;
        long minValue = Long.MAX_VALUE;

        for (int topicIdx = 0; topicIdx < topics.size(); topicIdx++) {
            String topic = topics.get(topicIdx);
            Map<LocalDateTime, Long> data = topicData.getOrDefault(topic, Collections.emptyMap());

            long[] hourlyCounts = new long[24];
            for (Map.Entry<LocalDateTime, Long> entry : data.entrySet()) {
                int hour = entry.getKey().getHour();
                hourlyCounts[hour] += entry.getValue();
            }

            for (int hour = 0; hour < 24; hour++) {
                long value = hourlyCounts[hour];
                result.getCells().add(new HeatmapCell(
                        hour,
                        topicIdx,
                        value,
                        String.valueOf(value)
                ));
                maxValue = Math.max(maxValue, value);
                minValue = Math.min(minValue, value);
            }
        }

        result.setMaxValue(maxValue);
        result.setMinValue(minValue == Long.MAX_VALUE ? 0 : minValue);

        return result;
    }

    public SankeyData generateSankeyDiagram(
            Map<MqTypeEnum, Map<String, Long>> mqTopicCounts,
            Map<String, Map<DeadReasonTypeEnum, Long>> topicReasonCounts) {

        SankeyData result = new SankeyData();
        List<SankeyNode> nodes = new ArrayList<>();
        List<SankeyLink> links = new ArrayList<>();

        Map<String, Integer> nodeIndex = new HashMap<>();
        int nextIndex = 0;

        for (MqTypeEnum mqType : MqTypeEnum.values()) {
            if (mqTopicCounts.containsKey(mqType) && !mqTopicCounts.get(mqType).isEmpty()) {
                nodes.add(new SankeyNode(mqType.getDesc(), 0));
                nodeIndex.put(mqType.name(), nextIndex++);
            }
        }

        Set<String> allTopics = new HashSet<>();
        mqTopicCounts.values().forEach(map -> allTopics.addAll(map.keySet()));
        for (String topic : allTopics) {
            nodes.add(new SankeyNode(topic, 1));
            nodeIndex.put("topic_" + topic, nextIndex++);
        }

        for (DeadReasonTypeEnum reason : DeadReasonTypeEnum.values()) {
            nodes.add(new SankeyNode(reason.getDesc(), 2));
            nodeIndex.put("reason_" + reason.name(), nextIndex++);
        }

        for (Map.Entry<MqTypeEnum, Map<String, Long>> mqEntry : mqTopicCounts.entrySet()) {
            int mqIdx = nodeIndex.get(mqEntry.getKey().name());
            for (Map.Entry<String, Long> topicEntry : mqEntry.getValue().entrySet()) {
                int topicIdx = nodeIndex.get("topic_" + topicEntry.getKey());
                links.add(new SankeyLink(mqIdx, topicIdx, topicEntry.getValue()));
            }
        }

        for (Map.Entry<String, Map<DeadReasonTypeEnum, Long>> topicEntry : topicReasonCounts.entrySet()) {
            Integer topicIdx = nodeIndex.get("topic_" + topicEntry.getKey());
            if (topicIdx != null) {
                for (Map.Entry<DeadReasonTypeEnum, Long> reasonEntry : topicEntry.getValue().entrySet()) {
                    int reasonIdx = nodeIndex.get("reason_" + reasonEntry.getKey().name());
                    links.add(new SankeyLink(topicIdx, reasonIdx, reasonEntry.getValue()));
                }
            }
        }

        result.setNodes(nodes);
        result.setLinks(links);
        return result;
    }

    public Map<String, Object> generateVisualizationReport(
            TimelineResult timeline,
            HeatmapData heatmap,
            SankeyData sankey) {

        Map<String, Object> report = new HashMap<>();

        report.put("timeline", timeline);
        report.put("heatmap", heatmap);
        report.put("sankey", sankey);

        Map<String, Object> insights = new HashMap<>();

        if (timeline.getSummary() != null) {
            insights.put("totalCount", timeline.getSummary().get("totalCount"));
            insights.put("peakCount", timeline.getSummary().get("peakCount"));
            insights.put("peakTime", timeline.getSummary().get("peakTime"));

            String trend = analyzeTrend(timeline.getData());
            insights.put("trend", trend);
        }

        List<Integer> peakHours = findPeakHours(heatmap);
        insights.put("peakHours", peakHours);

        List<Integer> peakDays = findPeakDays(heatmap);
        insights.put("peakDays", peakDays);

        report.put("insights", insights);

        return report;
    }

    private String analyzeTrend(List<TimelineDataPoint> data) {
        if (data.size() < 2) return "UNKNOWN";

        int half = data.size() / 2;
        double firstHalfAvg = data.subList(0, half).stream()
                .mapToLong(TimelineDataPoint::getCount)
                .average().orElse(0);
        double secondHalfAvg = data.subList(half, data.size()).stream()
                .mapToLong(TimelineDataPoint::getCount)
                .average().orElse(0);

        double change = (secondHalfAvg - firstHalfAvg) / firstHalfAvg * 100;
        if (change > 20) return "SHARP_INCREASE";
        if (change > 5) return "INCREASING";
        if (change < -20) return "SHARP_DECREASE";
        if (change < -5) return "DECREASING";
        return "STABLE";
    }

    private List<Integer> findPeakHours(HeatmapData heatmap) {
        long[] hourlySums = new long[24];
        for (HeatmapCell cell : heatmap.getCells()) {
            hourlySums[cell.getX()] += cell.getValue();
        }

        double threshold = Arrays.stream(hourlySums).average().orElse(0) * 1.5;
        return IntStream.range(0, 24)
                .filter(h -> hourlySums[h] > threshold)
                .boxed()
                .collect(Collectors.toList());
    }

    private List<Integer> findPeakDays(HeatmapData heatmap) {
        long[] dailySums = new long[7];
        for (HeatmapCell cell : heatmap.getCells()) {
            dailySums[cell.getY()] += cell.getValue();
        }

        double threshold = Arrays.stream(dailySums).average().orElse(0) * 1.3;
        return IntStream.range(0, 7)
                .filter(d -> dailySums[d] > threshold)
                .boxed()
                .collect(Collectors.toList());
    }

    public Map<String, Object> getVisualizationOptions() {
        Map<String, Object> options = new HashMap<>();

        Map<String, Object> timeline = new HashMap<>();
        timeline.put("intervals", Arrays.asList("hourly", "daily", "weekly", "monthly"));
        timeline.put("defaultInterval", "hourly");
        options.put("timeline", timeline);

        Map<String, Object> heatmap = new HashMap<>();
        heatmap.put("types", Arrays.asList("hourly_week", "topic_hourly"));
        heatmap.put("colorScheme", "YlOrRd");
        options.put("heatmap", heatmap);

        Map<String, Object> sankey = new HashMap<>();
        sankey.put("categories", Arrays.asList("MQ类型", "主题/队列", "死信原因"));
        options.put("sankey", sankey);

        return options;
    }
}
