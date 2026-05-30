package com.hotconfig.annotation;

import java.lang.annotation.*;

@Target({ElementType.TYPE, ElementType.FIELD})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface ConfigHealthCheck {

    boolean enabled() default true;

    boolean checkDanglingReferences() default true;

    boolean checkRequiredFields() default true;

    boolean checkTypeCompatibility() default true;

    long checkIntervalMs() default 60000;

    String[] excludeKeys() default {};
}
