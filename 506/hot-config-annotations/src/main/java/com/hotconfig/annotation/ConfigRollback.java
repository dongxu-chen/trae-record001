package com.hotconfig.annotation;

import java.lang.annotation.*;

@Target({ElementType.TYPE, ElementType.METHOD})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface ConfigRollback {

    boolean enabled() default true;

    int maxRetryAttempts() default 3;

    long retryDelayMs() default 1000;

    boolean autoRollback() default true;

    String[] rollbackOnExceptions() default {};
}
