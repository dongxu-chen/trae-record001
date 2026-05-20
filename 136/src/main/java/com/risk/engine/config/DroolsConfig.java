package com.risk.engine.config;

import lombok.extern.slf4j.Slf4j;
import org.drools.compiler.kie.builder.impl.KieContainerImpl;
import org.kie.api.KieBase;
import org.kie.api.KieServices;
import org.kie.api.builder.*;
import org.kie.api.runtime.KieContainer;
import org.kie.api.runtime.KieSession;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.Resource;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;
import org.springframework.core.io.support.ResourcePatternResolver;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.ReentrantReadWriteLock;

@Slf4j
@Configuration
public class DroolsConfig {

    private static final String RULES_PATH = "rules/";
    private static final String DEFAULT_SCENE = "DEFAULT";
    
    private final ReentrantReadWriteLock lock = new ReentrantReadWriteLock();
    private volatile Map<String, KieContainer> kieContainerMap = new ConcurrentHashMap<>();
    private volatile Map<String, Long> kieContainerVersion = new ConcurrentHashMap<>();

    @Bean
    public KieServices kieServices() {
        return KieServices.Factory.get();
    }

    @Bean
    public KieRepository kieRepository(KieServices kieServices) {
        return kieServices.getRepository();
    }

    @Bean
    public Map<String, KieContainer> kieContainerMap(KieServices kieServices, KieRepository kieRepository) throws IOException {
        initKieContainers(kieServices, kieRepository);
        return kieContainerMap;
    }

    private void initKieContainers(KieServices kieServices, KieRepository kieRepository) throws IOException {
        ResourcePatternResolver resourcePatternResolver = new PathMatchingResourcePatternResolver();
        Resource[] resources = resourcePatternResolver.getResources("classpath*:" + RULES_PATH + "**/*.*");
        
        Map<String, StringBuilder> sceneRulesMap = new HashMap<>();
        sceneRulesMap.put(DEFAULT_SCENE, new StringBuilder());
        
        for (Resource resource : resources) {
            String scene = extractSceneFromResource(resource);
            String ruleContent = readResourceContent(resource);
            sceneRulesMap.computeIfAbsent(scene, k -> new StringBuilder()).append(ruleContent).append("\n");
        }
        
        for (Map.Entry<String, StringBuilder> entry : sceneRulesMap.entrySet()) {
            String scene = entry.getKey();
            String rulesContent = entry.getValue().toString();
            
            if (compileAndBuildContainer(kieServices, kieRepository, scene, rulesContent)) {
                log.info("场景 [{}] 规则库初始化成功", scene);
            }
        }
    }

    private String extractSceneFromResource(Resource resource) {
        String filename = resource.getFilename();
        if (filename == null) {
            return DEFAULT_SCENE;
        }
        int dashIndex = filename.indexOf('-');
        if (dashIndex > 0) {
            return filename.substring(0, dashIndex).toUpperCase();
        }
        return DEFAULT_SCENE;
    }

    private String readResourceContent(Resource resource) throws IOException {
        return new String(resource.getInputStream().readAllBytes());
    }

    public boolean compileAndBuildContainer(KieServices kieServices, KieRepository kieRepository, 
                                            String scene, String rulesContent) {
        lock.writeLock().lock();
        try {
            KieFileSystem kieFileSystem = kieServices.newKieFileSystem();
            ReleaseId releaseId = kieServices.newReleaseId(
                    "com.risk.engine", "rules-" + scene.toLowerCase(), 
                    String.valueOf(System.currentTimeMillis()));
            
            kieFileSystem.generateAndWritePomXML(releaseId);
            kieFileSystem.write("src/main/resources/rules/" + scene + ".drl", rulesContent);
            
            KieBuilder kieBuilder = kieServices.newKieBuilder(kieFileSystem);
            kieBuilder.buildAll();
            
            if (kieBuilder.getResults().hasMessages(Message.Level.ERROR)) {
                log.error("场景 [{}] 规则编译失败: {}", scene, kieBuilder.getResults().getMessages());
                return false;
            }
            
            KieContainer newContainer = kieServices.newKieContainer(releaseId);
            
            if (kieContainerMap.containsKey(scene)) {
                KieContainer oldContainer = kieContainerMap.get(scene);
                try {
                    ((KieContainerImpl) oldContainer).dispose();
                } catch (Exception e) {
                    log.warn("旧容器释放异常: {}", e.getMessage());
                }
            }
            
            kieContainerMap.put(scene, newContainer);
            kieContainerVersion.put(scene, System.currentTimeMillis());
            log.info("场景 [{}] 规则库更新成功, 版本: {}", scene, releaseId.getVersion());
            return true;
            
        } catch (Exception e) {
            log.error("场景 [{}] 规则库构建失败: {}", scene, e.getMessage(), e);
            return false;
        } finally {
            lock.writeLock().unlock();
        }
    }

    public KieSession getKieSession(String scene) {
        lock.readLock().lock();
        try {
            KieContainer container = kieContainerMap.get(scene);
            if (container == null) {
                container = kieContainerMap.get(DEFAULT_SCENE);
            }
            if (container == null) {
                throw new IllegalStateException("没有可用的规则容器, 场景: " + scene);
            }
            KieBase kieBase = container.getKieBase();
            return kieBase.newKieSession();
        } finally {
            lock.readLock().unlock();
        }
    }

    public boolean reloadRules(String scene, String rulesContent) {
        KieServices kieServices = kieServices();
        KieRepository kieRepository = kieRepository(kieServices);
        return compileAndBuildContainer(kieServices, kieRepository, scene, rulesContent);
    }

    public Long getContainerVersion(String scene) {
        return kieContainerVersion.getOrDefault(scene, 0L);
    }
}
