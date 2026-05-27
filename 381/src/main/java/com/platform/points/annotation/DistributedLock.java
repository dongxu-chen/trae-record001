package com.platform.points.annotation;

import java.lang.annotation.*;
import java.util.concurrent.TimeUnit;

@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface DistributedLock {

    String key();

    String prefix() default "lock:";

    long waitTime() default 3;

    long leaseTime() default -1;

    boolean watchdog() default true;

    TimeUnit timeUnit() default TimeUnit.SECONDS;

    String message() default "系统繁忙，请稍后再试";
}
