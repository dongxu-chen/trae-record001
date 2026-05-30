package analyzer

import (
	"fmt"
	"sort"
	"time"
)

func (a *lagAnalyzer) generateRecommendations(analysis *ConsumerGroupAnalysis) []Recommendation {
	var recs []Recommendation

	for _, attr := range analysis.DelayAttributions {
		switch attr.Cause {
		case CauseSlowProcessing:
			recs = append(recs, a.generateSlowProcessingRecs(attr, analysis)...)
		case CauseNetworkLatency:
			recs = append(recs, a.generateNetworkLatencyRecs(attr, analysis)...)
		case CauseImbalance:
			recs = append(recs, a.generateImbalanceRecs(attr, analysis)...)
		case CauseRebalancing:
			recs = append(recs, a.generateRebalancingRecs(attr, analysis)...)
		case CauseHighThroughput:
			recs = append(recs, a.generateHighThroughputRecs(attr, analysis)...)
		}
	}

	if pred, err := a.PredictProgress(analysis.GroupID); err == nil {
		recs = append(recs, a.generatePredictionRecs(pred, analysis)...)
	}

	if analysis.MemberCount > 0 && analysis.TotalLag > a.cfg.LagThreshold {
		if sim, err := a.SimulateConsumerAddition(analysis.GroupID, 1); err == nil {
			recs = append(recs, a.generateSimulationRecs(sim, analysis)...)
		}
	}

	if len(analysis.HotPartitions) > 0 {
		if plan, err := a.GenerateRebalancePlan(analysis.GroupID); err == nil {
			recs = append(recs, a.generateRebalancePlanRecs(plan, analysis)...)
		}
	}

	recs = append(recs, a.generateCodeOptimizationRecs(analysis)...)

	if analysis.OverallStatus != StatusNormal {
		recs = append(recs, a.generateGeneralRecs(analysis)...)
	}

	sort.Slice(recs, func(i, j int) bool {
		priorityOrder := map[string]int{"critical": 0, "high": 1, "medium": 2, "low": 3}
		return priorityOrder[recs[i].Priority] < priorityOrder[recs[j].Priority]
	})

	return recs
}

func (a *lagAnalyzer) generateSlowProcessingRecs(attr DelayAttribution, analysis *ConsumerGroupAnalysis) []Recommendation {
	var recs []Recommendation

	severity := "high"
	if attr.Severity == StatusCritical {
		severity = "critical"
	}

	recs = append(recs, Recommendation{
		Priority:    severity,
		Category:    "Performance",
		Title:       "优化消费端处理逻辑",
		Description: fmt.Sprintf("检测到慢处理问题，影响 %d 个分区。消费者处理消息的速度低于 %.2f msgs/sec", len(attr.AffectedPartitions), a.cfg.SlowProcessingThreshold),
		Action:      "检查消费者处理逻辑，考虑异步处理、批量处理或优化数据库/IO操作。分析消费者代码中的性能瓶颈。",
		Impact:      "降低处理延迟，提高消费吞吐量",
	})

	recs = append(recs, Recommendation{
		Priority:    "medium",
		Category:    "Scaling",
		Title:       "增加消费者实例数量",
		Description: fmt.Sprintf("消费组当前有 %d 个成员，考虑水平扩展以分摊负载", analysis.MemberCount),
		Action:      "增加消费者实例数量，确保不超过主题的分区总数。检查分区分配策略是否合理。",
		Impact:      "提高并行处理能力，减少单个消费者的负载",
	})

	if len(attr.AffectedTopics) > 0 {
		recs = append(recs, Recommendation{
			Priority:    "medium",
			Category:    "Configuration",
			Title:       "调整消费者配置参数",
			Description: fmt.Sprintf("主题 %v 的消费速度不足", attr.AffectedTopics),
			Action:      "考虑增大 fetch.min.bytes 和 fetch.max.wait.ms 以减少网络往返。检查 max.poll.records 是否合理。",
			Impact:      "优化批量获取，减少网络开销",
		})
	}

	return recs
}

