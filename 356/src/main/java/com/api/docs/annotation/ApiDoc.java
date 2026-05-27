package com.api.docs.annotation;

import java.lang.annotation.*;

@Target({ElementType.TYPE, ElementType.METHOD})
@Retention(RetentionPolicy.RUNTIME)
public @interface ApiDoc {
    String value() default "";

    String description() default "";

    String summary() default "";

    String module() default "";

    String businessType() default "";

    String owner() default "";

    String version() default "";

    String createTime() default "";

    String updateTime() default "";

    String[] tags() default {};

    boolean deprecated() default false;

    String deprecatedReason() default "";
}
