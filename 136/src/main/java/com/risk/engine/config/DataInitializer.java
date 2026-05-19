package com.risk.engine.config;

import com.risk.engine.entity.EasyRule;
import com.risk.engine.entity.RiskList;
import com.risk.engine.repository.EasyRuleRepository;
import com.risk.engine.repository.RiskListRepository;
import com.risk.engine.rules.DynamicRuleEngine;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class DataInitializer implements CommandLineRunner {

    @Autowired
    private EasyRuleRepository easyRuleRepository;

    @Autowired
    private RiskListRepository riskListRepository;

    @Autowired
    private DynamicRuleEngine ruleEngine;

    @Override
    public void run(String... args) throws Exception {
        log.info("初始化测试数据...");
        
        initEasyRules();
        initTestLists();
        
        log.info("测试数据初始化完成");
    }

    private void initEasyRules() {
        if (easyRuleRepository.count() > 0) {
            return;
        }
        
        EasyRule rule1 = new EasyRule();
        rule1.setRuleCode("HIGH_AMOUNT_CHECK");
        rule1.setRuleName("高金额交易检查");
        rule1.setDescription("订单金额超过阈值时增加风险分数");
        rule1.setScene("PAYMENT");
        rule1.setPriority(10);
        rule1.setConditionType("MVEL");
        rule1.setConditionExpr("data.getOrDefault('orderAmount', 0) > 10000");
        rule1.setActionType("MVEL");
        rule1.setActionExpr("score = score + 30; hitRules.add('HIGH_AMOUNT_CHECK')");
        rule1.setStatus("ENABLED");
        easyRuleRepository.save(rule1);
        
        EasyRule rule2 = new EasyRule();
        rule2.setRuleCode("NEW_USER_CHECK");
        rule2.setRuleName("新用户风险检查");
        rule2.setDescription("新用户（注册小于7天）增加风险分数");
        rule2.setScene("PAYMENT");
        rule2.setPriority(20);
        rule2.setConditionType("MVEL");
        rule2.setConditionExpr("data.getOrDefault('registerDays', 100) < 7");
        rule2.setActionType("MVEL");
        rule2.setActionExpr("score = score + 20; hitRules.add('NEW_USER_CHECK')");
        rule2.setStatus("ENABLED");
        easyRuleRepository.save(rule2);
        
        EasyRule rule3 = new EasyRule();
        rule3.setRuleCode("DEVICE_RISK_CHECK");
        rule3.setRuleName("设备风险检查");
        rule3.setDescription("可疑设备标记增加风险分数");
        rule3.setScene("PAYMENT");
        rule3.setPriority(15);
        rule3.setConditionType("MVEL");
        rule3.setConditionExpr("data.getOrDefault('deviceRisk', 'LOW') == 'HIGH'");
        rule3.setActionType("MVEL");
        rule3.setActionExpr("score = score + 40; hitRules.add('DEVICE_RISK_CHECK')");
        rule3.setStatus("ENABLED");
        easyRuleRepository.save(rule3);
        
        EasyRule rule4 = new EasyRule();
        rule4.setRuleCode("REJECT_DECISION");
        rule4.setRuleName("拒绝决策");
        rule4.setDescription("风险分数超过80分时拒绝");
        rule4.setScene("PAYMENT");
        rule4.setPriority(100);
        rule4.setConditionType("MVEL");
        rule4.setConditionExpr("score >= 80");
        rule4.setActionType("MVEL");
        rule4.setActionExpr("decision = 'REJECT'; hitRules.add('REJECT_DECISION')");
        rule4.setStatus("ENABLED");
        easyRuleRepository.save(rule4);
        
        EasyRule rule5 = new EasyRule();
        rule5.setRuleCode("REVIEW_DECISION");
        rule5.setRuleName("人工审核决策");
        rule5.setDescription("风险分数在50-80之间时人工审核");
        rule5.setScene("PAYMENT");
        rule5.setPriority(90);
        rule5.setConditionType("MVEL");
        rule5.setConditionExpr("score >= 50 && score < 80");
        rule5.setActionType("MVEL");
        rule5.setActionExpr("decision = 'REVIEW'; hitRules.add('REVIEW_DECISION')");
        rule5.setStatus("ENABLED");
        easyRuleRepository.save(rule5);
        
        log.info("初始化了 {} 条EasyRules规则", easyRuleRepository.count());
        ruleEngine.loadAllRules();
    }

    private void initTestLists() {
        if (riskListRepository.count() > 0) {
            return;
        }
        
        RiskList blacklist1 = new RiskList();
        blacklist1.setListType("BLACKLIST");
        blacklist1.setMatchType("EXACT");
        blacklist1.setFieldName("phone");
        blacklist1.setFieldValue("13800138000");
        blacklist1.setListDesc("测试黑名单手机号");
        blacklist1.setStatus("ENABLED");
        riskListRepository.save(blacklist1);
        
        RiskList blacklist2 = new RiskList();
        blacklist2.setListType("BLACKLIST");
        blacklist2.setMatchType("FUZZY");
        blacklist2.setFieldName("deviceId");
        blacklist2.setFieldValue("emu");
        blacklist2.setListDesc("模拟器设备");
        blacklist2.setStatus("ENABLED");
        riskListRepository.save(blacklist2);
        
        RiskList whitelist1 = new RiskList();
        whitelist1.setListType("WHITELIST");
        whitelist1.setMatchType("EXACT");
        whitelist1.setFieldName("userId");
        whitelist1.setFieldValue("VIP001");
        whitelist1.setListDesc("VIP白名单用户");
        whitelist1.setStatus("ENABLED");
        riskListRepository.save(whitelist1);
        
        log.info("初始化了 {} 条名单", riskListRepository.count());
    }
}
