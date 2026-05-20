package com.econtract.service;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.econtract.common.BusinessException;
import com.econtract.entity.Contract;
import com.econtract.entity.ContractReview;
import com.econtract.mapper.ContractReviewMapper;
import com.econtract.mapper.ContractMapper;
import com.econtract.security.UserContext;
import lombok.extern.slf4j.Slf4j;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.io.File;
import java.io.IOException;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Service
public class ContractReviewService {

    @Value("${file.upload-path}")
    private String uploadPath;

    @Resource
    private ContractReviewMapper reviewMapper;

    @Resource
    private ContractMapper contractMapper;

    private static final Map<String, String> REQUIRED_CLAUSES = new LinkedHashMap<>();
    private static final List<Map<String, Object>> RISK_PATTERNS = new ArrayList<>();

    static {
        REQUIRED_CLAUSES.put("party_info", "当事人信息");
        REQUIRED_CLAUSES.put("subject", "合同标的");
        REQUIRED_CLAUSES.put("quantity", "数量条款");
        REQUIRED_CLAUSES.put("quality", "质量条款");
        REQUIRED_CLAUSES.put("price", "价款或报酬");
        REQUIRED_CLAUSES.put("performance", "履行期限、地点和方式");
        REQUIRED_CLAUSES.put("liability", "违约责任");
        REQUIRED_CLAUSES.put("dispute", "争议解决方式");

        RISK_PATTERNS.add(createRiskPattern("force_majeure", "不可抗力条款过于宽泛",
                Arrays.asList("不可抗力.*包括.*其他.*情况", "不可抗力.*不受限制", "一切不可抗力"),
                "HIGH", "不可抗力范围约定不明确，可能被滥用"));

        RISK_PATTERNS.add(createRiskPattern("disclaimer", "免责条款不合理",
                Arrays.asList("概不负责", "不承担任何责任", "无论何种情况", "全部免责"),
                "HIGH", "存在过度免责条款，可能损害您的权益"));

        RISK_PATTERNS.add(createRiskPattern("unilateral_termination", "单方解除权过于宽松",
                Arrays.asList("随时解除", "无需理由.*解除", "任意解除"),
                "MEDIUM", "对方拥有过于宽松的单方解除权"));

        RISK_PATTERNS.add(createRiskPattern("penalty_excessive", "违约金过高",
                Arrays.asList("违约金.*[3-9]0%", "违约金.*超过.*30%", "每日违约金.*千分之[五-九]"),
                "HIGH", "违约金超过合同标的30%，可能被认定为过高"));

        RISK_PATTERNS.add(createRiskPattern("jurisdiction", "管辖约定不利",
                Arrays.asList("由甲方住所地.*管辖", "由被告住所地.*管辖", "仲裁委员会.*甲方所在地"),
                "MEDIUM", "争议管辖地约定在对方所在地，增加维权成本"));

        RISK_PATTERNS.add(createRiskPattern("confidentiality", "保密条款过于苛刻",
                Arrays.asList("永久保密", "不得向任何人透露", "保密期限.*无限期"),
                "LOW", "保密义务过于严格，建议明确保密期限"));

        RISK_PATTERNS.add(createRiskPattern("ip_ownership", "知识产权归属不明确",
                Arrays.asList("知识产权.*归甲方所有", "所有知识产权.*单方所有", "本合同产生的知识产权.*全部归"),
                "MEDIUM", "知识产权归属可能不利于您方"));

        RISK_PATTERNS.add(createRiskPattern("unfair_payment", "付款条款不公",
                Arrays.asList("先付款.*后交货", "预付款.*100%", "全部款项.*预付"),
                "HIGH", "付款条件过于苛刻，存在资金风险"));

        RISK_PATTERNS.add(createRiskPattern("vague_description", "条款描述模糊",
                Arrays.asList("等等", "其他.*情况", "另行协商", "视情况而定"),
                "LOW", "条款描述模糊，容易产生争议"));

        RISK_PATTERNS.add(createRiskPattern("automatic_renewal", "自动续约条款",
                Arrays.asList("自动续约", "自动续期", "到期未提出异议.*视为同意"),
                "MEDIUM", "自动续约可能导致您在不知情的情况下续约"));
    }

