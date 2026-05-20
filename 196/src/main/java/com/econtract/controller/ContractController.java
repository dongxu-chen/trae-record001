package com.econtract.controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.econtract.common.Result;
import com.econtract.dto.ContractCreateDTO;
import com.econtract.dto.SignDTO;
import com.econtract.entity.Contract;
import com.econtract.entity.ContractSigner;
import com.econtract.service.ContractService;
import com.econtract.service.PdfService;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/contract")
public class ContractController {

    @Resource
    private ContractService contractService;

    @Resource
    private PdfService pdfService;

    @Resource
    private SignRemindService remindService;

    @GetMapping("/page")
    public Result<Page<Contract>> getContractPage(
            @RequestParam(defaultValue = "1") int pageNum,
            @RequestParam(defaultValue = "10") int pageSize,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String contractName) {
        return Result.success(contractService.getContractPage(pageNum, pageSize, status, contractName));
    }

    @GetMapping("/pending")
    public Result<Page<Contract>> getPendingSignPage(
            @RequestParam(defaultValue = "1") int pageNum,
            @RequestParam(defaultValue = "10") int pageSize) {
        return Result.success(contractService.getPendingSignPage(pageNum, pageSize));
    }

    @GetMapping("/{id}")
    public Result<Map<String, Object>> getContractDetail(@PathVariable Long id) {
        Contract contract = contractService.getContractById(id);
        List<ContractSigner> signers = contractService.getContractSigners(id);
        Map<String, Object> result = new HashMap<>();
        result.put("contract", contract);
        result.put("signers", signers);
        return Result.success(result);
    }

    @PostMapping
    public Result<Contract> createContract(
            @RequestPart("contract") @Validated ContractCreateDTO createDTO,
            @RequestPart(value = "file", required = false) MultipartFile file) throws IOException {
        return Result.success(contractService.createContract(createDTO, file));
    }

    @PostMapping("/sign")
    public Result<Void> signContract(@Validated @RequestBody SignDTO signDTO) throws Exception {
        contractService.signContract(signDTO);
        return Result.success("签署成功", null);
    }

    @PostMapping("/reject")
    public Result<Void> rejectSign(@RequestParam Long contractId, @RequestParam String reason) {
        contractService.rejectSign(contractId, reason);
        return Result.success("已拒签", null);
    }

    @PostMapping("/remind/{contractId}")
    public Result<Void> remindSigner(@PathVariable Long contractId) {
        remindService.remindSigner(contractId);
        return Result.success("催办成功", null);
    }

    @GetMapping("/remind/count/{contractId}")
    public Result<Integer> getRemainRemindCount(@PathVariable Long contractId) {
        return Result.success(remindService.getRemainRemindCount(contractId));
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteContract(@PathVariable Long id) {
        contractService.deleteContract(id);
        return Result.success();
    }

    @GetMapping("/download/{id}")
    public ResponseEntity<byte[]> downloadContract(@PathVariable Long id) throws IOException {
        Contract contract = contractService.getContractById(id);
        byte[] bytes = pdfService.getFileBytes(contract.getFilePath());
        String fileName = URLEncoder.encode(contract.getFileName(), StandardCharsets.UTF_8.name());
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename*=UTF-8''" + fileName)
                .contentType(MediaType.APPLICATION_PDF)
                .body(bytes);
    }
}
