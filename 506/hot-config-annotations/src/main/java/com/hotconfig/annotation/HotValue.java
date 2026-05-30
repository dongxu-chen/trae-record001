package com.hotconfig.annotation;

import java.lang.annotation.*;

@Target({ElementType.FIELD, ElementType.METHOD})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface HotValue {

    String value();

    String defaultValue() default "";

    boolean required() default false;
}
