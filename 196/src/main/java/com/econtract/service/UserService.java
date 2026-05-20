package com.econtract.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.econtract.common.BusinessException;
import com.econtract.common.ResultCode;
import com.econtract.dto.IdentityVerifyDTO;
import com.econtract.dto.LoginDTO;
import com.econtract.dto.RegisterDTO;
import com.econtract.entity.User;
import com.econtract.mapper.UserMapper;
import com.econtract.util.JwtUtil;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.util.HashMap;
import java.util.Map;

@Service
public class UserService {

    @Resource
    private UserMapper userMapper;

    @Resource
    private PasswordEncoder passwordEncoder;

    @Resource
    private JwtUtil jwtUtil;

    @Resource
    private SmsService smsService;

    @Resource
    private FaceService faceService;

    public Map<String, Object> login(LoginDTO loginDTO) {
        QueryWrapper<User> wrapper = new QueryWrapper<>();
        wrapper.eq("username", loginDTO.getUsername()).or().eq("phone", loginDTO.getUsername());
        User user = userMapper.selectOne(wrapper);
        if (user == null) {
            throw new BusinessException(ResultCode.USER_NOT_FOUND);
        }
        if (user.getStatus() == 0) {
            throw new BusinessException(ResultCode.USER_DISABLED);
        }
        if (!passwordEncoder.matches(loginDTO.getPassword(), user.getPassword())) {
            throw new BusinessException(ResultCode.USER_PASSWORD_ERROR);
        }
        String token = jwtUtil.generateToken(user.getId(), user.getUsername());
        Map<String, Object> result = new HashMap<>();
        result.put("token", token);
        result.put("userId", user.getId());
        result.put("username", user.getUsername());
        result.put("realName", user.getRealName());
        result.put("identityVerified", user.getIdentityVerified());
        return result;
    }

    @Transactional(rollbackFor = Exception.class)
    public void register(RegisterDTO registerDTO) {
        QueryWrapper<User> wrapper = new QueryWrapper<>();
        wrapper.eq("username", registerDTO.getUsername());
        if (userMapper.selectCount(wrapper) > 0) {
            throw new BusinessException(ResultCode.USER_ALREADY_EXISTS);
        }
        wrapper.clear();
        wrapper.eq("phone", registerDTO.getPhone());
        if (userMapper.selectCount(wrapper) > 0) {
            throw new BusinessException(ResultCode.PHONE_ALREADY_EXISTS);
        }
        smsService.verifyCode(registerDTO.getPhone(), registerDTO.getSmsCode(), "REGISTER");
        User user = new User();
        user.setUsername(registerDTO.getUsername());
        user.setPassword(passwordEncoder.encode(registerDTO.getPassword()));
        user.setRealName(registerDTO.getRealName());
        user.setPhone(registerDTO.getPhone());
        user.setStatus(1);
        user.setIdentityVerified(0);
        userMapper.insert(user);
    }

    @Transactional(rollbackFor = Exception.class)
    public void identityVerify(Long userId, IdentityVerifyDTO verifyDTO) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new BusinessException(ResultCode.USER_NOT_FOUND);
        }
        faceService.verifyFace(userId, "IDENTITY", verifyDTO.getFaceImage());
        user.setRealName(verifyDTO.getRealName());
        user.setIdCard(verifyDTO.getIdCard());
        user.setFaceImage(verifyDTO.getFaceImage());
        user.setIdentityVerified(1);
        userMapper.updateById(user);
    }

    public User getUserInfo(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new BusinessException(ResultCode.USER_NOT_FOUND);
        }
        user.setPassword(null);
        return user;
    }
}
