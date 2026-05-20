package com.econtract.controller;

import com.econtract.common.Result;
import com.econtract.dto.FaceVerifyDTO;
import com.econtract.dto.IdentityVerifyDTO;
import com.econtract.security.UserContext;
import com.econtract.service.FaceService;
import com.econtract.service.UserService;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;

@RestController
@RequestMapping("/user")
public class UserController {

    @Resource
    private UserService userService;

    @Resource
    private FaceService faceService;

    @PostMapping("/identity-verify")
    public Result<Void> identityVerify(@Validated @RequestBody IdentityVerifyDTO verifyDTO) {
        Long userId = UserContext.getCurrentUserId();
        userService.identityVerify(userId, verifyDTO);
        return Result.success("实名认证成功", null);
    }

    @PostMapping("/face-verify")
    public Result<Boolean> faceVerify(@Validated @RequestBody FaceVerifyDTO verifyDTO) {
        Long userId = UserContext.getCurrentUserId();
        boolean result = faceService.verifyFace(userId, verifyDTO.getVerifyType(), verifyDTO.getFaceImage());
        return Result.success(result);
    }

    @PostMapping("/face-save")
    public Result<Void> saveFaceImage(@RequestBody String faceImage) {
        Long userId = UserContext.getCurrentUserId();
        faceService.saveFaceImage(userId, faceImage);
        return Result.success("人脸照片保存成功", null);
    }
}
