package com.datasecurity.masking.audit;

import java.lang.annotation.*;

@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface Auditable {

    String operation() default "QUERY";

    String databaseId() default "default";

    boolean recordResult() default false;
}