    private static Map<String, Object> createRiskPattern(String code, String name,
                                                         List<String> patterns,
                                                         String level, String description) {
        Map<String, Object> pattern = new HashMap<>();
        pattern.put("code", code);
        pattern.put("name", name);
        pattern.put("patterns", patterns);
        pattern.put("level", level);
        pattern.put("description", description);
        return pattern;
    }

    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> reviewContract(Long contractId) {
        Contract contract = contractMapper.selectById(contractId);
        if (contract == null) {
            throw new BusinessException("合同不存在");
        }

        String text = extractTextFromPdf(contract.getFilePath());
        if (text == null || text.isEmpty()) {
            throw new BusinessException("无法读取合同内容，请确保PDF文件可正常读取");
        }

        List<Map<String, Object>> missingClauses = checkMissingClauses(text);
        List<Map<String, Object>> riskClauses = checkRiskClauses(text);

        int totalScore = calculateScore(missingClauses, riskClauses);
        String riskLevel = calculateRiskLevel(missingClauses, riskClauses);

        Map<String, Object> result = new HashMap<>();
        result.put("totalScore", totalScore);
        result.put("riskLevel", riskLevel);
        result.put("missingClauses", missingClauses);
        result.put("riskClauses", riskClauses);
        result.put("reviewTime", LocalDateTime.now());
        result.put("totalMissing", missingClauses.size());
        result.put("totalRisk", riskClauses.size());

        ContractReview review = new ContractReview();
        review.setContractId(contractId);
        review.setReviewResult(JSON.toJSONString(result));
        review.setMissingClauses(JSON.toJSONString(missingClauses));
        review.setRiskClauses(JSON.toJSONString(riskClauses));
        review.setRiskLevel(riskLevel);
        review.setTotalScore(totalScore);
        review.setReviewerId(UserContext.getCurrentUserId());
        review.setReviewTime(LocalDateTime.now());
        review.setStatus("REVIEWED");
        review.setCreateTime(LocalDateTime.now());

        QueryWrapper<ContractReview> wrapper = new QueryWrapper<>();
        wrapper.eq("contract_id", contractId);
        ContractReview existing = reviewMapper.selectOne(wrapper);
        if (existing != null) {
            review.setId(existing.getId());
            review.setUpdateTime(LocalDateTime.now());
            reviewMapper.updateById(review);
        } else {
            review.setUpdateTime(LocalDateTime.now());
            reviewMapper.insert(review);
        }

        contract.setReviewStatus("REVIEWED");
        contract.setRiskLevel(riskLevel);
        contract.setReviewScore(totalScore);
        contractMapper.updateById(contract);

        log.info("合同审查完成, contractId: {}, 评分: {}, 风险等级: {}", contractId, totalScore, riskLevel);

        return result;
    }

    public ContractReview getReviewByContractId(Long contractId) {
        QueryWrapper<ContractReview> wrapper = new QueryWrapper<>();
        wrapper.eq("contract_id", contractId);
        return reviewMapper.selectOne(wrapper);
    }

    private String extractTextFromPdf(String filePath) {
        try (PDDocument document = PDDocument.load(new File(filePath))) {
            PDFTextStripper stripper = new PDFTextStripper();
            return stripper.getText(document);
        } catch (IOException e) {
            log.error("读取PDF失败: {}", filePath, e);
            return null;
        }
    }

    private List<Map<String, Object>> checkMissingClauses(String text) {
        List<Map<String, Object>> missing = new ArrayList<>();

        for (Map.Entry<String, String> entry : REQUIRED_CLAUSES.entrySet()) {
            String code = entry.getKey();
            String name = entry.getValue();
            boolean found = checkClausePresence(text, code);

            if (!found) {
                Map<String, Object> clause = new HashMap<>();
                clause.put("code", code);
                clause.put("name", name);
                clause.put("severity", getMissingSeverity(code));
                clause.put("suggestion", getMissingSuggestion(code));
                missing.add(clause);
            }
        }

        return missing;
    }

    private boolean checkClausePresence(String text, String clauseCode) {
        String lowerText = text.toLowerCase();
        switch (clauseCode) {
            case "party_info":
                return containsAny(lowerText, "甲方", "乙方", "买方", "卖方", "出租人", "承租人",
                        "借款方", "贷款方", "甲方.*：", "乙方.*：", "甲方:", "乙方:");
            case "subject":
                return containsAny(lowerText, "标的", "货物名称", "服务内容", "项目名称",
                        "第一条.*标的", "产品名称", "工程名称");
            case "quantity":
                return containsAny(lowerText, "数量", "共计", "总计", "共.*件", "共.*套",
                        "共.*台", "共.*个", "[0-9]+\\s*(件|套|台|个|吨|千克|米|平方米)");
            case "quality":
                return containsAny(lowerText, "质量", "标准", "合格", "验收", "技术要求",
                        "质量标准", "验收标准", "符合.*标准");
            case "price":
                return containsAny(lowerText, "价款", "报酬", "金额", "价格", "费用",
                        "人民币.*元", "￥", "合计.*元", "总价", "单价");
            case "performance":
                return containsAny(lowerText, "履行期限", "履行地点", "履行方式",
                        "交货时间", "交付时间", "付款时间", "签订之日起", "年.*月.*日前",
                        "交货地点", "交付地点");
            case "liability":
                return containsAny(lowerText, "违约责任", "违约金", "赔偿损失", "违约方",
                        "如违约", "一方违约", "承担违约责任");
            case "dispute":
                return containsAny(lowerText, "争议解决", "诉讼", "仲裁", "人民法院",
                        "仲裁委员会", "协商不成", "向.*起诉", "由.*管辖");
            default:
                return true;
        }
    }

