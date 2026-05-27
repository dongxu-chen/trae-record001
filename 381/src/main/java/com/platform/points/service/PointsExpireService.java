package com.platform.points.service;

public interface PointsExpireService {

    void processExpire(Long userId, Integer points);

    void expirePoints(Long userId, Integer points);

    void batchExpire();
}
