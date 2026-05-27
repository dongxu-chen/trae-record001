package com.platform.points.service.impl;

import com.platform.points.vo.PointsRankVO;
import com.platform.points.service.PointsRankService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisCallback;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class PointsRankServiceImpl implements PointsRankService {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Value("${points.rank.top-size:100}")
    private int topSize;

    @Value("${points.rank.shard-count:16}")
    private int shardCount;

    private static final String RANK_KEY_PREFIX = "points:rank:shard:";
    private static final String TOP_RANK_CACHE_KEY = "points:rank:top:cache";
    private static final long TOP_CACHE_EXPIRE_SECONDS = 60;

    @Override
    public List<PointsRankVO> getTopRank(int size) {
        if (size <= 0) {
            size = topSize;
        }

        List<PointsRankVO> cachedTop = getTopRankFromCache(size);
        if (cachedTop != null && !cachedTop.isEmpty()) {
            return cachedTop;
        }

        List<PointsRankVO> result = getTopRankFromAllShards(size);

        if (!result.isEmpty()) {
            cacheTopRank(result);
        }

        return result;
    }

    @Override
    public PointsRankVO getUserRank(Long userId) {
        String shardKey = getShardKey(userId);
        ZSetOperations<String, Object> zSetOps = redisTemplate.opsForZSet();

        Long rank = zSetOps.reverseRank(shardKey, userId.toString());
        Double score = zSetOps.score(shardKey, userId.toString());

        PointsRankVO vo = new PointsRankVO();
        vo.setUserId(userId);
        vo.setPoints(score != null ? score.intValue() : 0);
        vo.setRank(rank != null ? rank.intValue() + 1 : -1);
        return vo;
    }

    @Override
    public void updateRank(Long userId, Integer points) {
        if (points == null || points == 0) {
            return;
        }

        try {
            String shardKey = getShardKey(userId);

            ZSetOperations<String, Object> zSetOps = redisTemplate.opsForZSet();
            zSetOps.incrementScore(shardKey, userId.toString(), points);

            log.debug("积分排行榜更新成功, userId: {}, points: {}, shard: {}", userId, points, shardKey);

            if (points > 0) {
                clearTopRankCache();
            }
        } catch (Exception e) {
            log.error("积分排行榜更新失败, userId: {}", userId, e);
        }
    }

    private String getShardKey(Long userId) {
        long shardIndex = Math.abs(userId.hashCode()) % shardCount;
        return RANK_KEY_PREFIX + shardIndex;
    }

    private List<PointsRankVO> getTopRankFromAllShards(int size) {
        Map<Long, Integer> allScores = new HashMap<>();

        for (int i = 0; i < shardCount; i++) {
            String shardKey = RANK_KEY_PREFIX + i;
            try {
                ZSetOperations<String, Object> zSetOps = redisTemplate.opsForZSet();
                Set<ZSetOperations.TypedTuple<Object>> tuples =
                        zSetOps.reverseRangeWithScores(shardKey, 0, size - 1);
                if (tuples != null) {
                    for (ZSetOperations.TypedTuple<Object> tuple : tuples) {
                        Long userId = Long.valueOf(tuple.getValue().toString());
                        int score = tuple.getScore() != null ? tuple.getScore().intValue() : 0;
                        allScores.merge(userId, score, Integer::sum);
                    }
                }
            } catch (Exception e) {
                log.error("读取分片排行榜失败, shardKey: {}", shardKey, e);
            }
        }

        List<Map.Entry<Long, Integer>> sortedEntries = new ArrayList<>(allScores.entrySet());
        sortedEntries.sort((a, b) -> Integer.compare(b.getValue(), a.getValue()));

        List<PointsRankVO> result = new ArrayList<>();
        int rank = 1;
        for (Map.Entry<Long, Integer> entry : sortedEntries) {
            if (rank > size) break;
            PointsRankVO vo = new PointsRankVO();
            vo.setUserId(entry.getKey());
            vo.setPoints(entry.getValue());
            vo.setRank(rank++);
            result.add(vo);
        }

        return result;
    }

    @SuppressWarnings("unchecked")
    private List<PointsRankVO> getTopRankFromCache(int size) {
        try {
            Object cached = redisTemplate.opsForValue().get(TOP_RANK_CACHE_KEY);
            if (cached instanceof List) {
                List<PointsRankVO> cachedList = (List<PointsRankVO>) cached;
                if (cachedList.size() >= size) {
                    return cachedList.subList(0, size);
                }
                return cachedList;
            }
        } catch (Exception e) {
            log.warn("获取排行榜缓存失败", e);
        }
        return null;
    }

    private void cacheTopRank(List<PointsRankVO> topList) {
        try {
            redisTemplate.opsForValue().set(TOP_RANK_CACHE_KEY, topList, TOP_CACHE_EXPIRE_SECONDS, TimeUnit.SECONDS);
        } catch (Exception e) {
            log.warn("缓存排行榜失败", e);
        }
    }

    private void clearTopRankCache() {
        try {
            redisTemplate.delete(TOP_RANK_CACHE_KEY);
        } catch (Exception e) {
            log.warn("清除排行榜缓存失败", e);
        }
    }

    public void batchUpdateRank(Map<Long, Integer> userPointsMap) {
        if (userPointsMap == null || userPointsMap.isEmpty()) {
            return;
        }

        try {
            redisTemplate.executePipelined((RedisCallback<Void>) connection -> {
                ZSetOperations<String, Object> zSetOps = redisTemplate.opsForZSet();
                for (Map.Entry<Long, Integer> entry : userPointsMap.entrySet()) {
                    String shardKey = getShardKey(entry.getKey());
                    zSetOps.incrementScore(shardKey, entry.getKey().toString(), entry.getValue());
                }
                return null;
            });
            clearTopRankCache();
            log.info("批量更新排行榜成功, 数量: {}", userPointsMap.size());
        } catch (Exception e) {
            log.error("批量更新排行榜失败", e);
        }
    }
}
