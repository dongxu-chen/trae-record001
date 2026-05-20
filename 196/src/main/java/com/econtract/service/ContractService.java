package com.econtract.service;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.econtract.common.BusinessException;
import com.econtract.common.ResultCode;
import com.econtract.dto.ContractCreateDTO;
import com.econtract.dto.SignDTO;
import com.econtract.dto.SignerDTO;
import com.econtract.entity.Contract;
import com.econtract.entity.ContractSigner;
import com.econtract.entity.ContractTemplate;
import com.econtract.entity.User;
import com.econtract.mapper.ContractMapper;
import com.econtract.mapper.ContractSignerMapper;
import com.econtract.mapper.UserMapper;
import com.econtract.security.UserContext;
import com.econtract.util.ContractNoGenerator;
import com.econtract.util.FileHashUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import java.io.File;
import java.io.IOException;
import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
public class ContractService {

    @Value("${file.upload-path}")
    private String uploadPath;

    @Resource
    private ContractMapper contractMapper;

    @Resource
    private ContractSignerMapper contractSignerMapper;

    @Resource
    private ContractTemplateService templateService;

    @Resource
    private UserMapper userMapper;

    @Resource
    private PdfService pdfService;

    @Resource
    private SmsService smsService;

    @Resource
    private FaceService faceService;

    @Resource
    private TimestampService timestampService;

    @Resource
    private BlockchainService blockchainService;

    @Resource
    private SignLogService signLogService;

    @Resource
    private HttpServletRequest request;

    public Page<Contract> getContractPage(int pageNum, int pageSize, String status, String contractName) {
        Page<Contract> page = new Page<>(pageNum, pageSize);
        QueryWrapper<Contract> wrapper = new QueryWrapper<>();
        if (status != null && !status.isEmpty()) {
            wrapper.eq("status", status);
        }
        if (contractName != null && !contractName.isEmpty()) {
            wrapper.like("contract_name", contractName);
        }
        wrapper.eq("creator_id", UserContext.getCurrentUserId());
        wrapper.orderByDesc("create_time");
        return contractMapper.selectPage(page, wrapper);
    }

    public Page<Contract> getPendingSignPage(int pageNum, int pageSize) {
        Page<Contract> page = new Page<>(pageNum, pageSize);
        Long userId = UserContext.getCurrentUserId();
        QueryWrapper<Contract> wrapper = new QueryWrapper<>();
        wrapper.inSql("id", "SELECT contract_id FROM contract_signer WHERE signer_id = " + userId
                + " AND sign_status IN ('PENDING', 'SIGNING') AND deleted = 0");
        wrapper.orderByDesc("create_time");
        return contractMapper.selectPage(page, wrapper);
    }

    public Contract getContractById(Long id) {
        Contract contract = contractMapper.selectById(id);
        if (contract == null) {
            throw new BusinessException(ResultCode.CONTRACT_NOT_FOUND);
        }
        return contract;
    }

    public List<ContractSigner> getContractSigners(Long contractId) {
        QueryWrapper<ContractSigner> wrapper = new QueryWrapper<>();
        wrapper.eq("contract_id", contractId);
        wrapper.orderByAsc("sign_order");
        return contractSignerMapper.selectList(wrapper);
    }

