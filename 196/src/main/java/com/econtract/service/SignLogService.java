package com.econtract.service;

import com.econtract.entity.SignLog;
import com.econtract.mapper.SignLogMapper;
import com.econtract.util.IpUtil;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import java.time.LocalDateTime;

@Service
public class SignLogService {

    @Resource
    private SignLogMapper signLogMapper;

    @Resource
    private HttpServletRequest request;

    @Async
    public void addLog(Long contractId, Long signerId, String operation, String detail) {
        SignLog log = new SignLog();
        log.setContractId(contractId);
        log.setSignerId(signerId);
        log.setOperation(operation);
        log.setDetail(detail);
        log.setIpAddress(IpUtil.getIpAddr(request));
        log.setUserAgent(IpUtil.getUserAgent(request));
        log.setCreateTime(LocalDateTime.now());
        signLogMapper.insert(log);
    }
}
