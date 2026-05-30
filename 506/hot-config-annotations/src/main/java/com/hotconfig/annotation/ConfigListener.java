package com.hotconfig.annotation;

import java.lang.annotation.*;

@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface ConfigListener {

    String[] keys() default {};

    String[] prefixes() default {};

    String[] sources() default {};

    boolean async() default false;
}
