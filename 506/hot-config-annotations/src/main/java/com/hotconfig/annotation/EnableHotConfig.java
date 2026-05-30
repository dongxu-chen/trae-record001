package com.hotconfig.annotation;

import org.springframework.context.annotation.Import;

import java.lang.annotation.*;

@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Documented
@Import(EnableHotConfigRegistrar.class)
public @interface EnableHotConfig {

    String[] basePackages() default {};

    String[] sources() default {};

    boolean enableApollo() default false;

    boolean enableFileWatch() default true;
}
