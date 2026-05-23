package com.pushcenter.config;

import org.apache.velocity.app.VelocityEngine;
import org.apache.velocity.runtime.RuntimeConstants;
import org.apache.velocity.runtime.resource.loader.ClasspathResourceLoader;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Properties;

@Configuration
public class VelocityConfig {

    @Bean
    public VelocityEngine velocityEngine() {
        Properties props = new Properties();

        props.setProperty(RuntimeConstants.RESOURCE_LOADER, "classpath");
        props.setProperty("classpath.resource.loader.class", ClasspathResourceLoader.class.getName());

        props.setProperty(RuntimeConstants.INPUT_ENCODING, "UTF-8");
        props.setProperty(RuntimeConstants.OUTPUT_ENCODING, "UTF-8");

        props.setProperty(RuntimeConstants.VM_LIBRARY, "");
        props.setProperty(RuntimeConstants.VM_LIBRARY_AUTORELOAD, "false");
        props.setProperty(RuntimeConstants.FILE_RESOURCE_LOADER_CACHE, "true");

        props.setProperty("runtime.log.logsystem.class", "org.apache.velocity.runtime.log.NullLogChute");

        VelocityEngine engine = new VelocityEngine();
        engine.init(props);

        return engine;
    }
}
