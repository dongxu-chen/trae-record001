package com.hotconfig.annotation;

import org.springframework.beans.factory.config.BeanDefinition;
import org.springframework.beans.factory.support.BeanDefinitionRegistry;
import org.springframework.beans.factory.support.RootBeanDefinition;
import org.springframework.context.annotation.ImportBeanDefinitionRegistrar;
import org.springframework.core.annotation.AnnotationAttributes;
import org.springframework.core.type.AnnotationMetadata;
import org.springframework.util.ClassUtils;
import org.springframework.util.StringUtils;

public class EnableHotConfigRegistrar implements ImportBeanDefinitionRegistrar {

    private static final String AUTO_CONFIGURATION_CLASS = "com.hotconfig.spring.HotConfigAutoConfiguration";

    @Override
    public void registerBeanDefinitions(AnnotationMetadata importingClassMetadata, BeanDefinitionRegistry registry) {
        AnnotationAttributes attributes = AnnotationAttributes.fromMap(
                importingClassMetadata.getAnnotationAttributes(EnableHotConfig.class.getName(), false));

        if (attributes == null) {
            return;
        }

        String[] basePackages = attributes.getStringArray("basePackages");
        String[] sources = attributes.getStringArray("sources");
        boolean enableApollo = attributes.getBoolean("enableApollo");
        boolean enableFileWatch = attributes.getBoolean("enableFileWatch");

        if (basePackages.length > 0) {
            System.setProperty("hotconfig.basePackages", StringUtils.arrayToCommaDelimitedString(basePackages));
        }
        if (sources.length > 0) {
            System.setProperty("hotconfig.sources", StringUtils.arrayToCommaDelimitedString(sources));
        }
        System.setProperty("hotconfig.enableApollo", String.valueOf(enableApollo));
        System.setProperty("hotconfig.enableFileWatch", String.valueOf(enableFileWatch));

        try {
            if (ClassUtils.isPresent(AUTO_CONFIGURATION_CLASS, getClass().getClassLoader())) {
                Class<?> configClass = ClassUtils.forName(AUTO_CONFIGURATION_CLASS, getClass().getClassLoader());
                BeanDefinition beanDefinition = new RootBeanDefinition(configClass);
                registry.registerBeanDefinition(AUTO_CONFIGURATION_CLASS, beanDefinition);
            }
        } catch (Exception e) {
            throw new RuntimeException("Failed to register HotConfigAutoConfiguration", e);
        }
    }
}
