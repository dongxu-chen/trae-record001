package com.platform.points.service;

import com.platform.points.entity.PointsLevelConfig;
import com.platform.points.vo.UserLevelVO;

import java.util.List;

public interface UserLevelService {

    UserLevelVO getUserLevel(Long userId);

    List<PointsLevelConfig> getAllLevelConfigs();

    void checkAndUpdateLevel(Long userId, Integer totalPoints);

    void initUserLevel(Long userId);
}