func (a *lagAnalyzer) generateNetworkLatencyRecs(attr DelayAttribution, analysis *ConsumerGroupAnalysis) []Recommendation {
	var recs []Recommendation

	severity := "high"
	if attr.Severity == StatusCritical {
		severity = "critical"
	}

	avgRTT := 0.0
	maxRTT := 0.0
	jitter := 0.0
	if attr.Metrics != nil {
		avgRTT = attr.Metrics["avg_rtt_ms"]
		maxRTT = attr.Metrics["max_rtt_ms"]
		jitter = attr.Metrics["jitter_ms"]
	}

	recs = append(recs, Recommendation{
		Priority:    severity,
		Category:    "Network",
		Title:       "网络延迟过高（基于主动RTT探测）",
		Description: fmt.Sprintf("主动RTT探测发现网络延迟异常，平均RTT=%.1fms，最大RTT=%.1fms，抖动=%.1fms，影响 %d 个分区", avgRTT, maxRTT, jitter, len(attr.AffectedPartitions)),
		Action:      fmt.Sprintf("检查消费者与Kafka集群之间的网络连接。平均RTT=%.1fms已超过正常范围(50ms)，使用 mtr/traceroute 诊断网络路径上的延迟节点。检查DNS解析、防火墙、负载均衡器等中间环节。", avgRTT),
		Impact:      "降低网络延迟，提升消费速率",
		CodeExample: `# 诊断命令
mtr -rwzbc 100 <kafka-broker-host>
traceroute -T -p 9092 <kafka-broker-host>
# 检查DNS解析时间
dig <kafka-broker-host> | grep "Query time"`,
	})

	if analysis.NetworkRTTSummary != nil {
		for id, brtt := range analysis.NetworkRTTSummary.BrokerRTTs {
			if brtt.RTT > time.Duration(a.kafkaCfg.RTTWarningThreshold)*time.Millisecond {
				recs = append(recs, Recommendation{
					Priority:    "high",
					Category:    "Network",
					Title:       fmt.Sprintf("Broker %d (%s) 网络延迟异常", id, brtt.Host),
					Description: fmt.Sprintf("Broker RTT=%.1fms, Min=%.1fms, Max=%.1fms, Jitter=%.1fms", float64(brtt.RTT.Microseconds())/1000, float64(brtt.MinRTT.Microseconds())/1000, float64(brtt.MaxRTT.Microseconds())/1000, float64(brtt.Jitter.Microseconds())/1000),
					Action:      fmt.Sprintf("重点排查到 Broker %d (%s) 的网络链路，高抖动(%.1fms)可能由网络拥塞或不稳定路由导致", id, brtt.Host, float64(brtt.Jitter.Microseconds())/1000),
					Impact:      "针对性修复网络瓶颈",
				})
			}
		}
	}

	recs = append(recs, Recommendation{
		Priority:    "medium",
		Category:    "Configuration",
		Title:       "调整网络超时配置",
		Description: fmt.Sprintf("当前RTT=%.1fms，网络不稳定可能导致频繁超时和重试", avgRTT),
		Action: fmt.Sprintf(`根据实际RTT调整配置:
  request.timeout.ms = %d (建议 >= 3x RTT)
  session.timeout.ms = %d (建议 >= 10x RTT)  
  heartbeat.interval.ms = %d (建议 = session.timeout.ms / 3)
  connections.max.idle.ms = 540000`, int(avgRTT*3), int(avgRTT*10), int(avgRTT*10/3)),
		Impact:      "减少因网络波动导致的再平衡",
	})

	recs = append(recs, Recommendation{
		Priority:    "low",
		Category:    "Infrastructure",
		Title:       "考虑就近部署",
		Description: "如果消费者与Kafka集群跨可用区或跨地域，网络延迟会较高",
		Action:      "尽量将消费者部署在与Kafka集群相同的可用区或地域。考虑使用就近的broker节点，配置 broker.rack 实现机架感知。",
		Impact:      "从架构上降低网络延迟",
	})

	return recs
}

func (a *lagAnalyzer) generateImbalanceRecs(attr DelayAttribution, analysis *ConsumerGroupAnalysis) []Recommendation {
	var recs []Recommendation

	severity := "high"
	if attr.Severity == StatusCritical {
		severity = "critical"
	}

	recs = append(recs, Recommendation{
		Priority:    severity,
		Category:    "Partitioning",
		Title:       "检查消息分区键策略（含消息大小权重分析）",
		Description: fmt.Sprintf("检测到分区不均衡问题(含消息大小权重)，影响主题: %v。大消息分区权重更高，加权lag分布不均", attr.AffectedTopics),
		Action:      "检查生产者的分区键选择。如果使用自定义分区器，确保消息能够均匀分布到所有分区。大消息分区需要特别关注，即使lag较小，实际处理负担可能更重。考虑使用随机分区或轮询策略。",
		Impact:      "均衡各分区的消息负载，考虑消息大小差异",
	})

	for _, topic := range attr.AffectedTopics {
		if topicLag, ok := analysis.Topics[topic]; ok {
			maxSize := 0.0
			minSize := float64(1<<63 - 1)
			for _, p := range topicLag.Partitions {
				if p.AvgMessageSize > maxSize {
					maxSize = p.AvgMessageSize
				}
				if p.AvgMessageSize > 0 && p.AvgMessageSize < minSize {
					minSize = p.AvgMessageSize
				}
			}
			if maxSize > 0 && minSize < float64(1<<63-1) && maxSize/minSize > 2 {
				recs = append(recs, Recommendation{
					Priority:    severity,
					Category:    "Partitioning",
					Title:       fmt.Sprintf("主题 %s 消息大小差异极大", topic),
					Description: fmt.Sprintf("最大平均消息大小=%.0f bytes，最小=%.0f bytes，比值=%.1f。大消息分区即使lag相同，处理时间也远高于小消息分区", maxSize, minSize, maxSize/minSize),
					Action:      "对大消息进行压缩或拆分。在生产者端使用压缩(snappy/lz4/zstd)减少消息体积。对于超大消息，考虑使用消息引用模式：将payload存入外部存储(如S3)，Kafka只传递引用。",
					Impact:      "减小消息大小差异，均衡分区负载",
					CodeExample: `// 生产者压缩配置
props.put("compression.type", "zstd");
// 大消息拆分为引用模式
byte[] payload = largeMessage.getBytes();
if (payload.length > 1_000_000) {
    String s3Key = uploadToS3(payload);
    producer.send(new ProducerRecord(topic, key, s3Key.getBytes()));
} else {
    producer.send(new ProducerRecord(topic, key, payload));
}`,
				})
			}
		}
	}

	recs = append(recs, Recommendation{
		Priority:    "medium",
		Category:    "Rebalance",
		Title:       "检查消费者分区分配策略",
		Description: "分区分配不合理可能导致某些消费者负载过高，尤其大消息分区集中时",
		Action:      "考虑使用 StickyAssignor 保持分配稳定性，或自定义分配器考虑分区数据量。检查消费者实例的处理能力是否均衡。",
		Impact:      "均衡消费者之间的分区分配",
	})

	if analysis.MemberCount > 0 {
		recs = append(recs, Recommendation{
			Priority:    "medium",
			Category:    "Scaling",
			Title:       "调整消费者数量与分区数的比例",
			Description: fmt.Sprintf("当前有 %d 个消费者成员，检查是否与分区数匹配", analysis.MemberCount),
			Action:      "确保消费者数量不超过分区数量。如果分区数远大于消费者数，考虑增加消费者以提高并行度。",
			Impact:      "最大化并行消费能力",
		})
	}

	return recs
}

