package com.homestay.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.homestay.common.BusinessException;
import com.homestay.common.UserContext;
import com.homestay.entity.Blacklist;
import com.homestay.entity.User;
import com.homestay.entity.UserBehavior;
import com.homestay.mapper.BlacklistMapper;
import com.homestay.mapper.UserBehaviorMapper;
import com.homestay.mapper.UserMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class BlacklistService {

    private static final int BEHAVIOR_CANCEL_ORDER = 1;
    private static final int BEHAVIOR_NO_SHOW = 2;
    private static final int BEHAVIOR_VIOLATION = 3;

    private static final int CANCEL_THRESHOLD_DAYS = 30;
    private static final int CANCEL_THRESHOLD_COUNT = 5;

    @Autowired
    private BlacklistMapper blacklistMapper;

    @Autowired
    private UserBehaviorMapper userBehaviorMapper;

    @Autowired
    private UserMapper userMapper;

    public void recordBehavior(Long userId, Integer behaviorType, Long targetId, String remark) {
        UserBehavior behavior = new UserBehavior();
        behavior.setUserId(userId);
        behavior.setBehaviorType(behaviorType);
        behavior.setTargetId(targetId);
        behavior.setRemark(remark);
        userBehaviorMapper.insert(behavior);

        if (behaviorType == BEHAVIOR_CANCEL_ORDER) {
            checkAndAutoBlacklist(userId);
        }
    }

    private void checkAndAutoBlacklist(Long userId) {
        LocalDateTime thirtyDaysAgo = LocalDateTime.now().minusDays(CANCEL_THRESHOLD_DAYS);
        int cancelCount = userBehaviorMapper.countUserBehavior(userId, BEHAVIOR_CANCEL_ORDER, thirtyDaysAgo);

        if (cancelCount >= CANCEL_THRESHOLD_COUNT) {
            if (!blacklistMapper.isUserBlacklisted(userId, LocalDateTime.now())) {
                User user = userMapper.selectById(userId);
                Blacklist blacklist = new Blacklist();
                blacklist.setUserId(userId);
                blacklist.setUsername(user != null ? user.getUsername() : "");
                blacklist.setPhone(user != null ? user.getPhone() : "");
                blacklist.setReason(1);
                blacklist.setRemark("30天内取消订单超过" + CANCEL_THRESHOLD_COUNT + "次，系统自动拉黑");
                blacklist.setStartTime(LocalDateTime.now());
                blacklist.setEndTime(LocalDateTime.now().plusDays(30));
                blacklist.setStatus(1);
                blacklistMapper.insert(blacklist);
            }
        }
    }

    public boolean isUserBlacklisted(Long userId) {
        return blacklistMapper.isUserBlacklisted(userId, LocalDateTime.now());
    }

    public Blacklist getActiveBlacklist(Long userId) {
        return blacklistMapper.findActiveBlacklist(userId, LocalDateTime.now());
    }

    public void checkBlacklist(Long userId) {
        if (isUserBlacklisted(userId)) {
            Blacklist blacklist = getActiveBlacklist(userId);
            String reason = blacklist != null ? blacklist.getRemark() : "您已被限制预订";
            throw new BusinessException(reason + "，如有疑问请联系客服");
        }
    }

    @Transactional(rollbackFor = Exception.class)
    public void addToBlacklist(Long userId, Integer reason, String remark, Integer days) {
        Long currentUserId = UserContext.getUserId();
        User admin = userMapper.selectById(currentUserId);
        if (admin == null || admin.getRole() != 2) {
            throw new BusinessException("无权限操作");
        }
        if (blacklistMapper.isUserBlacklisted(userId, LocalDateTime.now())) {
            throw new BusinessException("用户已在黑名单中");
        }
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new BusinessException("用户不存在");
        }
        Blacklist blacklist = new Blacklist();
        blacklist.setUserId(userId);
        blacklist.setUsername(user.getUsername());
        blacklist.setPhone(user.getPhone());
        blacklist.setReason(reason);
        blacklist.setRemark(remark);
        blacklist.setStartTime(LocalDateTime.now());
        if (days != null && days > 0) {
            blacklist.setEndTime(LocalDateTime.now().plusDays(days));
        }
        blacklist.setStatus(1);
        blacklistMapper.insert(blacklist);
    }

    @Transactional(rollbackFor = Exception.class)
    public void removeFromBlacklist(Long id) {
        Long currentUserId = UserContext.getUserId();
        User admin = userMapper.selectById(currentUserId);
        if (admin == null || admin.getRole() != 2) {
            throw new BusinessException("无权限操作");
        }
        Blacklist blacklist = blacklistMapper.selectById(id);
        if (blacklist == null) {
            throw new BusinessException("黑名单记录不存在");
        }
        blacklist.setStatus(0);
        blacklist.setEndTime(LocalDateTime.now());
        blacklistMapper.updateById(blacklist);
    }

    public List<Blacklist> getBlacklist(Integer status, int pageNum, int pageSize) {
        LambdaQueryWrapper<Blacklist> wrapper = new LambdaQueryWrapper<>();
        if (status != null) {
            wrapper.eq(Blacklist::getStatus, status);
        }
        wrapper.orderByDesc(Blacklist::getCreateTime)
                .last("LIMIT " + (pageNum - 1) * pageSize + "," + pageSize);
        return blacklistMapper.selectList(wrapper);
    }

    public void recordCancelOrder(Long userId, Long orderId) {
        recordBehavior(userId, BEHAVIOR_CANCEL_ORDER, orderId, "取消订单");
    }

    public void recordNoShow(Long userId, Long orderId) {
        recordBehavior(userId, BEHAVIOR_NO_SHOW, orderId, "未入住");
    }

    public void recordViolation(Long userId, Long orderId, String remark) {
        recordBehavior(userId, BEHAVIOR_VIOLATION, orderId, remark);
    }
}
