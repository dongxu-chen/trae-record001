package com.hotconfig.annotation;

import java.lang.annotation.*;

@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface DependsOnConfig {

    String[] value() default {};

    int order() default 0;
}