func (a *lagAnalyzer) generateRebalancingRecs(attr DelayAttribution, analysis *ConsumerGroupAnalysis) []Recommendation {
	var recs []Recommendation

	recs = append(recs, Recommendation{
		Priority:    "high",
		Category:    "Rebalance",
		Title:       "调查频繁再平衡的原因",
		Description: fmt.Sprintf("消费组当前状态为 %s，正在进行再平衡", analysis.State),
		Action:      "检查是否有消费者实例频繁加入或离开。检查 session.timeout.ms 和 heartbeat.interval.ms 配置。检查 max.poll.interval.ms 是否足够处理消息。",
		Impact:      "减少不必要的再平衡，提高消费稳定性",
	})

	recs = append(recs, Recommendation{
		Priority:    "medium",
		Category:    "Configuration",
		Title:       "优化再平衡相关配置",
		Description: "合理的配置可以减少再平衡的频率和影响",
		Action:      "适当调大 session.timeout.ms 以避免不必要的再平衡。考虑使用静态成员资格 (group.instance.id) 以减少再平衡时的分区重分配。",
		Impact:      "提高消费组稳定性",
		CodeExample: `// 静态成员资格配置
props.put("group.instance.id", "consumer-hostname-1");
props.put("session.timeout.ms", "30000");
props.put("heartbeat.interval.ms", "10000");
props.put("max.poll.interval.ms", "600000");`,
	})

	return recs
}

func (a *lagAnalyzer) generateHighThroughputRecs(attr DelayAttribution, analysis *ConsumerGroupAnalysis) []Recommendation {
	var recs []Recommendation

	severity := "high"
	if attr.Severity == StatusCritical {
		severity = "critical"
	}

	recs = append(recs, Recommendation{
		Priority:    severity,
		Category:    "Scaling",
		Title:       "扩展消费能力",
		Description: fmt.Sprintf("检测到高吞吐量压力，影响主题: %v。消息流入速度超过消费能力", attr.AffectedTopics),
		Action:      "增加消费者实例数量以提高并行消费能力。如果已达到分区数限制，考虑增加主题的分区数量。",
		Impact:      "提高整体消费吞吐量",
	})

	recs = append(recs, Recommendation{
		Priority:    "high",
		Category:    "Performance",
		Title:       "优化批量处理",
		Description: "高吞吐量场景下，批量处理可以显著提高性能",
		Action:      "增大 max.poll.records 以每次获取更多消息。检查是否启用了批量处理逻辑。考虑使用压缩减少数据传输量。",
		Impact:      "提高消费效率，减少网络开销",
		CodeExample: `// 批量处理优化
props.put("max.poll.records", "500");
props.put("fetch.min.bytes", "1048576"); // 1MB
props.put("fetch.max.wait.ms", "500");

// 批量消费逻辑
while (true) {
    ConsumerRecords<K, V> records = consumer.poll(Duration.ofMillis(1000));
    if (!records.isEmpty()) {
        List<Record> batch = new ArrayList<>();
        for (ConsumerRecord<K, V> record : records) {
            batch.add(transform(record));
        }
        batchInsert(batch);  // 批量写入而非逐条
        consumer.commitSync();
    }
}`,
	})

	recs = append(recs, Recommendation{
		Priority:    "medium",
		Category:    "Architecture",
		Title:       "考虑限流或削峰填谷",
		Description: "如果高峰时段流量过大，可以考虑限流或使用缓冲",
		Action:      "在生产者端实施限流策略。考虑在Kafka前增加一层缓冲队列。评估是否可以错峰处理非实时消息。",
		Impact:      "平滑流量，避免系统过载",
	})

	return recs
}