    @Transactional(rollbackFor = Exception.class)
    public Contract createContract(ContractCreateDTO createDTO, MultipartFile file) throws IOException {
        Long userId = UserContext.getCurrentUserId();
        User user = userMapper.selectById(userId);
        if (user.getIdentityVerified() == 0) {
            throw new BusinessException("请先完成实名认证");
        }

        String filePath;
        String fileName;
        Long fileSize;
        String formData = createDTO.getFormData();

        if (createDTO.getTemplateId() != null) {
            ContractTemplate template = templateService.getTemplateById(createDTO.getTemplateId());
            filePath = pdfService.fillForm(template.getFilePath(), formData, template.getFields());
            fileName = template.getFileName();
            fileSize = new File(filePath).length();
        } else if (file != null && !file.isEmpty()) {
            fileName = file.getOriginalFilename();
            fileSize = file.getSize();
            File dir = new File(uploadPath);
            if (!dir.exists()) {
                dir.mkdirs();
            }
            String uuid = UUID.randomUUID().toString().replace("-", "");
            String ext = fileName.substring(fileName.lastIndexOf("."));
            filePath = uploadPath + uuid + ext;
            file.transferTo(new File(filePath));
        } else {
            throw new BusinessException("请选择模板或上传合同文件");
        }

        String fileHash = FileHashUtil.sha256(new File(filePath));

        Contract contract = new Contract();
        contract.setContractNo(ContractNoGenerator.generate());
        contract.setContractName(createDTO.getContractName());
        contract.setTemplateId(createDTO.getTemplateId());
        contract.setFilePath(filePath);
        contract.setFileName(fileName);
        contract.setFileSize(fileSize);
        contract.setFileHash(fileHash);
        contract.setFormData(formData);
        contract.setStatus("PENDING");
        contract.setCreatorId(userId);
        contract.setExpireTime(createDTO.getExpireTime());
        contractMapper.insert(contract);

        for (SignerDTO signerDTO : createDTO.getSigners()) {
            ContractSigner signer = new ContractSigner();
            signer.setContractId(contract.getId());
            signer.setSignerId(signerDTO.getSignerId());
            signer.setSignerName(signerDTO.getSignerName());
            signer.setSignerPhone(signerDTO.getSignerPhone());
            signer.setSignOrder(signerDTO.getSignOrder());
            signer.setSignStatus("PENDING");
            signer.setSignPosition(signerDTO.getSignPosition());
            contractSignerMapper.insert(signer);
        }

        updateContractStatus(contract.getId());
        signLogService.addLog(contract.getId(), userId, "CREATE", "创建合同");

        return contract;
    }

    @Transactional(rollbackFor = Exception.class)
    public void signContract(SignDTO signDTO) throws Exception {
        Long userId = UserContext.getCurrentUserId();
        Contract contract = getContractById(signDTO.getContractId());

        if (!"SIGNING".equals(contract.getStatus()) && !"PENDING".equals(contract.getStatus())) {
            throw new BusinessException(ResultCode.CONTRACT_STATUS_ERROR);
        }

        QueryWrapper<ContractSigner> wrapper = new QueryWrapper<>();
        wrapper.eq("contract_id", contract.getId());
        wrapper.eq("signer_id", userId);
        ContractSigner currentSigner = contractSignerMapper.selectOne(wrapper);

        if (currentSigner == null) {
            throw new BusinessException("您不是该合同的签署人");
        }

        if ("COMPLETED".equals(currentSigner.getSignStatus())) {
            throw new BusinessException(ResultCode.CONTRACT_ALREADY_SIGNED);
        }

        List<ContractSigner> allSigners = getContractSigners(contract.getId());
        int maxCompletedOrder = allSigners.stream()
                .filter(s -> "COMPLETED".equals(s.getSignStatus()))
                .map(ContractSigner::getSignOrder)
                .max(Comparator.naturalOrder())
                .orElse(0);

        if (currentSigner.getSignOrder() != maxCompletedOrder + 1) {
            throw new BusinessException(ResultCode.CONTRACT_NOT_YOUR_TURN);
        }

        if ("SMS".equals(signDTO.getAuthType())) {
            smsService.verifyCode(currentSigner.getSignerPhone(), signDTO.getSmsCode(), "SIGN");
            currentSigner.setAuthType("SMS");
            currentSigner.setAuthTime(LocalDateTime.now());
        } else if ("FACE".equals(signDTO.getAuthType())) {
            faceService.verifyFace(userId, "SIGN", signDTO.getFaceImage());
            currentSigner.setAuthType("FACE");
            currentSigner.setAuthTime(LocalDateTime.now());
        }

        String signedPath = pdfService.addSignature(contract.getFilePath(),
                signDTO.getSignatureImage(),
                signDTO.getSignPosition() != null ? signDTO.getSignPosition() : currentSigner.getSignPosition());

        String signedFileHash = FileHashUtil.sha256(new File(signedPath));
        String timestampToken = timestampService.getTimestamp(signedFileHash.getBytes());

        currentSigner.setSignStatus("COMPLETED");
        currentSigner.setSignTime(LocalDateTime.now());
        currentSigner.setSignatureImage(signDTO.getSignatureImage());
        currentSigner.setSignatureType(signDTO.getSignatureType());
        currentSigner.setSignPosition(signDTO.getSignPosition());
        currentSigner.setSignIp(com.econtract.util.IpUtil.getIpAddr(request));
        currentSigner.setSignDevice(com.econtract.util.IpUtil.getUserAgent(request));
        currentSigner.setTimestampToken(timestampToken);
        currentSigner.setSignNote(signDTO.getSignNote());
        contractSignerMapper.updateById(currentSigner);

        contract.setFilePath(signedPath);
        contract.setFileHash(signedFileHash);
        contractMapper.updateById(contract);

        updateContractStatus(contract.getId());
        signLogService.addLog(contract.getId(), userId, "SIGN",
                "签署合同，签名类型：" + signDTO.getSignatureType() + "，认证方式：" + signDTO.getAuthType());

        contract = getContractById(contract.getId());
        if ("COMPLETED".equals(contract.getStatus())) {
            blockchainService.asyncSaveEvidence("CONTRACT", contract.getId(), contract);
        }

        blockchainService.asyncSaveEvidence("SIGN", currentSigner.getId(), currentSigner);
    }