    private String getMissingSeverity(String code) {
        switch (code) {
            case "party_info":
            case "subject":
            case "price":
            case "liability":
                return "HIGH";
            case "quantity":
            case "performance":
            case "dispute":
                return "MEDIUM";
            case "quality":
                return "LOW";
            default:
                return "LOW";
        }
    }

    private String getMissingSuggestion(String code) {
        switch (code) {
            case "party_info":
                return "建议补充完整的当事人信息，包括姓名/名称、地址、联系方式、法定代表人等";
            case "subject":
                return "建议明确约定合同标的，包括名称、规格、型号等详细信息";
            case "quantity":
                return "建议明确约定数量、计量单位和计算方法";
            case "quality":
                return "建议明确质量标准、验收程序和质量保证期限";
            case "price":
                return "建议明确约定价款金额、支付方式、支付时间和币种";
            case "performance":
                return "建议明确履行的期限、地点、方式和运输责任";
            case "liability":
                return "建议明确违约情形、违约金计算方式和损失赔偿范围";
            case "dispute":
                return "建议明确争议解决方式（诉讼/仲裁）和管辖机构";
            default:
                return "建议补充完善相关条款";
        }
    }

    private List<Map<String, Object>> checkRiskClauses(String text) {
        List<Map<String, Object>> risks = new ArrayList<>();
        String lowerText = text.toLowerCase();

        for (Map<String, Object> patternConfig : RISK_PATTERNS) {
            String code = (String) patternConfig.get("code");
            String name = (String) patternConfig.get("name");
            @SuppressWarnings("unchecked")
            List<String> patterns = (List<String>) patternConfig.get("patterns");
            String level = (String) patternConfig.get("level");
            String description = (String) patternConfig.get("description");

            List<String> matchedTexts = new ArrayList<>();
            for (String pattern : patterns) {
                try {
                    Pattern p = Pattern.compile(pattern, Pattern.CASE_INSENSITIVE);
                    Matcher m = p.matcher(text);
                    while (m.find()) {
                        String matched = m.group();
                        if (matched.length() > 50) {
                            matched = matched.substring(0, 50) + "...";
                        }
                        matchedTexts.add(matched);
                    }
                } catch (Exception e) {
                    log.warn("正则匹配失败: {}", pattern, e);
                }
            }

            if (!matchedTexts.isEmpty()) {
                Map<String, Object> risk = new HashMap<>();
                risk.put("code", code);
                risk.put("name", name);
                risk.put("level", level);
                risk.put("description", description);
                risk.put("matchedTexts", matchedTexts);
                risk.put("suggestion", getRiskSuggestion(code));
                risks.add(risk);
            }
        }

        checkPenaltyAmount(text, risks);

        return risks;
    }

    private void checkPenaltyAmount(String text, List<Map<String, Object>> risks) {
        try {
            BigDecimal totalAmount = extractTotalAmount(text);
            if (totalAmount == null || totalAmount.compareTo(BigDecimal.ZERO) <= 0) {
                return;
            }

            Pattern penaltyPattern = Pattern.compile(
                    "违约金.*?(\\d+(?:\\.\\d+)?)\\s*%|每日.*?(\\d+(?:\\.\\d+)?)\\s*%",
                    Pattern.CASE_INSENSITIVE);
            Matcher matcher = penaltyPattern.matcher(text);

            while (matcher.find()) {
                String percentStr = matcher.group(1) != null ? matcher.group(1) : matcher.group(2);
                BigDecimal percent = new BigDecimal(percentStr);

                if (percent.compareTo(new BigDecimal("30")) > 0) {
                    Map<String, Object> risk = new HashMap<>();
                    risk.put("code", "penalty_excessive_percent");
                    risk.put("name", "违约金比例过高");
                    risk.put("level", "HIGH");
                    risk.put("description", String.format(
                            "违约金比例为%s%%，超过法律保护的30%%上限，可能被法院调低", percent));
                    risk.put("matchedTexts", Collections.singletonList(matcher.group()));
                    risk.put("suggestion", "建议将违约金调整至合同金额的30%以内");
                    risks.add(risk);
                }

                if (percent.compareTo(new BigDecimal("5")) > 0) {
                    BigDecimal annualRate = percent.multiply(new BigDecimal("365"));
                    if (annualRate.compareTo(new BigDecimal("24")) > 0) {
                        Map<String, Object> risk = new HashMap<>();
                        risk.put("code", "daily_penalty_excessive");
                        risk.put("name", "每日违约金过高");
                        risk.put("level", "HIGH");
                        risk.put("description", String.format(
                                "每日违约金%s%%，年化利率约%s%%，超过法定24%%上限", percent, annualRate));
                        risk.put("matchedTexts", Collections.singletonList(matcher.group()));
                        risk.put("suggestion", "建议降低每日违约金比例，年化不超过24%");
                        risks.add(risk);
                    }
                }
            }
        } catch (Exception e) {
            log.warn("违约金金额检查失败", e);
        }
    }