func (a *lagAnalyzer) generateCodeOptimizationRecs(analysis *ConsumerGroupAnalysis) []Recommendation {
	var recs []Recommendation

	patterns := a.detectCodePatterns(analysis)

	for _, pattern := range patterns {
		recs = append(recs, a.patternToRecommendation(pattern, analysis)...)
	}

	return recs
}

func (a *lagAnalyzer) detectCodePatterns(analysis *ConsumerGroupAnalysis) []CodePattern {
	var patterns []CodePattern

	slowProcessingDetected := false
	for _, attr := range analysis.DelayAttributions {
		if attr.Cause == CauseSlowProcessing {
			slowProcessingDetected = true
			break
		}
	}

	if slowProcessingDetected {
		patterns = append(patterns, CodePattern{
			Name:        "sync_db_in_loop",
			Description: "消费循环中可能存在同步数据库操作",
			Severity:    StatusCritical,
			Suggestions: []string{
				"在消费循环中逐条执行 INSERT/UPDATE 会导致大量数据库往返",
				"应使用批量写入（batch insert）替代逐条写入",
				"考虑使用写缓冲区，累积N条后一次性提交",
			},
		})

		patterns = append(patterns, CodePattern{
			Name:        "no_batch_processing",
			Description: "可能缺少批量处理逻辑，逐条处理效率低",
			Severity:    StatusWarning,
			Suggestions: []string{
				"检查是否每次 poll 后逐条处理消息",
				"应累积消息后批量处理（如批量DB写入、批量API调用）",
				"设置合理的 max.poll.records 提高单次获取量",
			},
		})

		patterns = append(patterns, CodePattern{
			Name:        "external_api_sync",
			Description: "消费逻辑可能包含同步外部API调用",
			Severity:    StatusWarning,
			Suggestions: []string{
				"同步HTTP/RPC调用会阻塞消费线程",
				"应使用异步调用或连接池",
				"考虑设置合理的超时和重试策略",
				"引入断路器模式防止级联故障",
			},
		})

		patterns = append(patterns, CodePattern{
			Name:        "blocking_deserialization",
			Description: "消息反序列化可能存在性能瓶颈",
			Severity:    StatusWarning,
			Suggestions: []string{
				"大消息的JSON/XML反序列化开销大",
				"考虑使用Protobuf/Avro等高效序列化格式",
				"反序列化与处理逻辑解耦，使用goroutine并行处理",
			},
		})
	}

	for _, topicLag := range analysis.Topics {
		if topicLag.AvgMessageSize > 100*1024 {
			patterns = append(patterns, CodePattern{
				Name:        "large_message_handling",
				Description: fmt.Sprintf("主题 %s 平均消息大小=%.1fKB，大消息处理需特殊优化", topicLag.Topic, topicLag.AvgMessageSize/1024),
				Severity:    StatusWarning,
				Suggestions: []string{
					"大消息反序列化和处理耗时高",
					"考虑使用零拷贝技术减少内存分配",
					"使用消息引用模式，Kafka只传元数据，payload存外部存储",
					"生产者端启用压缩(snappy/zstd)可减少50-80%数据量",
				},
			})
			break
		}
	}

	if analysis.NetworkRTTSummary != nil && analysis.NetworkRTTSummary.HighRTTCount > 0 {
		patterns = append(patterns, CodePattern{
			Name:        "no_connection_pooling",
			Description: "高RTT环境下可能未使用连接池或连接复用",
			Severity:    StatusWarning,
			Suggestions: []string{
				"每次建立新TCP连接会增加RTT开销",
				"确保Kafka客户端复用broker连接",
				"检查 connections.max.idle.ms 避免频繁断连重连",
				"对于外部调用，使用连接池而非短连接",
			},
		})
	}

	commitPattern := a.detectCommitPattern(analysis)
	if commitPattern != nil {
		patterns = append(patterns, *commitPattern)
	}

	return patterns
}

func (a *lagAnalyzer) detectCommitPattern(analysis *ConsumerGroupAnalysis) *CodePattern {
	hasSlowProcessing := false
	for _, attr := range analysis.DelayAttributions {
		if attr.Cause == CauseSlowProcessing {
			hasSlowProcessing = true
		}
	}

	if !hasSlowProcessing {
		return nil
	}

	return &CodePattern{
		Name:        "auto_commit_misuse",
		Description: "可能存在自动提交配置不当导致重复消费或消息丢失",
		Severity:    StatusWarning,
		Suggestions: []string{
			"enable.auto.commit=true 可能在处理完成前就提交offset",
			"处理失败时offset已提交会导致消息丢失",
			"建议使用手动提交: enable.auto.commit=false",
			"处理完成后调用 commitSync() 或 commitAsync()",
			"注意 max.poll.interval.ms 必须大于最长处理时间",
		},
	}
}