    @Transactional(rollbackFor = Exception.class)
    public void rejectSign(Long contractId, String reason) {
        Long userId = UserContext.getCurrentUserId();
        Contract contract = getContractById(contractId);

        QueryWrapper<ContractSigner> wrapper = new QueryWrapper<>();
        wrapper.eq("contract_id", contractId);
        wrapper.eq("signer_id", userId);
        ContractSigner currentSigner = contractSignerMapper.selectOne(wrapper);

        if (currentSigner == null) {
            throw new BusinessException("您不是该合同的签署人");
        }

        if ("COMPLETED".equals(currentSigner.getSignStatus())) {
            throw new BusinessException(ResultCode.CONTRACT_ALREADY_SIGNED);
        }

        currentSigner.setSignStatus("REJECTED");
        currentSigner.setSignNote(reason);
        currentSigner.setSignTime(LocalDateTime.now());
        contractSignerMapper.updateById(currentSigner);

        contract.setStatus("REJECTED");
        contractMapper.updateById(contract);

        signLogService.addLog(contractId, userId, "REJECT", "拒签合同，原因：" + reason);
    }

    private void updateContractStatus(Long contractId) {
        List<ContractSigner> signers = getContractSigners(contractId);
        boolean allCompleted = signers.stream().allMatch(s -> "COMPLETED".equals(s.getSignStatus()));
        boolean anyRejected = signers.stream().anyMatch(s -> "REJECTED".equals(s.getSignStatus()));
        boolean anySigning = signers.stream().anyMatch(s -> "SIGNING".equals(s.getSignStatus()));

        Contract contract = new Contract();
        contract.setId(contractId);

        if (anyRejected) {
            contract.setStatus("REJECTED");
        } else if (allCompleted) {
            contract.setStatus("COMPLETED");
        } else if (anySigning) {
            contract.setStatus("SIGNING");
        } else {
            contract.setStatus("PENDING");
        }

        contractMapper.updateById(contract);

        if ("PENDING".equals(contract.getStatus()) || "SIGNING".equals(contract.getStatus())) {
            notifyNextSigner(contractId);
        }
    }

    private void notifyNextSigner(Long contractId) {
        List<ContractSigner> signers = getContractSigners(contractId);
        for (ContractSigner signer : signers) {
            if ("PENDING".equals(signer.getSignStatus())) {
                signer.setSignStatus("SIGNING");
                signer.setSignDeadline(LocalDateTime.now().plusHours(timeoutHours));
                contractSignerMapper.updateById(signer);

                try {
                    smsService.sendSms(signer.getSignerPhone(), "SIGN_NOTIFY");
                } catch (Exception e) {
                    log.warn("发送签署通知短信失败: {}", e.getMessage());
                }
                break;
            }
        }
    }

    public void deleteContract(Long id) {
        Contract contract = getContractById(id);
        if (!contract.getCreatorId().equals(UserContext.getCurrentUserId())) {
            throw new BusinessException("无权限删除此合同");
        }
        if (!"DRAFT".equals(contract.getStatus()) && !"PENDING".equals(contract.getStatus())) {
            throw new BusinessException("只能删除草稿或待签署状态的合同");
        }
        contractMapper.deleteById(id);
    }
}
