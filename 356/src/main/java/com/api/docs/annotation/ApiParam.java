package com.api.docs.annotation;

import java.lang.annotation.*;

@Target({ElementType.PARAMETER, ElementType.FIELD, ElementType.METHOD})
@Retention(RetentionPolicy.RUNTIME)
public @interface ApiParam {
    String value() default "";

    String name() default "";

    String description() default "";

    String example() default "";

    String defaultValue() default "";

    boolean required() default false;

    String[] allowableValues() default {};

    String dataType() default "";
}
