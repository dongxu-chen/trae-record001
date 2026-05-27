package com.platform.points.service;

import com.platform.points.vo.PointsRankVO;

import java.util.List;

public interface PointsRankService {

    List<PointsRankVO> getTopRank(int topSize);

    PointsRankVO getUserRank(Long userId);

    void updateRank(Long userId, Integer points);
}
