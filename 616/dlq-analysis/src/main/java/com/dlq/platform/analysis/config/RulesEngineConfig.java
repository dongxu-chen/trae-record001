package com.dlq.platform.analysis.config;

import org.jeasy.rules.api.RulesEngine;
import org.jeasy.rules.core.DefaultRulesEngine;
import org.jeasy.rules.core.RulesEngineParameters;
import org.jeasy.rules.mvel.MVELRuleFactory;
import org.jeasy.rules.spel.SpELRuleFactory;
import org.jeasy.rules.support.RuleDefinitionReader;
import org.jeasy.rules.support.reader.JsonRuleDefinitionReader;
import org.jeasy.rules.support.reader.YamlRuleDefinitionReader;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RulesEngineConfig {

    @Bean
    public RulesEngine rulesEngine() {
        RulesEngineParameters parameters = new RulesEngineParameters()
                .skipOnFirstAppliedRule(false)
                .skipOnFirstFailedRule(false)
                .skipOnFirstNonTriggeredRule(false)
                .rulePriorityThreshold(10);

        return new DefaultRulesEngine(parameters);
    }

    @Bean
    public MVELRuleFactory mvelRuleFactory() {
        RuleDefinitionReader reader = new JsonRuleDefinitionReader();
        return new MVELRuleFactory(reader);
    }

    @Bean
    public YamlRuleDefinitionReader yamlRuleDefinitionReader() {
        return new YamlRuleDefinitionReader();
    }

    @Bean
    public SpELRuleFactory spELRuleFactory() {
        RuleDefinitionReader reader = new YamlRuleDefinitionReader();
        return new SpELRuleFactory(reader);
    }
}
