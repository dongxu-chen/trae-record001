package com.apiversion.gateway.strategy;

public interface HeaderParseStrategy {

    String getStrategyName();

    String parse(String headerValue, String pattern);
}
