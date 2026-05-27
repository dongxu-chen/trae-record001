package com.datasecurity.masking.annotation;

import java.lang.annotation.*;

@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface DataMasking {

    String databaseId() default "default";

    boolean enabled() default true;
}