func (a *lagAnalyzer) patternToRecommendation(pattern CodePattern, analysis *ConsumerGroupAnalysis) []Recommendation {
	var recs []Recommendation

	priority := "medium"
	if pattern.Severity == StatusCritical {
		priority = "high"
	} else if pattern.Severity == StatusWarning {
		priority = "medium"
	}

	switch pattern.Name {
	case "sync_db_in_loop":
		recs = append(recs, Recommendation{
			Priority:    priority,
			Category:    "CodeOptimization",
			Title:       "【代码优化】消除消费循环中的同步数据库操作",
			Description: pattern.Description,
			Action:      "将逐条数据库写入改为批量写入。使用缓冲区累积消息后一次性提交，可提升10-50倍吞吐量。",
			Impact:      "大幅提升消费吞吐量，减少数据库压力",
			CodeExample: `// 优化前：逐条写入（慢）
for (ConsumerRecord<K, V> record : records) {
    db.insert(transform(record));  // 每条一次网络往返
}

// 优化后：批量写入（快）
List<Record> batch = new ArrayList<>(records.count());
for (ConsumerRecord<K, V> record : records) {
    batch.add(transform(record));
}
db.batchInsert(batch);  // 一次网络往返写入全部

// Go版本优化
var batch []Record
for _, msg := range messages {
    batch = append(batch, transform(msg))
}
db.BatchInsert(batch)`,
		})

	case "no_batch_processing":
		recs = append(recs, Recommendation{
			Priority:    priority,
			Category:    "CodeOptimization",
			Title:       "【代码优化】引入批量处理模式",
			Description: pattern.Description,
			Action:      "实现消息批量处理，减少单条处理的开销。设置合理的批量大小和超时。",
			Impact:      "提高消费效率，降低CPU和网络开销",
			CodeExample: `// 批量处理模式
type BatchProcessor struct {
    buffer    []Record
    batchSize int
    timeout   time.Duration
}

func (bp *BatchProcessor) Add(record Record) {
    bp.buffer = append(bp.buffer, record)
    if len(bp.buffer) >= bp.batchSize {
        bp.Flush()
    }
}

func (bp *BatchProcessor) Flush() {
    if len(bp.buffer) > 0 {
        db.BatchInsert(bp.buffer)
        bp.buffer = bp.buffer[:0]
    }
}`,
		})

	case "external_api_sync":
		recs = append(recs, Recommendation{
			Priority:    priority,
			Category:    "CodeOptimization",
			Title:       "【代码优化】异步化外部API调用",
			Description: pattern.Description,
			Action:      "将同步HTTP/RPC调用改为异步或使用连接池。引入断路器防止故障扩散。",
			Impact:      "消除阻塞点，提高消费并发度",
			CodeExample: `// 优化前：同步调用
response, err := http.Post(apiURL, body)  // 阻塞等待

// 优化后：异步+连接池+断路器
var client = &http.Client{
    Transport: &http.Transport{
        MaxIdleConnsPerHost: 100,
        IdleConnTimeout:     90 * time.Second,
    },
    Timeout: 5 * time.Second,
}

// 使用errgroup并发调用
g, ctx := errgroup.WithContext(ctx)
g.SetLimit(50)  // 限制并发数
for _, msg := range messages {
    msg := msg
    g.Go(func() error {
        return callAPI(ctx, client, msg)
    })
}
if err := g.Wait(); err != nil {
    return err
}`,
		})

	case "blocking_deserialization":
		recs = append(recs, Recommendation{
			Priority:    priority,
			Category:    "CodeOptimization",
			Title:       "【代码优化】优化消息反序列化性能",
			Description: pattern.Description,
			Action:      "从JSON/XML切换到Protobuf/Avro等高效格式，或将反序列化与处理并行化。",
			Impact:      "降低CPU开销，提高反序列化速度2-10倍",
			CodeExample: `// 优化前：JSON反序列化（慢）
err := json.Unmarshal(data, &msg)

// 优化后：Protobuf反序列化（快）
err := proto.Unmarshal(data, &msg)

// 性能对比：
// JSON:    ~1000 ops/ms, 分配大量内存
// Protobuf: ~10000 ops/ms, 零拷贝设计

// 并行反序列化
var wg sync.WaitGroup
sem := make(chan struct{}, runtime.NumCPU())
results := make([]Message, len(messages))
for i, raw := range messages {
    wg.Add(1)
    sem <- struct{}{}
    go func(idx int, data []byte) {
        defer wg.Done()
        proto.Unmarshal(data, &results[idx])
        <-sem
    }(i, raw)
}
wg.Wait()`,
		})

	case "large_message_handling":
		recs = append(recs, Recommendation{
			Priority:    priority,
			Category:    "CodeOptimization",
			Title:       "【代码优化】大消息处理优化",
			Description: pattern.Description,
			Action:      "使用消息引用模式、零拷贝技术、压缩等手段优化大消息处理。",
			Impact:      "减少网络传输和内存开销，提升大消息处理速度",
			CodeExample: `// 方案1：消息引用模式
// 生产者：大payload存S3，Kafka只发引用
func produceLargeMessage(topic string, payload []byte) {
    if len(payload) > 100_000 {
        s3Key := uploadToS3(payload)
        ref := &MessageRef{S3Key: s3Key, Size: len(payload)}
        kafka.Produce(topic, ref)
    } else {
        kafka.Produce(topic, payload)
    }
}

// 方案2：生产者端压缩
// compression.type=zstd (压缩比好)
// compression.type=snappy (压缩速度快)
// 可减少50-80%数据量

// 方案3：Go零拷贝处理
func processMessage(r io.Reader) error {
    // 使用io.TeeReader避免数据拷贝
    // 使用sync.Pool复用buffer
    buf := bufPool.Get().(*bytes.Buffer)
    defer bufPool.Put(buf)
    buf.Reset()
    _, err := io.Copy(buf, r)
    return err
}`,
		})

	case "no_connection_pooling":
		recs = append(recs, Recommendation{
			Priority:    priority,
			Category:    "CodeOptimization",
			Title:       "【代码优化】确保连接池和连接复用",
			Description: pattern.Description,
			Action:      "检查Kafka客户端和外部调用是否使用连接池。避免频繁创建和销毁连接。",
			Impact:      "减少RTT开销，提升连接稳定性",
			CodeExample: `// Kafka客户端连接复用（sarama）
// 全局共享Client实例，不要每次创建新的
var globalClient sarama.Client
var globalProducer sarama.SyncProducer

func InitKafka(brokers []string) error {
    config := sarama.NewConfig()
    config.Net.MaxOpenRequests = 100       // 连接上最大并发请求数
    config.Net.DialTimeout = 30 * time.Second
    
    client, err := sarama.NewClient(brokers, config)
    globalClient = client  // 复用
    
    producer, err := sarama.NewSyncProducerFromClient(client)
    globalProducer = producer  // 复用
    return err
}

// HTTP连接池
var httpClient = &http.Client{
    Transport: &http.Transport{
        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 100,
        IdleConnTimeout:     90 * time.Second,
        DisableKeepAlives:   false,  // 启用Keep-Alive
    },
    Timeout: 10 * time.Second,
}`,
		})

	case "auto_commit_misuse":
		recs = append(recs, Recommendation{
			Priority:    priority,
			Category:    "CodeOptimization",
			Title:       "【代码优化】优化Offset提交策略",
			Description: pattern.Description,
			Action:      "切换为手动提交offset，确保消息处理完成后再提交。避免消息丢失和重复消费。",
			Impact:      "确保at-least-once语义，避免消息丢失",
			CodeExample: `// 优化前：自动提交（可能丢消息）
// enable.auto.commit=true (默认)

// 优化后：手动提交
// enable.auto.commit=false
func consumeLoop(consumer *kafka.Consumer) {
    for {
        messages := consumer.Poll(1000)
        for _, msg := range messages {
            err := processMessage(msg)
            if err != nil {
                log.Printf("处理失败,offset=%d: %v", msg.Offset, err)
                continue  // 跳过或发往死信队列
            }
        }
        // 处理完成后手动提交
        if err := consumer.CommitSync(); err != nil {
            log.Printf("提交失败: %v", err)
        }
    }
}

// 进阶：按分区粒度提交offset
func commitPerPartition(consumer *kafka.Consumer, topic string) {
    for partition, offset := range processedOffsets {
        consumer.CommitOffset(topic, partition, offset+1)
    }
}`,
		})
	}

	return recs
}

