package com.platform.points.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.platform.points.entity.PointsLevelConfig;
import com.platform.points.entity.UserLevel;
import com.platform.points.entity.UserLevelLog;
import com.platform.points.entity.UserPoints;
import com.platform.points.mapper.PointsLevelConfigMapper;
import com.platform.points.mapper.UserLevelLogMapper;
import com.platform.points.mapper.UserLevelMapper;
import com.platform.points.mapper.UserPointsMapper;
import com.platform.points.service.UserLevelService;
import com.platform.points.vo.UserLevelVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
public class UserLevelServiceImpl implements UserLevelService {

    @Autowired
    private UserLevelMapper userLevelMapper;

    @Autowired
    private PointsLevelConfigMapper levelConfigMapper;

    @Autowired
    private UserLevelLogMapper userLevelLogMapper;

    @Autowired
    private UserPointsMapper userPointsMapper;

    @Override
    public UserLevelVO getUserLevel(Long userId) {
        UserLevel userLevel = userLevelMapper.selectByUserId(userId);
        if (userLevel == null) {
            initUserLevel(userId);
            userLevel = userLevelMapper.selectByUserId(userId);
        }

        PointsLevelConfig currentConfig = levelConfigMapper.selectById(userLevel.getCurrentLevelId());
        PointsLevelConfig nextConfig = levelConfigMapper.selectNextLevel(userLevel.getCurrentLevelOrder());

        UserLevelVO vo = new UserLevelVO();
        BeanUtils.copyProperties(userLevel, vo);

        if (currentConfig != null) {
            vo.setLevelIcon(currentConfig.getLevelIcon());
            vo.setDiscountRate(currentConfig.getDiscountRate());
            vo.setLevelPrivileges(currentConfig.getLevelPrivileges());
        }

        if (nextConfig != null) {
            vo.setNextLevelName(nextConfig.getLevelName());
            vo.setNextLevelPoints(nextConfig.getMinPoints());
            int pointsToNext = nextConfig.getMinPoints() - userLevel.getTotalPoints();
            vo.setPointsToNextLevel(Math.max(0, pointsToNext));
            int levelRange = nextConfig.getMinPoints() - currentConfig.getMinPoints();
            int currentProgress = userLevel.getTotalPoints() - currentConfig.getMinPoints();
            vo.setProgressPercent(Math.min(100.0, Math.max(0.0, (double) currentProgress / levelRange * 100)));
        } else {
            vo.setPointsToNextLevel(0);
            vo.setProgressPercent(100.0);
        }

        return vo;
    }

    @Override
    public List<PointsLevelConfig> getAllLevelConfigs() {
        return levelConfigMapper.selectAllActiveLevels();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void checkAndUpdateLevel(Long userId, Integer totalPoints) {
        UserLevel userLevel = userLevelMapper.selectByUserId(userId);
        if (userLevel == null) {
            initUserLevel(userId);
            return;
        }

        PointsLevelConfig newLevel = levelConfigMapper.selectLevelByPoints(totalPoints);
        if (newLevel == null) {
            return;
        }

        if (!newLevel.getId().equals(userLevel.getCurrentLevelId()) && newLevel.getLevelOrder() > userLevel.getCurrentLevelOrder()) {
            log.info("用户等级升级, userId: {}, {} -> {}", userId, userLevel.getCurrentLevelName(), newLevel.getLevelName());

            recordLevelUpLog(userId, userLevel, newLevel, totalPoints);

            userLevel.setCurrentLevelId(newLevel.getId());
            userLevel.setCurrentLevelCode(newLevel.getLevelCode());
            userLevel.setCurrentLevelName(newLevel.getLevelName());
            userLevel.setCurrentLevelOrder(newLevel.getLevelOrder());
            userLevel.setTotalPoints(totalPoints);
            userLevel.setLevelPoints(totalPoints - newLevel.getMinPoints());
            userLevel.setLevelUpTime(LocalDateTime.now());
            userLevelMapper.updateById(userLevel);
        } else {
            userLevel.setTotalPoints(totalPoints);
            userLevel.setLevelPoints(totalPoints - newLevel.getMinPoints());
            userLevelMapper.updateById(userLevel);
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void initUserLevel(Long userId) {
        LambdaQueryWrapper<UserPoints> pointsWrapper = new LambdaQueryWrapper<>();
        pointsWrapper.eq(UserPoints::getUserId, userId);
        UserPoints userPoints = userPointsMapper.selectOne(pointsWrapper);

        int totalPoints = userPoints != null ? userPoints.getTotalPoints() : 0;
        PointsLevelConfig initialLevel = levelConfigMapper.selectLevelByPoints(totalPoints);
        if (initialLevel == null) {
            List<PointsLevelConfig> allLevels = levelConfigMapper.selectAllActiveLevels();
            if (allLevels.isEmpty()) {
                return;
            }
            initialLevel = allLevels.get(0);
        }

        UserLevel userLevel = new UserLevel();
        userLevel.setUserId(userId);
        userLevel.setCurrentLevelId(initialLevel.getId());
        userLevel.setCurrentLevelCode(initialLevel.getLevelCode());
        userLevel.setCurrentLevelName(initialLevel.getLevelName());
        userLevel.setCurrentLevelOrder(initialLevel.getLevelOrder());
        userLevel.setTotalPoints(totalPoints);
        userLevel.setLevelPoints(Math.max(0, totalPoints - initialLevel.getMinPoints()));
        userLevel.setLevelUpTime(LocalDateTime.now());
        userLevelMapper.insert(userLevel);

        log.info("初始化用户等级, userId: {}, level: {}", userId, initialLevel.getLevelName());
    }

    private void recordLevelUpLog(Long userId, UserLevel currentLevel, PointsLevelConfig newLevel, Integer triggerPoints) {
        UserLevelLog levelLog = new UserLevelLog();
        levelLog.setUserId(userId);
        levelLog.setBeforeLevelId(currentLevel.getCurrentLevelId());
        levelLog.setBeforeLevelCode(currentLevel.getCurrentLevelCode());
        levelLog.setBeforeLevelName(currentLevel.getCurrentLevelName());
        levelLog.setAfterLevelId(newLevel.getId());
        levelLog.setAfterLevelCode(newLevel.getLevelCode());
        levelLog.setAfterLevelName(newLevel.getLevelName());
        levelLog.setChangeType(1);
        levelLog.setChangeReason("积分累计升级");
        levelLog.setTriggerPoints(triggerPoints);
        userLevelLogMapper.insert(levelLog);
    }
}
