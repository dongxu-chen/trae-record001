package com.hotconfig.annotation;

import java.lang.annotation.*;

@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface HotConfig {

    String prefix() default "";

    String[] sources() default {};

    boolean autoRefresh() default true;
}