    private BigDecimal extractTotalAmount(String text) {
        try {
            Pattern amountPattern = Pattern.compile(
                    "(?:合同|总)金额[^\\d]*?(\\d+(?:,\\d+)*(?:\\.\\d+)?)|(?:总计|合计)[^\\d]*?(\\d+(?:,\\d+)*(?:\\.\\d+)?)",
                    Pattern.CASE_INSENSITIVE);
            Matcher matcher = amountPattern.matcher(text);
            if (matcher.find()) {
                String amountStr = matcher.group(1) != null ? matcher.group(1) : matcher.group(2);
                amountStr = amountStr.replace(",", "");
                return new BigDecimal(amountStr);
            }
        } catch (Exception e) {
            log.warn("提取合同金额失败", e);
        }
        return null;
    }

    private String getRiskSuggestion(String code) {
        switch (code) {
            case "force_majeure":
                return "建议明确列举不可抗力的具体情形，避免使用过于宽泛的表述";
            case "disclaimer":
                return "建议删除或修改过度免责条款，公平约定双方责任";
            case "unilateral_termination":
                return "建议协商修改解除条件，约定合理的通知期和补偿方式";
            case "penalty_excessive":
                return "建议将违约金调整至合理范围（一般不超过合同金额30%）";
            case "jurisdiction":
                return "建议协商选择双方所在地或合同履行地作为管辖地";
            case "confidentiality":
                return "建议明确保密期限（一般2-5年）和保密例外情形";
            case "ip_ownership":
                return "建议根据实际贡献合理约定知识产权的归属和使用范围";
            case "unfair_payment":
                return "建议采用分期付款方式，降低预付款比例";
            case "vague_description":
                return "建议将模糊表述具体化，明确双方权利义务";
            case "automatic_renewal":
                return "建议增加提前通知期限，或删除自动续约条款改为手动续约";
            default:
                return "建议咨询专业律师评估相关风险";
        }
    }

    private int calculateScore(List<Map<String, Object>> missing, List<Map<String, Object>> risks) {
        int score = 100;

        for (Map<String, Object> clause : missing) {
            String severity = (String) clause.get("severity");
            switch (severity) {
                case "HIGH":
                    score -= 10;
                    break;
                case "MEDIUM":
                    score -= 6;
                    break;
                case "LOW":
                    score -= 3;
                    break;
            }
        }

        for (Map<String, Object> risk : risks) {
            String level = (String) risk.get("level");
            switch (level) {
                case "HIGH":
                    score -= 8;
                    break;
                case "MEDIUM":
                    score -= 5;
                    break;
                case "LOW":
                    score -= 2;
                    break;
            }
        }

        return Math.max(0, Math.min(100, score));
    }

    private String calculateRiskLevel(List<Map<String, Object>> missing, List<Map<String, Object>> risks) {
        long highRiskCount = risks.stream()
                .filter(r -> "HIGH".equals(r.get("level")))
                .count();
        long highMissingCount = missing.stream()
                .filter(c -> "HIGH".equals(c.get("severity")))
                .count();

        if (highRiskCount >= 2 || highMissingCount >= 2) {
            return "HIGH";
        } else if (highRiskCount >= 1 || highMissingCount >= 1 || risks.size() >= 3) {
            return "MEDIUM";
        } else {
            return "LOW";
        }
    }

    private boolean containsAny(String text, String... keywords) {
        for (String keyword : keywords) {
            if (text.contains(keyword.toLowerCase())) {
                return true;
            }
        }
        return false;
    }
}
