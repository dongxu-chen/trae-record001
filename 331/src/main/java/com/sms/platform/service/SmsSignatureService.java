package com.sms.platform.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.sms.platform.common.exception.BusinessException;
import com.sms.platform.entity.SmsSignature;
import com.sms.platform.mapper.SmsSignatureMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import javax.annotation.Resource;
import java.util.List;

@Slf4j
@Service
public class SmsSignatureService {

    @Resource
    private SmsSignatureMapper signatureMapper;

    public void addSignature(SmsSignature signature) {
        SmsSignature exists = signatureMapper.selectOne(
                new LambdaQueryWrapper<SmsSignature>()
                        .eq(SmsSignature::getSmsType, signature.getSmsType())
                        .eq(SmsSignature::getChannelCode, signature.getChannelCode())
                        .eq(SmsSignature::getDeleted, 0)
        );
        if (exists != null) {
            throw new BusinessException("该短信类型和通道的签名已存在");
        }
        signatureMapper.insert(signature);
        log.info("添加签名成功: {}", signature.getSignatureName());
    }

    public void updateSignature(SmsSignature signature) {
        SmsSignature exists = signatureMapper.selectById(signature.getId());
        if (exists == null || exists.getDeleted() == 1) {
            throw new BusinessException("签名不存在");
        }
        signatureMapper.updateById(signature);
        log.info("更新签名成功: id={}", signature.getId());
    }

    public void deleteSignature(Long id) {
        SmsSignature signature = signatureMapper.selectById(id);
        if (signature == null || signature.getDeleted() == 1) {
            throw new BusinessException("签名不存在");
        }
        signature.setDeleted(1);
        signatureMapper.updateById(signature);
        log.info("删除签名成功: id={}", id);
    }

    public SmsSignature getSignature(Long id) {
        SmsSignature signature = signatureMapper.selectById(id);
        if (signature == null || signature.getDeleted() == 1) {
            throw new BusinessException("签名不存在");
        }
        return signature;
    }

    public Page<SmsSignature> listSignatures(Integer pageNum, Integer pageSize, Integer smsType, Integer channelCode, Integer status) {
        Page<SmsSignature> page = new Page<>(pageNum, pageSize);
        LambdaQueryWrapper<SmsSignature> wrapper = new LambdaQueryWrapper<SmsSignature>()
                .eq(SmsSignature::getDeleted, 0)
                .orderByDesc(SmsSignature::getCreateTime);

        if (smsType != null) {
            wrapper.eq(SmsSignature::getSmsType, smsType);
        }
        if (channelCode != null) {
            wrapper.eq(SmsSignature::getChannelCode, channelCode);
        }
        if (status != null) {
            wrapper.eq(SmsSignature::getStatus, status);
        }

        return signatureMapper.selectPage(page, wrapper);
    }

    public List<SmsSignature> listAllSignatures() {
        return signatureMapper.selectList(
                new LambdaQueryWrapper<SmsSignature>()
                        .eq(SmsSignature::getStatus, 1)
                        .eq(SmsSignature::getDeleted, 0)
                        .orderByDesc(SmsSignature::getCreateTime)
        );
    }
}
