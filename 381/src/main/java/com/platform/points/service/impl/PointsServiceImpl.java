package com.platform.points.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.platform.points.annotation.DistributedLock;
import com.platform.points.dto.PointsDeductDTO;
import com.platform.points.dto.PointsGrantDTO;
import com.platform.points.dto.PointsRecordQueryDTO;
import com.platform.points.entity.PointsExpire;
import com.platform.points.entity.PointsRecord;
import com.platform.points.entity.UserPoints;
import com.platform.points.enums.PointsSourceEnum;
import com.platform.points.enums.PointsStatusEnum;
import com.platform.points.enums.PointsTypeEnum;
import com.platform.points.exception.BusinessException;
import com.platform.points.mapper.PointsExpireMapper;
import com.platform.points.mapper.PointsRecordMapper;
import com.platform.points.mapper.UserPointsMapper;
import com.platform.points.mq.PointsMQProducer;
import com.platform.points.service.PointsExpireService;
import com.platform.points.service.PointsRankService;
import com.platform.points.service.PointsService;
import com.platform.points.service.UserLevelService;
import com.platform.points.vo.PointsRecordVO;
import com.platform.points.vo.UserPointsVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class PointsServiceImpl implements PointsService {

    @Autowired
    private UserPointsMapper userPointsMapper;

    @Autowired
    private PointsRecordMapper pointsRecordMapper;

    @Autowired
    private PointsExpireMapper pointsExpireMapper;

    @Autowired
    private PointsMQProducer pointsMQProducer;

    @Autowired
    private PointsExpireService pointsExpireService;

    @Autowired
    private PointsRankService pointsRankService;

    @Autowired
    private UserLevelService userLevelService;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Value("${points.expire.days}")
    private int expireDays;

    private static final String REQUEST_KEY_PREFIX = "points:request:";

    @Override
    public UserPointsVO getUserPoints(Long userId) {
        LambdaQueryWrapper<UserPoints> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserPoints::getUserId, userId);
        UserPoints userPoints = userPointsMapper.selectOne(wrapper);
        if (userPoints == null) {
            userPoints = initUserPoints(userId);
        }
        UserPointsVO vo = new UserPointsVO();
        BeanUtils.copyProperties(userPoints, vo);
        return vo;
    }

    @Override
    public void grantPoints(PointsGrantDTO dto) {
        if (isDuplicateRequest(dto.getOrderNo())) {
            throw new BusinessException("重复的请求，请勿重复操作");
        }
        pointsMQProducer.sendGrantMessage(dto);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    @DistributedLock(key = "#dto.userId", prefix = "points:grant:lock:", watchdog = true)
    public void processGrant(PointsGrantDTO dto) {
        Long userId = dto.getUserId();
        Integer points = dto.getPoints();

        UserPoints userPoints = getUserPointsEntity(userId);
        int balanceBefore = userPoints.getAvailablePoints();
        int balanceAfter = balanceBefore + points;

        int rows = userPointsMapper.addPoints(userId, points);
        if (rows == 0) {
            throw new BusinessException("积分发放失败，请稍后重试");
        }

        PointsRecord record = new PointsRecord();
        record.setUserId(userId);
        record.setOrderNo(generateOrderNo());
        record.setPointsType(PointsTypeEnum.GRANT.getCode());
        record.setPointsSource(dto.getSource());
        record.setPoints(points);
        record.setBalanceBefore(balanceBefore);
        record.setBalanceAfter(balanceAfter);
        record.setDescription(dto.getDescription());
        record.setRemark(dto.getRemark());
        pointsRecordMapper.insert(record);

        saveExpireRecord(userId, points, dto.getSource(), record.getOrderNo());

        pointsRankService.updateRank(userId, points);

        userLevelService.checkAndUpdateLevel(userId, balanceAfter);

        markRequestProcessed(dto.getOrderNo());

        log.info("积分发放成功, userId: {}, points: {}, source: {}", userId, points, dto.getSource());
    }

    @Override
    public void deductPoints(PointsDeductDTO dto) {
        if (isDuplicateRequest(dto.getOrderNo())) {
            throw new BusinessException("重复的请求，请勿重复操作");
        }
        pointsMQProducer.sendDeductMessage(dto);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    @DistributedLock(key = "#dto.userId", prefix = "points:deduct:lock:", watchdog = true)
    public void processDeduct(PointsDeductDTO dto) {
        Long userId = dto.getUserId();
        Integer points = dto.getPoints();

        UserPoints userPoints = getUserPointsEntity(userId);
        if (userPoints.getAvailablePoints() < points) {
            throw new BusinessException("可用积分不足");
        }

        int balanceBefore = userPoints.getAvailablePoints();
        int balanceAfter = balanceBefore - points;

        int rows = userPointsMapper.deductPoints(userId, points);
        if (rows == 0) {
            throw new BusinessException("积分扣减失败，请稍后重试");
        }

        consumeExpirePoints(userId, points);

        PointsRecord record = new PointsRecord();
        record.setUserId(userId);
        record.setOrderNo(generateOrderNo());
        record.setPointsType(PointsTypeEnum.DEDUCT.getCode());
        record.setPointsSource(dto.getSource());
        record.setPoints(points);
        record.setBalanceBefore(balanceBefore);
        record.setBalanceAfter(balanceAfter);
        record.setDescription(dto.getDescription());
        record.setRemark(dto.getRemark());
        pointsRecordMapper.insert(record);

        pointsRankService.updateRank(userId, -points);

        markRequestProcessed(dto.getOrderNo());

        log.info("积分扣减成功, userId: {}, points: {}, source: {}", userId, points, dto.getSource());
    }

    @Override
    public IPage<PointsRecordVO> queryRecords(PointsRecordQueryDTO dto) {
        Page<PointsRecordVO> page = new Page<>(dto.getPageNum(), dto.getPageSize());
        return pointsRecordMapper.selectRecordPage(page, dto);
    }

    private UserPoints initUserPoints(Long userId) {
        UserPoints userPoints = new UserPoints();
        userPoints.setUserId(userId);
        userPoints.setTotalPoints(0);
        userPoints.setAvailablePoints(0);
        userPoints.setFrozenPoints(0);
        userPointsMapper.insert(userPoints);
        return userPoints;
    }

    private UserPoints getUserPointsEntity(Long userId) {
        LambdaQueryWrapper<UserPoints> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserPoints::getUserId, userId);
        UserPoints userPoints = userPointsMapper.selectOne(wrapper);
        if (userPoints == null) {
            return initUserPoints(userId);
        }
        return userPoints;
    }

    private void saveExpireRecord(Long userId, Integer points, Integer source, String orderNo) {
        PointsExpire expire = new PointsExpire();
        expire.setUserId(userId);
        expire.setPoints(points);
        expire.setRemainingPoints(points);
        expire.setSource(source);
        expire.setSourceOrderNo(orderNo);
        expire.setExpireTime(LocalDateTime.now().plusDays(expireDays));
        expire.setStatus(PointsStatusEnum.NORMAL.getCode());
        pointsExpireMapper.insert(expire);
    }

    private void consumeExpirePoints(Long userId, Integer pointsToConsume) {
        List<PointsExpire> expireList = pointsExpireMapper.selectExpiredByUserId(userId);
        int remaining = pointsToConsume;
        for (PointsExpire expire : expireList) {
            if (remaining <= 0) break;
            int consume = Math.min(expire.getRemainingPoints(), remaining);
            pointsExpireMapper.consumePoints(expire.getId(), consume);
            remaining -= consume;
        }
        if (remaining > 0) {
            log.warn("积分过期记录不足, userId: {}, 未消耗积分数: {}", userId, remaining);
        }
    }

    private String generateOrderNo() {
        return UUID.randomUUID().toString().replace("-", "").toUpperCase();
    }

    private boolean isDuplicateRequest(String orderNo) {
        if (orderNo == null) return false;
        String key = REQUEST_KEY_PREFIX + orderNo;
        Boolean exists = redisTemplate.hasKey(key);
        return Boolean.TRUE.equals(exists);
    }

    private void markRequestProcessed(String orderNo) {
        if (orderNo == null) return;
        String key = REQUEST_KEY_PREFIX + orderNo;
        redisTemplate.opsForValue().set(key, "1", 24, TimeUnit.HOURS);
    }
}
