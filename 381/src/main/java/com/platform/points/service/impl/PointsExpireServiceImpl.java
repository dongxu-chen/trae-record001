package com.platform.points.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.platform.points.entity.PointsExpire;
import com.platform.points.entity.PointsRecord;
import com.platform.points.entity.UserPoints;
import com.platform.points.enums.PointsSourceEnum;
import com.platform.points.enums.PointsTypeEnum;
import com.platform.points.exception.BusinessException;
import com.platform.points.mapper.PointsExpireMapper;
import com.platform.points.mapper.PointsRecordMapper;
import com.platform.points.mapper.UserPointsMapper;
import com.platform.points.service.PointsExpireService;
import com.platform.points.service.PointsRankService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@Service
public class PointsExpireServiceImpl implements PointsExpireService {

    private static final int BATCH_SIZE = 1000;
    private static final int MAX_ROUNDS = 100;

    @Autowired
    private PointsExpireMapper pointsExpireMapper;

    @Autowired
    private UserPointsMapper userPointsMapper;

    @Autowired
    private PointsRecordMapper pointsRecordMapper;

    @Autowired
    private PointsRankService pointsRankService;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void processExpire(Long userId, Integer points) {
        UserPoints userPoints = getUserPointsEntity(userId);
        if (userPoints == null || userPoints.getAvailablePoints() < points) {
            log.warn("用户可用积分不足，无法执行过期扣减, userId: {}, available: {}, need: {}",
                    userId, userPoints != null ? userPoints.getAvailablePoints() : 0, points);
            return;
        }

        int balanceBefore = userPoints.getAvailablePoints();
        int balanceAfter = balanceBefore - points;

        int rows = userPointsMapper.deductPoints(userId, points);
        if (rows == 0) {
            throw new BusinessException("积分过期扣减失败");
        }

        PointsRecord record = new PointsRecord();
        record.setUserId(userId);
        record.setOrderNo("EXPIRE" + System.currentTimeMillis() + userId);
        record.setPointsType(PointsTypeEnum.DEDUCT.getCode());
        record.setPointsSource(PointsSourceEnum.EXPIRE.getCode());
        record.setPoints(points);
        record.setBalanceBefore(balanceBefore);
        record.setBalanceAfter(balanceAfter);
        record.setDescription("积分自动过期");
        pointsRecordMapper.insert(record);

        pointsRankService.updateRank(userId, -points);

        log.info("积分过期扣减成功, userId: {}, points: {}", userId, points);
    }

    @Override
    public void expirePoints(Long userId, Integer points) {
        processExpire(userId, points);
    }

    @Override
    public void batchExpire() {
        log.info("开始批量处理过期积分，批次大小: {}", BATCH_SIZE);

        int totalProcessed = 0;
        int round = 0;
        long lastId = 0L;
        LocalDateTime now = LocalDateTime.now();

        while (round < MAX_ROUNDS) {
            round++;
            List<PointsExpire> expireList = pointsExpireMapper.selectBatchExpired(lastId, now, BATCH_SIZE);
            if (expireList.isEmpty()) {
                log.info("第{}轮无过期数据，批量处理结束，共处理{}条记录", round - 1, totalProcessed);
                break;
            }

            log.info("第{}轮查询到{}条过期记录", round, expireList.size());

            Map<Long, Integer> userExpireMap = new HashMap<>();
            List<Long> expireIds = new ArrayList<>();

            for (PointsExpire expire : expireList) {
                Integer remaining = expire.getRemainingPoints();
                if (remaining != null && remaining > 0) {
                    userExpireMap.merge(expire.getUserId(), remaining, Integer::sum);
                    expireIds.add(expire.getId());
                }
                lastId = Math.max(lastId, expire.getId());
            }

            for (Map.Entry<Long, Integer> entry : userExpireMap.entrySet()) {
                try {
                    processExpire(entry.getKey(), entry.getValue());
                } catch (Exception e) {
                    log.error("处理用户过期积分失败, userId: {}", entry.getKey(), e);
                }
            }

            for (Long expireId : expireIds) {
                try {
                    pointsExpireMapper.markExpired(expireId);
                } catch (Exception e) {
                    log.error("标记过期记录失败, expireId: {}", expireId, e);
                }
            }

            totalProcessed += expireList.size();
            log.info("第{}轮处理完成，本批次{}条，累计{}条", round, expireList.size(), totalProcessed);

            if (expireList.size() < BATCH_SIZE) {
                log.info("本批次数据不足{}条，已全部处理完成，共处理{}条记录", BATCH_SIZE, totalProcessed);
                break;
            }

            try {
                Thread.sleep(100);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }

        if (round >= MAX_ROUNDS) {
            log.warn("达到最大轮次限制{}，可能还有未处理的过期数据", MAX_ROUNDS);
        }

        log.info("批量处理过期积分任务结束，共处理{}条记录", totalProcessed);
    }

    private UserPoints getUserPointsEntity(Long userId) {
        LambdaQueryWrapper<UserPoints> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserPoints::getUserId, userId);
        return userPointsMapper.selectOne(wrapper);
    }
}
