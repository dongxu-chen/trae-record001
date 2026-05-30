package com.apiversion.version.service;

import com.apiversion.version.entity.HeaderParseRule;
import com.apiversion.version.entity.RoutingRule;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import java.util.List;

public interface RoutingRuleService {

    IPage<RoutingRule> listRules(Page<RoutingRule> page, String apiName, Boolean enabled);

    RoutingRule getRuleById(Long id);

    RoutingRule createRule(RoutingRule rule);

    RoutingRule updateRule(RoutingRule rule);

    void deleteRule(Long id);

    List<HeaderParseRule> getHeaderRulesByRoutingRuleId(Long routingRuleId);

    HeaderParseRule createHeaderRule(HeaderParseRule rule);

    HeaderParseRule updateHeaderRule(HeaderParseRule rule);

    void deleteHeaderRule(Long id);

    void syncHeaderRulesToRedis(String apiPath);

    List<RoutingRule> getEnabledRules();
}
