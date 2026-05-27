package com.api.docs.annotation;

import java.lang.annotation.*;

@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Repeatable(ApiResponses.class)
public @interface ApiResponse {
    String code() default "200";

    String message() default "";

    Class<?> response() default Object.class;

    String description() default "";

    boolean isArray() default false;
}
