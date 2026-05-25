package com.apigateway.grpc.bridge;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.protobuf.util.JsonFormat;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * gRPC桥接Spring Boot自动配置类
 * 自动配置gRPC桥接所需的所有Bean
 * 包括通道工厂、JSON转换器、桥接服务等
 */
@Configuration
@ConditionalOnClass({GrpcBridgeService.class})
@EnableConfigurationProperties(GrpcClientProperties.class)
public class GrpcBridgeAutoConfiguration {

    /**
     * 配置gRPC客户端属性
     *
     * @return gRPC客户端属性配置
     */
    @Bean
    @ConditionalOnMissingBean
    public GrpcClientProperties grpcClientProperties() {
        return new GrpcClientProperties();
    }

    /**
     * 配置gRPC通道工厂
     *
     * @param properties gRPC客户端配置
     * @return gRPC通道工厂
     */
    @Bean
    @ConditionalOnMissingBean
    public GrpcChannelFactory grpcChannelFactory(GrpcClientProperties properties) {
        return new GrpcChannelFactory(properties);
    }

    /**
     * 配置Protobuf JSON转换器
     *
     * @param objectMapper Jackson ObjectMapper
     * @return Protobuf JSON转换器
     */
    @Bean
    @ConditionalOnMissingBean
    public ProtobufJsonConverter protobufJsonConverter(ObjectMapper objectMapper) {
        return new ProtobufJsonConverter();
    }

    /**
     * 配置gRPC桥接服务
     *
     * @param channelFactory gRPC通道工厂
     * @param jsonConverter  Protobuf JSON转换器
     * @param properties     gRPC客户端配置
     * @return gRPC桥接服务
     */
    @Bean
    @ConditionalOnMissingBean
    public GrpcBridgeService grpcBridgeService(GrpcChannelFactory channelFactory,
                                               ProtobufJsonConverter jsonConverter,
                                               GrpcClientProperties properties) {
        return new GrpcBridgeService(channelFactory, jsonConverter, properties);
    }

    /**
     * 配置Jackson ObjectMapper（如果不存在）
     *
     * @return Jackson ObjectMapper
     */
    @Bean
    @ConditionalOnMissingBean
    public ObjectMapper objectMapper() {
        return new ObjectMapper();
    }

    /**
     * 配置Protobuf JSON Printer
     *
     * @return JSON Printer
     */
    @Bean
    @ConditionalOnMissingBean
    public JsonFormat.Printer jsonPrinter() {
        return JsonFormat.printer()
                .includingDefaultValueFields()
                .preservingProtoFieldNames()
                .omittingInsignificantWhitespace();
    }

    /**
     * 配置Protobuf JSON Parser
     *
     * @return JSON Parser
     */
    @Bean
    @ConditionalOnMissingBean
    public JsonFormat.Parser jsonParser() {
        return JsonFormat.parser()
                .ignoringUnknownFields();
    }
}