func (a *lagAnalyzer) generatePredictionRecs(prediction *GroupProgressPrediction, analysis *ConsumerGroupAnalysis) []Recommendation {
	var recs []Recommendation

	if prediction == nil {
		return recs
	}

	maxDuration := prediction.OverallEstimatedTimeToClear
	hasCritical := len(prediction.CriticalPartitions) > 0
	confidence := prediction.Confidence

	if maxDuration > 4*time.Hour && analysis.OverallStatus != StatusNormal {
		severity := "high"
		if maxDuration > 24*time.Hour {
			severity = "critical"
		}

		estimatedTime := formatDuration(maxDuration)
		recs = append(recs, Recommendation{
			Priority:    severity,
			Category:    "Prediction",
			Title:       "消费积压预估时长过长",
			Description: fmt.Sprintf("基于当前消费速率，预估需要 %s 才能消费完所有积压(置信度=%.0f%%)。%d 个分区预计清退时间超过1小时。", estimatedTime, confidence*100, hasCritical),
			Action:      "立即采取措施降低lag：1) 增加消费者实例 2) 优化消费逻辑 3) 考虑限流生产者。调用 /api/predict/{group} 查看详细预测数据。",
			Impact:      "避免lag持续增长导致数据丢失或业务延迟",
		})
	}

	if !prediction.WillCatchUp && prediction.NetRate < 0 && analysis.OverallStatus != StatusNormal {
		recs = append(recs, Recommendation{
			Priority:    "critical",
			Category:    "Prediction",
			Title:       "告警：消费速率低于生产速率，lag将持续增长",
			Description: fmt.Sprintf("当前净消费速率=%.2f msgs/sec(负表示lag增长)。总消费速率=%.2f，总生产速率=%.2f", prediction.NetRate, prediction.AggregateConsumptionRate, prediction.AggregateIngestionRate),
			Action:      "必须立即扩容或降低生产速率。否则lag将无限增长，最终导致消息丢失。建议立即增加至少2个消费者实例。",
			Impact:      "防止lag失控增长，避免数据丢失",
		})
	}

	if confidence < 0.5 && analysis.TotalLag > a.cfg.LagThreshold {
		recs = append(recs, Recommendation{
			Priority:    "low",
			Category:    "Prediction",
			Title:       "预测置信度较低，需更多历史数据",
			Description: fmt.Sprintf("当前预测置信度=%.0f%%，建议等待至少 %d 个数据点后再做决策", confidence*100, 10),
			Action:      "继续监控，积累更多历史数据。检查分析周期是否足够长。",
			Impact:      "提高预测准确性",
		})
	}

	return recs
}

