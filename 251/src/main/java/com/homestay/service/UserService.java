package com.homestay.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.homestay.common.BusinessException;
import com.homestay.common.UserContext;
import com.homestay.dto.HostApplyDTO;
import com.homestay.dto.LoginDTO;
import com.homestay.dto.RegisterDTO;
import com.homestay.entity.User;
import com.homestay.mapper.UserMapper;
import com.homestay.utils.JwtUtil;
import com.homestay.vo.LoginVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.concurrent.TimeUnit;

@Service
public class UserService {

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    private static final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    public LoginVO login(LoginDTO dto) {
        User user = userMapper.selectOne(new LambdaQueryWrapper<User>()
                .eq(User::getUsername, dto.getUsername()));
        if (user == null) {
            throw new BusinessException("用户不存在");
        }
        if (!passwordEncoder.matches(dto.getPassword(), user.getPassword())) {
            throw new BusinessException("密码错误");
        }
        if (user.getDeleted() == 1) {
            throw new BusinessException("账号已被禁用");
        }
        String token = jwtUtil.generateToken(user.getId(), user.getUsername(), user.getRole());
        redisTemplate.opsForValue().set("token:" + user.getId(), token, 24, TimeUnit.HOURS);
        LoginVO vo = new LoginVO();
        vo.setUserId(user.getId());
        vo.setToken(token);
        vo.setUsername(user.getUsername());
        vo.setNickname(user.getNickname());
        vo.setAvatar(user.getAvatar());
        vo.setRole(user.getRole());
        vo.setHostStatus(user.getHostStatus());
        return vo;
    }

    public void register(RegisterDTO dto) {
        User existUser = userMapper.selectOne(new LambdaQueryWrapper<User>()
                .eq(User::getUsername, dto.getUsername()));
        if (existUser != null) {
            throw new BusinessException("用户名已存在");
        }
        User user = new User();
        user.setUsername(dto.getUsername());
        user.setPassword(passwordEncoder.encode(dto.getPassword()));
        user.setNickname(dto.getNickname());
        user.setPhone(dto.getPhone());
        user.setRole(1);
        user.setHostStatus(0);
        userMapper.insert(user);
    }

    public void applyHost(HostApplyDTO dto) {
        Long userId = UserContext.getUserId();
        if (userId == null) {
            throw new BusinessException("请先登录");
        }
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new BusinessException("用户不存在");
        }
        if (user.getHostStatus() == 1) {
            throw new BusinessException("已是房东");
        }
        if (user.getHostStatus() == 2) {
            throw new BusinessException("审核中，请耐心等待");
        }
        user.setHostIdCard(dto.getIdCard());
        user.setHostName(dto.getName());
        user.setHostApplyReason(dto.getApplyReason());
        user.setHostStatus(2);
        userMapper.updateById(user);
    }

    public void auditHost(Long userId, Integer status, String rejectReason) {
        Long currentUserId = UserContext.getUserId();
        User admin = userMapper.selectById(currentUserId);
        if (admin == null || admin.getRole() != 2) {
            throw new BusinessException("无权限操作");
        }
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new BusinessException("用户不存在");
        }
        if (status == 1) {
            user.setHostStatus(1);
            user.setRole(3);
        } else if (status == 3) {
            user.setHostStatus(3);
            user.setHostApplyReason(rejectReason);
        }
        userMapper.updateById(user);
    }

    public User getUserInfo() {
        Long userId = UserContext.getUserId();
        if (userId == null) {
            throw new BusinessException("请先登录");
        }
        User user = userMapper.selectById(userId);
        user.setPassword(null);
        return user;
    }

    public void logout() {
        Long userId = UserContext.getUserId();
        if (userId != null) {
            redisTemplate.delete("token:" + userId);
        }
    }
}
