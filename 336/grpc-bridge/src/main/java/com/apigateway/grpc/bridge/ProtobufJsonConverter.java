package com.apigateway.grpc.bridge;

import com.apigateway.grpc.bridge.exception.GrpcBridgeException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.google.protobuf.Descriptors;
import com.google.protobuf.Message;
import com.google.protobuf.MessageOrBuilder;
import com.google.protobuf.util.JsonFormat;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.List;
import java.util.Map;

/**
 * Protobuf与JSON双向转换器
 * 使用protobuf-java-util和Jackson实现高效的序列化和反序列化
 * 支持动态消息类型转换
 */
@Slf4j
@Component
public class ProtobufJsonConverter {

    /**
     * Jackson ObjectMapper
     */
    private final ObjectMapper objectMapper;

    /**
     * Protobuf JSON Printer，用于Protobuf转JSON
     */
    private final JsonFormat.Printer jsonPrinter;

    /**
     * Protobuf JSON Parser，用于JSON转Protobuf
     */
    private final JsonFormat.Parser jsonParser;

    /**
     * 构造函数，初始化转换器
     */
    public ProtobufJsonConverter() {
        this.objectMapper = new ObjectMapper();
        this.jsonPrinter = JsonFormat.printer()
                .includingDefaultValueFields()
                .preservingProtoFieldNames()
                .omittingInsignificantWhitespace();
        this.jsonParser = JsonFormat.parser()
                .ignoringUnknownFields();
    }

    /**
     * 将Protobuf消息转换为JSON字符串
     *
     * @param message Protobuf消息
     * @return JSON字符串
     */
    public String toJson(MessageOrBuilder message) {
        try {
            return jsonPrinter.print(message);
        } catch (Exception e) {
            throw new GrpcBridgeException("PROTOBUF_TO_JSON_ERROR",
                    "Failed to convert protobuf message to JSON: " + e.getMessage(), e);
        }
    }

    /**
     * 将Protobuf消息列表转换为JSON数组字符串
     *
     * @param messages Protobuf消息列表
     * @param <T>      消息类型
     * @return JSON数组字符串
     */
    public <T extends MessageOrBuilder> String toJsonArray(List<T> messages) {
        try {
            ArrayNode arrayNode = objectMapper.createArrayNode();
            for (T message : messages) {
                String json = jsonPrinter.print(message);
                arrayNode.add(objectMapper.readTree(json));
            }
            return objectMapper.writeValueAsString(arrayNode);
        } catch (Exception e) {
            throw new GrpcBridgeException("PROTOBUF_TO_JSON_ERROR",
                    "Failed to convert protobuf message list to JSON array: " + e.getMessage(), e);
        }
    }

    /**
     * 将JSON字符串转换为Protobuf消息
     *
     * @param json         JSON字符串
     * @param builder      Protobuf消息Builder
     * @param <T>          消息类型
     * @return 填充后的Builder
     */
    @SuppressWarnings("unchecked")
    public <T extends Message.Builder> T fromJson(String json, T builder) {
        try {
            jsonParser.merge(json, builder);
            return builder;
        } catch (Exception e) {
            throw new GrpcBridgeException("JSON_TO_PROTOBUF_ERROR",
                    "Failed to convert JSON to protobuf message: " + e.getMessage(), e);
        }
    }

    /**
     * 将Map转换为Protobuf消息
     *
     * @param map     数据Map
     * @param builder Protobuf消息Builder
     * @param <T>     消息类型
     * @return 填充后的Builder
     */
    public <T extends Message.Builder> T fromMap(Map<String, Object> map, T builder) {
        try {
            String json = objectMapper.writeValueAsString(map);
            return fromJson(json, builder);
        } catch (IOException e) {
            throw new GrpcBridgeException("MAP_TO_PROTOBUF_ERROR",
                    "Failed to convert Map to protobuf message: " + e.getMessage(), e);
        }
    }