func (a *lagAnalyzer) generateSimulationRecs(simulation *ConsumerSimulation, analysis *ConsumerGroupAnalysis) []Recommendation {
	var recs []Recommendation

	if simulation == nil {
		return recs
	}

	improvement := simulation.ImprovementPercent
	timeSaved := simulation.EstimatedTimeSaved

	if improvement > 20 {
		priority := "medium"
		if improvement > 50 {
			priority = "high"
		}

		recs = append(recs, Recommendation{
			Priority:    priority,
			Category:    "Simulation",
			Title:       fmt.Sprintf("建议增加消费者实例（模拟显示可降低%.1f%%的lag）", improvement),
			Description: fmt.Sprintf("模拟增加 %d 个消费者(从 %d 到 %d)，预计总lag可从 %d 降至 %.0f，改善%.1f%%。预计节省 %s 清退时间。",
				simulation.SimulatedMemberCount-simulation.OriginalMemberCount,
				simulation.OriginalMemberCount,
				simulation.SimulatedMemberCount,
				simulation.OriginalTotalLag,
				simulation.SimulatedTotalLag,
				improvement,
				formatDuration(timeSaved),
			),
			Action:      fmt.Sprintf("建议逐步增加消费者实例，先增加1个观察效果。调用 /api/simulate/{group}?add=N 模拟增加N个消费者的效果。注意: 消费者数不应超过分区总数。"),
			Impact:      fmt.Sprintf("预计lag降低%.1f%%，清退时间提前 %s", improvement, formatDuration(timeSaved)),
			CodeExample: `# 模拟增加2个消费者的效果
curl http://localhost:8080/api/simulate/my-group?add=2

# Kubernetes扩缩容
kubectl scale deployment my-consumer --replicas=4`,
		})
	}

	for topic, topicSim := range simulation.TopicSimulations {
		if topicSim.ImprovementPercent > 30 {
			recs = append(recs, Recommendation{
				Priority:    "high",
				Category:    "Simulation",
				Title:       fmt.Sprintf("主题 %s 扩容收益显著(+%.1f%%)", topic, topicSim.ImprovementPercent),
				Description: fmt.Sprintf("主题 %s 扩容后预计清退时间从 %s 缩短至 %s，节省 %s",
					topic,
					formatDuration(topicSim.OriginalTimeToClear),
					formatDuration(topicSim.EstimatedTimeToClear),
					formatDuration(topicSim.OriginalTimeToClear-topicSim.EstimatedTimeToClear),
				),
				Action:      "优先为该主题分配更多消费者资源。考虑单独为该主题创建专用消费组。",
				Impact:      "针对性优化，最大化扩容ROI",
			})
		}
	}

	actualPartitions := 0
	for _, tl := range analysis.Topics {
		actualPartitions += tl.PartitionCount
	}
	if simulation.SimulatedMemberCount > actualPartitions {
		recs = append(recs, Recommendation{
			Priority:    "medium",
			Category:    "Simulation",
			Title:       "消费者数将超过分区总数，部分消费者将空闲",
			Description: fmt.Sprintf("当前总分区数=%d，模拟消费者数=%d。超过分区数的消费者将无法分配到分区，造成资源浪费。", actualPartitions, simulation.SimulatedMemberCount),
			Action:      "建议先增加主题的分区数，再增加消费者。或者将多余的消费者分配给其他消费组。",
			Impact:      "避免资源浪费，提高投入产出比",
		})
	}

	return recs
}

