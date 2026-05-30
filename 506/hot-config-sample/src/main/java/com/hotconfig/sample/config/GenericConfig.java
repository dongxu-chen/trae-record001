package com.hotconfig.sample.config;

import com.hotconfig.annotation.HotConfig;
import com.hotconfig.annotation.HotValue;
import lombok.Data;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

@Data
@Component
@HotConfig(prefix = "generic")
public class GenericConfig {

    @HotValue(value = "string.list", defaultValue = "a,b,c")
    private List<String> stringList;

    @HotValue(value = "integer.list", defaultValue = "1,2,3")
    private List<Integer> integerList;

    @HotValue(value = "long.set", defaultValue = "100,200,300")
    private Set<Long> longSet;

    @HotValue(value = "string-int.map", defaultValue = "key1:1,key2:2,key3:3")
    private Map<String, Integer> stringIntMap;

    @HotValue(value = "int-string.map", defaultValue = "1:one,2:two,3:three")
    private Map<Integer, String> intStringMap;

    @HotValue(value = "optional.value", defaultValue = "default")
    private Optional<String> optionalValue;

    @HotValue(value = "optional.number", defaultValue = "42")
    private Optional<Integer> optionalNumber;

    @HotValue(value = "double.list", defaultValue = "1.1,2.2,3.3")
    private List<Double> doubleList;

    @HotValue(value = "boolean.list", defaultValue = "true,false,true")
    private List<Boolean> booleanList;
}
