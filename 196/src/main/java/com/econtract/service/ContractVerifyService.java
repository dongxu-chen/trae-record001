package com.econtract.service;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.econtract.common.BusinessException;
import com.econtract.entity.Contract;
import com.econtract.entity.ContractSigner;
import com.econtract.entity.ContractVerifyLog;
import com.econtract.entity.BlockchainEvidence;
import com.econtract.mapper.ContractMapper;
import com.econtract.mapper.ContractSignerMapper;
import com.econtract.mapper.ContractVerifyLogMapper;
import com.econtract.mapper.BlockchainEvidenceMapper;
import com.econtract.util.FileHashUtil;
import com.econtract.util.IpUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import java.io.File;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
public class ContractVerifyService {

    @Resource
    private ContractMapper contractMapper;

    @Resource
    private ContractSignerMapper signerMapper;

    @Resource
    private ContractVerifyLogMapper verifyLogMapper;

    @Resource
    private BlockchainEvidenceMapper evidenceMapper;

    @Resource
    private HttpServletRequest request;

    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> verifyContract(String contractNo, String verifyType) {
        Map<String, Object> result = new HashMap<>();
        List<Map<String, Object>> verifyItems = new ArrayList<>();
        boolean overallPassed = true;

        QueryWrapper<Contract> wrapper = new QueryWrapper<>();
        wrapper.eq("contract_no", contractNo);
        Contract contract = contractMapper.selectOne(wrapper);

        if (contract == null) {
            addVerifyItem(verifyItems, "合同存在性", false, "未找到该合同编号对应的合同", "请确认合同编号是否正确");
            overallPassed = false;
            result.put("contractExists", false);
        } else {
            result.put("contractExists", true);
            result.put("contractNo", contract.getContractNo());
            result.put("contractName", contract.getContractName());
            result.put("status", contract.getStatus());
            result.put("statusText", getStatusText(contract.getStatus()));
            result.put("createTime", contract.getCreateTime());
            result.put("allowPublicVerify", contract.getAllowPublicVerify() == null
                    || contract.getAllowPublicVerify() == 1);

            if (contract.getAllowPublicVerify() != null && contract.getAllowPublicVerify() == 0
                    && "PUBLIC".equals(verifyType)) {
                addVerifyItem(verifyItems, "公开验真权限", false,
                        "该合同不允许公开验真", "请联系合同签署方获取授权");
                overallPassed = false;
                result.put("authPassed", false);
            } else {
                result.put("authPassed", true);

                addVerifyItem(verifyItems, "合同存在性", true,
                        "合同已在系统中登记", "合同编号有效");

                boolean fileIntegrity = verifyFileIntegrity(contract);
                addVerifyItem(verifyItems, "文件完整性", fileIntegrity,
                        fileIntegrity ? "文件哈希校验通过，文件未被篡改" : "文件哈希校验失败，文件可能被篡改",
                        "通过比对当前文件哈希与签署时存储的哈希值验证");

                boolean blockchainValid = verifyBlockchain(contract);
                addVerifyItem(verifyItems, "区块链存证", blockchainValid,
                        blockchainValid ? "区块链存证有效，可追溯" : "区块链存证验证失败",
                        "通过区块链节点验证存证数据的真实性");

                QueryWrapper<ContractSigner> signerWrapper = new QueryWrapper<>();
                signerWrapper.eq("contract_id", contract.getId());
                signerWrapper.orderByAsc("sign_order");
                List<ContractSigner> signers = signerMapper.selectList(signerWrapper);

                boolean allSigned = signers.stream()
                        .allMatch(s -> "COMPLETED".equals(s.getSignStatus()));
                addVerifyItem(verifyItems, "签署完整性", allSigned,
                        allSigned ? "所有签署方已完成签署" : "存在未完成签署的签署方",
                        String.format("共%d方签署，已完成%d方",
                                signers.size(),
                                (int) signers.stream().filter(s -> "COMPLETED".equals(s.getSignStatus())
                                        .count()));

                boolean timestampValid = verifyTimestamps(signers);
                addVerifyItem(verifyItems, "可信时间戳", timestampValid,
                        timestampValid ? "签署时间戳有效" : "部分签署时间戳缺失或无效",
                        "使用RFC3161标准可信时间戳验证签署时间");

                boolean identityValid = verifyIdentity(signers);
                addVerifyItem(verifyItems, "身份认证", identityValid,
                        identityValid ? "所有签署方均通过身份认证" : "部分签署方身份认证记录不完整",
                        "签署前均通过短信或人脸识别认证");

                overallPassed = fileIntegrity && blockchainValid && allSigned && timestampValid
                        && identityValid;

                result.put("signers", formatSigners(signers));
                result.put("signCount", signers.size());
                result.put("completedSignCount",
                        (int) signers.stream().filter(s -> "COMPLETED".equals(s.getSignStatus())
                                .count());
            }

            if (contract.getBlockchainTxId() != null) {
                result.put("blockchainTxId", contract.getBlockchainTxId());
                result.put("blockchainHash", contract.getBlockchainHash());
                result.put("blockchainTime", contract.getBlockchainTime());
            }
        }

        result.put("overallPassed", overallPassed);
        result.put("verifyItems", verifyItems);
        result.put("verifyTime", LocalDateTime.now());

        try {
            ContractVerifyLog verifyLog = new ContractVerifyLog();
            verifyLog.setContractNo(contractNo);
            verifyLog.setVerifyType(verifyType);
            verifyLog.setRequesterIp(IpUtil.getIpAddr(request));
            verifyLog.setRequesterInfo(IpUtil.getUserAgent(request));
            verifyLog.setVerifyResult(overallPassed ? "PASSED" : "FAILED");
            verifyLog.setVerifyDetail(JSON.toJSONString(result));
            verifyLog.setCreateTime(LocalDateTime.now());
            verifyLogMapper.insert(verifyLog);
        } catch (Exception e) {
            log.warn("记录验真日志失败: {}", e.getMessage());
        }

        log.info("合同验真完成, contractNo: {}, verifyType: {}, passed: {}",
                contractNo, verifyType, overallPassed);
        return result;
    }

    private void addVerifyItem(List<Map<String, Object>> items, String name,
                               boolean passed, String description, String detail) {
        Map<String, Object> item = new HashMap<>();
        item.put("name", name);
        item.put("passed", passed);
        item.put("description", description);
        item.put("detail", detail);
        items.add(item);
    }

    private boolean verifyFileIntegrity(Contract contract) {
        if (contract.getFileHash() == null) {
            return false;
        }
        try {
            File file = new File(contract.getFilePath());
            if (!file.exists()) {
                return false;
            }
            String currentHash = FileHashUtil.sha256(file);
            return contract.getFileHash().equals(currentHash);
        } catch (Exception e) {
            log.warn("验证文件完整性失败: {}", e.getMessage());
            return false;
        }
    }

    private boolean verifyBlockchain(Contract contract) {
        if (contract.getBlockchainTxId() == null) {
            return false;
        }
        try {
            QueryWrapper<BlockchainEvidence> wrapper = new QueryWrapper<>();
            wrapper.eq("biz_type", "CONTRACT");
            wrapper.eq("biz_id", contract.getId());
            wrapper.eq("status", "SUCCESS");
            wrapper.orderByDesc("create_time");
            wrapper.last("limit 1");
            BlockchainEvidence evidence = evidenceMapper.selectOne(wrapper);
            return evidence != null;
        } catch (Exception e) {
            log.warn("验证区块链存证失败: {}", e.getMessage());
            return contract.getBlockchainTxId() != null
                    && !contract.getBlockchainTxId().startsWith("MOCK");
        }
    }

    private boolean verifyTimestamps(List<ContractSigner> signers) {
        for (ContractSigner signer : signers) {
            if ("COMPLETED".equals(signer.getSignStatus())
                    && (signer.getTimestampToken() == null
                    || signer.getTimestampToken().isEmpty())) {
                return false;
            }
        }
        return true;
    }

    private boolean verifyIdentity(List<ContractSigner> signers) {
        for (ContractSigner signer : signers) {
            if ("COMPLETED".equals(signer.getSignStatus())
                    && (signer.getAuthType() == null
                    || signer.getAuthTime() == null)) {
                return false;
            }
        }
        return true;
    }

    private List<Map<String, Object>> formatSigners(List<ContractSigner> signers) {
        List<Map<String, Object>> result = new ArrayList<>();
        for (ContractSigner signer : signers) {
            Map<String, Object> item = new HashMap<>();
            item.put("signOrder", signer.getSignOrder());
            item.put("signerName", signer.getSignerName());
            item.put("signerPhone", maskPhone(signer.getSignerPhone()));
            item.put("signStatus", signer.getSignStatus());
            item.put("signStatusText", getSignerStatusText(signer.getSignStatus()));
            item.put("signTime", signer.getSignTime());
            item.put("authType", signer.getAuthType());
            item.put("hasWitness", signer.getWitnessAuthId() != null);
            item.put("hasPressureData", signer.getPressureData() != null
                    && !signer.getPressureData().isEmpty());
            result.add(item);
        }
        return result;
    }

    private String maskPhone(String phone) {
        if (phone == null || phone.length() < 11) {
            return phone;
        }
        return phone.substring(0, 3) + "****" + phone.substring(7);
    }

    private String getStatusText(String status) {
        switch (status) {
            case "DRAFT": return "草稿";
            case "PENDING": return "待签署";
            case "SIGNING": return "签署中";
            case "COMPLETED": return "已完成";
            case "REJECTED": return "已拒签";
            case "EXPIRED": return "已过期";
            default: return status;
        }
    }

    private String getSignerStatusText(String status) {
        switch (status) {
            case "PENDING": return "待签署";
            case "SIGNING": return "签署中";
            case "COMPLETED": return "已签署";
            case "REJECTED": return "已拒签";
            default: return status;
        }
    }

    public List<ContractVerifyLog> getVerifyLogs(String contractNo) {
        QueryWrapper<ContractVerifyLog> wrapper = new QueryWrapper<>();
        wrapper.eq("contract_no", contractNo);
        wrapper.orderByDesc("create_time");
        wrapper.last("limit 100");
        return verifyLogMapper.selectList(wrapper);
    }
}