func (a *lagAnalyzer) generateRebalancePlanRecs(plan *RebalancePlan, analysis *ConsumerGroupAnalysis) []Recommendation {
	var recs []Recommendation

	if plan == nil {
		return recs
	}

	splitCount := 0
	redistributeCount := 0
	for _, action := range plan.HotPartitions {
		switch action.Action {
		case "split":
			splitCount++
		case "redistribute":
			redistributeCount++
		}
	}

	if splitCount > 0 {
		risk := plan.RebalanceImpact.RiskLevel
		priority := "medium"
		if risk == "high" {
			priority = "high"
		}

		recs = append(recs, Recommendation{
			Priority:    priority,
			Category:    "Rebalance",
			Title:       fmt.Sprintf("建议拆分 %d 个热点分区", splitCount),
			Description: fmt.Sprintf("检测到 %d 个热点分区需要拆分，预计改善 %.1f%% 的lag。风险等级: %s，预估停机时间: %s，数据迁移量: %.2f GB",
				splitCount, plan.EstimatedImprovement, risk, formatDuration(plan.RebalanceImpact.DowntimeEstimate), float64(plan.RebalanceImpact.DataMovementBytes)/1024/1024/1024),
			Action:      "在业务低峰期执行分区拆分。1) 创建新版本主题，分区数为原主题的N倍 2) 使用镜像工具或双写迁移数据 3) 逐步切换消费者到新主题。调用 /api/rebalance/{group} 查看详细计划。",
			Impact:      fmt.Sprintf("预计lag改善 %.1f%%，解决热点分区问题", plan.EstimatedImprovement),
			CodeExample: `# 查看详细重平衡计划
curl http://localhost:8080/api/rebalance/my-group

# 创建新主题(增加分区)
kafka-topics --create --topic my-topic-v2 \
  --partitions 12 --replication-factor 3 \
  --bootstrap-server localhost:9092

# 使用MirrorMaker 2.0迁移数据
# 或临时启动消费者消费旧主题+生产到新主题`,
		})
	}

	if redistributeCount > 0 {
		recs = append(recs, Recommendation{
			Priority:    "medium",
			Category:    "Rebalance",
			Title:       fmt.Sprintf("建议重分配 %d 个分区以平衡负载", redistributeCount),
			Description: fmt.Sprintf("%d 个分区分配不均，导致某些消费者负载过高。建议使用 StickyAssignor 或自定义分区分配策略。", redistributeCount),
			Action:      "修改消费者配置，使用更均衡的分配策略。1) 重启所有消费者触发再平衡 2) 考虑使用静态成员资格减少再平衡影响 3) 检查消费者实例是否有处理能力差异。",
			Impact:      "均衡消费者负载，提高整体消费能力",
			CodeExample: `// 消费者配置 - 使用StickyAssignor
props.put("partition.assignment.strategy", 
    "org.apache.kafka.clients.consumer.StickyAssignor");

// 启用静态成员资格(减少再平衡)
props.put("group.instance.id", "consumer-hostname-001");`,
		})
	}

	if len(plan.TopicsToExpand) > 0 {
		for _, expansion := range plan.TopicsToExpand {
			recs = append(recs, Recommendation{
				Priority:    "high",
				Category:    "Rebalance",
				Title:       fmt.Sprintf("建议将主题 %s 分区从 %d 增加到 %d", expansion.Topic, expansion.CurrentPartitions, expansion.RecommendedPartitions),
				Description: fmt.Sprintf("原因: %s。预计改善 %.1f%% 的lag。", expansion.Reason, expansion.ExpectedImprovement),
				Action:      "按以下步骤增加分区: 1) kafka-topics --alter --topic xxx --partitions N 2) 确保消费者数量随之调整 3) 注意: 已存在消息的分区不会重新分配。",
				Impact:      fmt.Sprintf("提高并行度，预计改善 %.1f%% 的消费能力", expansion.ExpectedImprovement),
				CodeExample: `# 增加分区
kafka-topics --alter --topic my-topic \
  --partitions ` + string(rune('0'+expansion.RecommendedPartitions)) + ` \
  --bootstrap-server localhost:9092

# 验证
kafka-topics --describe --topic my-topic`,
			})
		}
	}

	return recs
}

func formatDuration(d time.Duration) string {
	if d <= 0 {
		return "0秒"
	}

	days := int(d.Hours()) / 24
	hours := int(d.Hours()) % 24
	minutes := int(d.Minutes()) % 60
	seconds := int(d.Seconds()) % 60

	result := ""
	if days > 0 {
		result += string(rune('0'+days)) + "天"
	}
	if hours > 0 || days > 0 {
		result += string(rune('0'+hours)) + "小时"
	}
	if minutes > 0 || hours > 0 || days > 0 {
		result += string(rune('0'+minutes)) + "分钟"
	}
	if seconds > 0 && result == "" {
		result += string(rune('0'+seconds)) + "秒"
	}
	if result == "" {
		result = "< 1秒"
	}
	return result
}

func (a *lagAnalyzer) generateGeneralRecs(analysis *ConsumerGroupAnalysis) []Recommendation {
	var recs []Recommendation

	recs = append(recs, Recommendation{
		Priority:    "medium",
		Category:    "Monitoring",
		Title:       "建立完善的监控告警体系",
		Description: fmt.Sprintf("消费组 %s 状态为 %s，需要持续监控", analysis.GroupID, analysis.OverallStatus),
		Action:      "设置lag阈值告警。监控消费者提交延迟、处理速率等关键指标。建立lag增长趋势告警。",
		Impact:      "及时发现问题，避免影响业务",
	})

	recs = append(recs, Recommendation{
		Priority:    "low",
		Category:    "Maintenance",
		Title:       "定期检查消费者健康状态",
		Description: "定期维护可以预防很多问题",
		Action:      "定期检查消费者日志，查看是否有错误或异常。定期检查Kafka集群状态，包括ISR、副本同步等。",
		Impact:      "保持系统健康运行",
	})

	return recs
}
