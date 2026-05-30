package com.riskengine.engine.drools;

import com.riskengine.model.RuleDefinition;
import lombok.extern.slf4j.Slf4j;
import org.drools.compiler.kie.builder.impl.InternalKieModule;
import org.drools.compiler.kie.builder.impl.KieBuilderImpl;
import org.drools.compiler.kie.builder.impl.KieFileSystemImpl;
import org.kie.api.KieBase;
import org.kie.api.KieServices;
import org.kie.api.builder.KieBuilder;
import org.kie.api.builder.KieFileSystem;
import org.kie.api.builder.Message;
import org.kie.api.builder.ReleaseId;
import org.kie.api.runtime.KieContainer;
import org.kie.api.runtime.KieSession;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class DroolsEngineManager {

    private final KieServices kieServices = KieServices.Factory.get();
    private final Map<String, KieContainer> containerCache = new ConcurrentHashMap<>();
    private final Map<String, KieBase> kieBaseCache = new ConcurrentHashMap<>();

    public synchronized KieSession buildKieSession(List<RuleDefinition> rules) {
        KieFileSystem kieFileSystem = kieServices.newKieFileSystem();

        for (RuleDefinition rule : rules) {
            if (rule.getEnabled() && rule.getDroolsDrl() != null) {
                String path = "src/main/resources/rules/" + rule.getRuleCode() + ".drl";
                kieFileSystem.write(path, rule.getDroolsDrl());
            }
        }

        KieBuilder kieBuilder = kieServices.newKieBuilder(kieFileSystem);
        kieBuilder.buildAll();

        List<Message> errors = kieBuilder.getResults().getMessages(Message.Level.ERROR);
        if (!errors.isEmpty()) {
            errors.forEach(e -> log.error("Drools compile error: {}", e.getText()));
            throw new RuntimeException("Drools rule compilation failed: " + errors.get(0).getText());
        }

        ReleaseId releaseId = kieBuilder.getKieModule().getReleaseId();
        KieContainer kieContainer = kieServices.newKieContainer(releaseId);

        KieBase kieBase = kieContainer.getKieBase();
        kieBaseCache.put("default", kieBase);
        containerCache.put("default", kieContainer);

        return kieContainer.newKieSession();
    }

    public KieSession getKieSession() {
        KieBase kieBase = kieBaseCache.get("default");
        if (kieBase == null) {
            return null;
        }
        return kieBase.newKieSession();
    }

    public synchronized void reloadRules(List<RuleDefinition> rules) {
        log.info("Reloading Drools rules, rule count: {}", rules.size());

        KieContainer oldContainer = containerCache.get("default");
        KieBase oldBase = kieBaseCache.get("default");

        try {
            KieSession session = buildKieSession(rules);
            session.dispose();
            log.info("Drools rules reloaded successfully");
        } catch (Exception e) {
            log.error("Failed to reload Drools rules, rolling back", e);
            if (oldContainer != null) {
                kieBaseCache.put("default", oldContainer.getKieBase());
            }
            throw new RuntimeException("Rule reload failed: " + e.getMessage(), e);
        }

        if (oldContainer != null) {
            try {
                oldContainer.dispose();
            } catch (Exception e) {
                log.warn("Failed to dispose old KieContainer", e);
            }
        }
    }

    public boolean validateDrl(String drl) {
        try {
            KieFileSystem kieFileSystem = kieServices.newKieFileSystem();
            kieFileSystem.write("src/main/resources/rules/validate.drl", drl);
            KieBuilder kieBuilder = kieServices.newKieBuilder(kieFileSystem);
            kieBuilder.buildAll();
            List<Message> errors = kieBuilder.getResults().getMessages(Message.Level.ERROR);
            return errors.isEmpty();
        } catch (Exception e) {
            log.warn("DRL validation failed: {}", e.getMessage());
            return false;
        }
    }
}