    /**
     * 将Protobuf消息转换为Map
     *
     * @param message Protobuf消息
     * @return Map对象
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> toMap(MessageOrBuilder message) {
        try {
            String json = toJson(message);
            return objectMapper.readValue(json, Map.class);
        } catch (IOException e) {
            throw new GrpcBridgeException("PROTOBUF_TO_MAP_ERROR",
                    "Failed to convert protobuf message to Map: " + e.getMessage(), e);
        }
    }

    /**
     * 将JSON字符串转换为JsonNode
     *
     * @param json JSON字符串
     * @return JsonNode
     */
    public JsonNode toJsonNode(String json) {
        try {
            return objectMapper.readTree(json);
        } catch (IOException e) {
            throw new GrpcBridgeException("JSON_PARSE_ERROR",
                    "Failed to parse JSON string: " + e.getMessage(), e);
        }
    }

    /**
     * 将Protobuf消息转换为JsonNode
     *
     * @param message Protobuf消息
     * @return JsonNode
     */
    public JsonNode toJsonNode(MessageOrBuilder message) {
        return toJsonNode(toJson(message));
    }

    /**
     * 包装响应结果为标准JSON格式
     *
     * @param success 是否成功
     * @param data    数据内容
     * @param message 消息
     * @return 标准JSON响应字符串
     */
    public String wrapResponse(boolean success, Object data, String message) {
        try {
            ObjectNode responseNode = objectMapper.createObjectNode();
            responseNode.put("success", success);
            responseNode.put("message", message);

            if (data instanceof String dataStr) {
                JsonNode dataNode = objectMapper.readTree(dataStr);
                responseNode.set("data", dataNode);
            } else if (data instanceof MessageOrBuilder messageOrBuilder) {
                responseNode.set("data", toJsonNode(messageOrBuilder));
            } else if (data != null) {
                responseNode.set("data", objectMapper.valueToTree(data));
            }

            return objectMapper.writeValueAsString(responseNode);
        } catch (IOException e) {
            throw new GrpcBridgeException("RESPONSE_WRAP_ERROR",
                    "Failed to wrap response: " + e.getMessage(), e);
        }
    }

    /**
     * 包装错误响应
     *
     * @param errorCode    错误码
     * @param errorMessage 错误消息
     * @return 错误JSON响应字符串
     */
    public String wrapErrorResponse(String errorCode, String errorMessage) {
        try {
            ObjectNode responseNode = objectMapper.createObjectNode();
            responseNode.put("success", false);
            responseNode.put("message", errorMessage);

            ObjectNode errorNode = objectMapper.createObjectNode();
            errorNode.put("code", errorCode);
            errorNode.put("message", errorMessage);
            responseNode.set("error", errorNode);

            return objectMapper.writeValueAsString(responseNode);
        } catch (IOException e) {
            throw new GrpcBridgeException("RESPONSE_WRAP_ERROR",
                    "Failed to wrap error response: " + e.getMessage(), e);
        }
    }

    /**
     * 验证JSON是否符合Protobuf消息格式
     *
     * @param json          JSON字符串
     * @param descriptor    消息描述符
     * @return 验证结果，true表示有效
     */
    public boolean validateJson(String json, Descriptors.Descriptor descriptor) {
        try {
            Message.Builder builder = Message.newBuilderForType(
                    Descriptors.DescriptorsProtos.FileDescriptorSet.getDefaultInstanceForType()
                            .getDescriptorForType()).clone();
            jsonParser.merge(json, builder);
            return true;
        } catch (Exception e) {
            log.warn("JSON validation failed for descriptor {}: {}", descriptor.getName(), e.getMessage());
            return false;
        }
    }

    /**
     * 格式化JSON字符串（美化输出）
     *
     * @param json JSON字符串
     * @return 格式化后的JSON字符串
     */
    public String prettyPrint(String json) {
        try {
            JsonNode jsonNode = objectMapper.readTree(json);
            return objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(jsonNode);
        } catch (IOException e) {
            throw new GrpcBridgeException("JSON_FORMAT_ERROR",
                    "Failed to format JSON: " + e.getMessage(), e);
        }
    }
}
