package com.apigateway.core.handler;

import com.fasterxml.jackson.databind.ObjectMapper;
import graphql.ExecutionInput;
import graphql.ExecutionResult;
import graphql.GraphQL;
import graphql.GraphQLException;
import graphql.schema.DataFetcher;
import graphql.schema.GraphQLSchema;
import graphql.schema.idl.RuntimeWiring;
import graphql.schema.idl.SchemaGenerator;
import graphql.schema.idl.SchemaParser;
import graphql.schema.idl.TypeDefinitionRegistry;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.server.ServerRequest;
import org.springframework.web.reactive.function.server.ServerResponse;
import reactor.core.publisher.Mono;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * GraphQL处理器
 * 处理/api/graphql/**请求，支持GraphQL查询执行
 * 内置用户和订单相关的GraphQL Schema和DataFetcher
 * 使用graphql-java库实现
 *
 * @author api-gateway
 * @version 1.0.0
 * @since 2026-05-24
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class GraphQLHandler {

    /**
     * JSON对象映射器
     */
    private final ObjectMapper objectMapper;

    /**
     * GraphQL实例
     */
    private GraphQL graphQL;

    /**
     * 默认GraphQL Schema定义
     */
    private static final String DEFAULT_SCHEMA = """
            type Query {
                user(id: ID!): User
                users(page: Int = 1, size: Int = 10): UserList
                order(orderId: ID!): Order
                orders(userId: ID, page: Int = 1, size: Int = 10): OrderList
                userWithOrders(userId: ID!): UserWithOrders
            }
            
            type Mutation {
                createUser(input: CreateUserInput!): User
                updateUser(id: ID!, input: UpdateUserInput!): User
                deleteUser(id: ID!): DeleteResponse
                createOrder(input: CreateOrderInput!): Order
                updateOrderStatus(orderId: ID!, status: String!): Order
            }
            
            type User {
                id: ID!
                name: String!
                email: String!
                age: Int
                createdAt: String
                updatedAt: String
            }
            
            type UserList {
                users: [User!]!
                total: Int!
                page: Int!
                size: Int!
            }
            
            type UserWithOrders {
                user: User!
                orders: [Order!]!
            }
            
            type Order {
                orderId: ID!
                userId: ID!
                items: [OrderItem!]!
                totalAmount: Float!
                status: String!
                address: String
                createdAt: String
                updatedAt: String
            }
            
            type OrderItem {
                productId: String!
                productName: String!
                quantity: Int!
                price: Float!
            }
            
            type OrderList {
                orders: [Order!]!
                total: Int!
                page: Int!
                size: Int!
            }
            
            input CreateUserInput {
                name: String!
                email: String!
                age: Int
            }
            
            input UpdateUserInput {
                name: String
                email: String
                age: Int
            }
            
            input CreateOrderInput {
                userId: ID!
                items: [OrderItemInput!]!
                address: String!
            }
            
            input OrderItemInput {
                productId: String!
                productName: String!
                quantity: Int!
                price: Float!
            }
            
            type DeleteResponse {
                success: Boolean!
                message: String!
            }
            """;

    /**
     * 初始化GraphQL实例
     */
    @PostConstruct
    public void init() {
        log.info("初始化GraphQL处理器");
        try {
            String schemaContent = loadSchema();
            graphQL = buildGraphQL(schemaContent);
            log.info("GraphQL处理器初始化完成");
        } catch (Exception e) {
            log.error("GraphQL初始化失败", e);
            throw new RuntimeException("GraphQL初始化失败", e);
        }
    }

    /**
     * 加载GraphQL Schema
     * 优先从classpath加载graphql/schema.graphqls，不存在则使用默认Schema
     *
     * @return Schema内容
     */
    private String loadSchema() {
        try (InputStream is = getClass().getResourceAsStream("/graphql/schema.graphqls")) {
            if (is != null) {
                log.info("从classpath加载GraphQL Schema");
                return new String(is.readAllBytes(), StandardCharsets.UTF_8);
            }
        } catch (Exception e) {
            log.warn("加载自定义Schema失败，使用默认Schema: {}", e.getMessage());
        }
        log.info("使用默认GraphQL Schema");
        return DEFAULT_SCHEMA;
    }

    /**
     * 构建GraphQL实例
     *
     * @param schemaContent Schema内容
     * @return GraphQL实例
     */
    private GraphQL buildGraphQL(String schemaContent) {
        SchemaParser schemaParser = new SchemaParser();
        TypeDefinitionRegistry typeRegistry = schemaParser.parse(schemaContent);

        RuntimeWiring wiring = buildRuntimeWiring();
        SchemaGenerator schemaGenerator = new SchemaGenerator();
        GraphQLSchema graphQLSchema = schemaGenerator.makeExecutableSchema(typeRegistry, wiring);

        return GraphQL.newGraphQL(graphQLSchema).build();
    }

    /**
     * 构建运行时Wiring，注册DataFetcher
     *
     * @return RuntimeWiring实例
     */
    private RuntimeWiring buildRuntimeWiring() {
        return RuntimeWiring.newRuntimeWiring()
                .type("Query", typeWiring -> typeWiring
                        .dataFetcher("user", userDataFetcher())
                        .dataFetcher("users", usersDataFetcher())
                        .dataFetcher("order", orderDataFetcher())
                        .dataFetcher("orders", ordersDataFetcher())
                        .dataFetcher("userWithOrders", userWithOrdersDataFetcher())
                )
                .type("Mutation", typeWiring -> typeWiring
                        .dataFetcher("createUser", createUserDataFetcher())
                        .dataFetcher("updateUser", updateUserDataFetcher())
                        .dataFetcher("deleteUser", deleteUserDataFetcher())
                        .dataFetcher("createOrder", createOrderDataFetcher())
                        .dataFetcher("updateOrderStatus", updateOrderStatusDataFetcher())
                )
                .build();
    }

    /**
     * 处理GraphQL请求
     *
     * @param request 服务器请求
     * @return 服务器响应Mono
     */
    public Mono<ServerResponse> handleGraphQL(ServerRequest request) {
        log.debug("收到GraphQL请求");

        return parseGraphQLRequest(request)
                .flatMap(graphQLRequest -> executeGraphQL(graphQLRequest.query(),
                        graphQLRequest.operationName(),
                        graphQLRequest.variables()))
                .flatMap(result -> ServerResponse.ok()
                        .contentType(MediaType.APPLICATION_JSON)
                        .bodyValue(result))
                .onErrorResume(this::handleError);
    }

    /**
     * 处理GraphQL GET请求
     * 通过查询参数传递query、operationName和variables
     *
     * @param request 服务器请求
     * @return 服务器响应Mono
     */
    public Mono<ServerResponse> handleGraphQLGet(ServerRequest request) {
        log.debug("收到GraphQL GET请求");

        String query = request.queryParam("query").orElse("");
        String operationName = request.queryParam("operationName").orElse(null);
        Map<String, Object> variables = parseVariables(request.queryParam("variables").orElse(null));

        if (query.isEmpty()) {
            return badRequest("GraphQL查询不能为空");
        }

        return executeGraphQL(query, operationName, variables)
                .flatMap(result -> ServerResponse.ok()
                        .contentType(MediaType.APPLICATION_JSON)
                        .bodyValue(result))
                .onErrorResume(this::handleError);
    }

    /**
     * 处理GraphQL POST请求
     * 通过请求体传递query、operationName和variables
     *
     * @param request 服务器请求
     * @return 服务器响应Mono
     */
    public Mono<ServerResponse> handleGraphQLPost(ServerRequest request) {
        log.debug("收到GraphQL POST请求");
        return handleGraphQL(request);
    }

    /**
     * 解析GraphQL请求体
     *
     * @param request 服务器请求
     * @return GraphQL请求Mono
     */
    private Mono<GraphQLRequest> parseGraphQLRequest(ServerRequest request) {
        return request.bodyToMono(String.class)
                .flatMap(body -> {
                    try {
                        Map<String, Object> requestMap = objectMapper.readValue(body, Map.class);
                        String query = (String) requestMap.getOrDefault("query", "");
                        String operationName = (String) requestMap.get("operationName");
                        Map<String, Object> variables = parseVariables(requestMap.get("variables"));

                        if (query.isEmpty()) {
                            return Mono.error(new IllegalArgumentException("GraphQL查询不能为空"));
                        }

                        return Mono.just(new GraphQLRequest(query, operationName, variables));
                    } catch (Exception e) {
                        log.error("解析GraphQL请求失败: {}", e.getMessage());
                        return Mono.error(new IllegalArgumentException("无效的GraphQL请求格式"));
                    }
                });
    }

    /**
     * 解析variables参数
     *
     * @param variablesObj variables对象
     * @return variables Map
     */
    @SuppressWarnings("unchecked")
    private Map<String, Object> parseVariables(Object variablesObj) {
        if (variablesObj == null) {
            return new HashMap<>();
        }
        if (variablesObj instanceof String variablesStr) {
            if (variablesStr.isEmpty()) {
                return new HashMap<>();
            }
            try {
                return objectMapper.readValue(variablesStr, Map.class);
            } catch (Exception e) {
                log.warn("解析variables失败: {}", e.getMessage());
                return new HashMap<>();
            }
        }
        if (variablesObj instanceof Map) {
            return (Map<String, Object>) variablesObj;
        }
        return new HashMap<>();
    }

    /**
     * 执行GraphQL查询
     *
     * @param query         查询语句
     * @param operationName 操作名称
     * @param variables     变量
     * @return 执行结果Mono
     */
    private Mono<Map<String, Object>> executeGraphQL(String query, String operationName,
                                                     Map<String, Object> variables) {
        log.debug("执行GraphQL查询 - operationName: {}", operationName);
        log.trace("GraphQL query: {}", query);

        return Mono.fromCallable(() -> {
            ExecutionInput executionInput = ExecutionInput.newExecutionInput()
                    .query(query)
                    .operationName(operationName)
                    .variables(variables)
                    .build();

            ExecutionResult executionResult = graphQL.execute(executionInput);

            Map<String, Object> result = new HashMap<>();
            if (!executionResult.getErrors().isEmpty()) {
                result.put("errors", executionResult.getErrors());
            }
            result.put("data", executionResult.getData());
            if (executionResult.getExtensions() != null) {
                result.put("extensions", executionResult.getExtensions());
            }

            return result;
        }).onErrorMap(e -> {
            log.error("GraphQL执行失败: {}", e.getMessage());
            if (e instanceof GraphQLException) {
                return e;
            }
            return new GraphQLException("GraphQL执行失败", e);
        });
    }

    /**
     * 获取GraphQL Schema
     *
     * @param request 服务器请求
     * @return Schema响应Mono
     */
    public Mono<ServerResponse> getSchema(ServerRequest request) {
        log.debug("获取GraphQL Schema");
        return ServerResponse.ok()
                .contentType(MediaType.TEXT_PLAIN)
                .bodyValue(loadSchema());
    }

    /**
     * 获取GraphQL健康状态
     *
     * @param request 服务器请求
     * @return 健康状态响应Mono
     */
    public Mono<ServerResponse> health(ServerRequest request) {
        return ServerResponse.ok()
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(Map.of(
                        "status", "UP",
                        "service", "graphql",
                        "timestamp", System.currentTimeMillis()
                ));
    }

    // ==================== DataFetcher 实现 ====================

    /**
     * 获取单个用户DataFetcher
     */
    private DataFetcher<Mono<Map<String, Object>>> userDataFetcher() {
        return dataFetchingEnvironment -> {
            String id = dataFetchingEnvironment.getArgument("id");
            log.debug("GraphQL查询用户 - id: {}", id);

            return Mono.just(Map.of(
                    "id", id,
                    "name", "User" + id,
                    "email", "user" + id + "@example.com",
                    "age", 25 + Integer.parseInt(id) % 10,
                    "createdAt", "2026-01-01T00:00:00Z",
                    "updatedAt", "2026-01-01T00:00:00Z"
            ));
        };
    }

    /**
     * 获取用户列表DataFetcher
     */
    private DataFetcher<Mono<Map<String, Object>>> usersDataFetcher() {
        return dataFetchingEnvironment -> {
            int page = dataFetchingEnvironment.getArgumentOrDefault("page", 1);
            int size = dataFetchingEnvironment.getArgumentOrDefault("size", 10);
            log.debug("GraphQL查询用户列表 - page: {}, size: {}", page, size);

            List<Map<String, Object>> users = new ArrayList<>();
            for (int i = 0; i < size; i++) {
                int userId = (page - 1) * size + i + 1;
                users.add(Map.of(
                        "id", String.valueOf(userId),
                        "name", "User" + userId,
                        "email", "user" + userId + "@example.com",
                        "age", 25 + userId % 10,
                        "createdAt", "2026-01-01T00:00:00Z",
                        "updatedAt", "2026-01-01T00:00:00Z"
                ));
            }

            return Mono.just(Map.of(
                    "users", users,
                    "total", 100,
                    "page", page,
                    "size", size
            ));
        };
    }

    /**
     * 获取单个订单DataFetcher
     */
    private DataFetcher<Mono<Map<String, Object>>> orderDataFetcher() {
        return dataFetchingEnvironment -> {
            String orderId = dataFetchingEnvironment.getArgument("orderId");
            log.debug("GraphQL查询订单 - orderId: {}", orderId);

            List<Map<String, Object>> items = List.of(
                    Map.of(
                            "productId", "P001",
                            "productName", "Product 1",
                            "quantity", 2,
                            "price", 99.99
                    ),
                    Map.of(
                            "productId", "P002",
                            "productName", "Product 2",
                            "quantity", 1,
                            "price", 199.99
                    )
            );

            return Mono.just(Map.of(
                    "orderId", orderId,
                    "userId", "1",
                    "items", items,
                    "totalAmount", 399.97,
                    "status", "CREATED",
                    "address", "北京市朝阳区",
                    "createdAt", "2026-01-01T00:00:00Z",
                    "updatedAt", "2026-01-01T00:00:00Z"
            ));
        };
    }

    /**
     * 获取订单列表DataFetcher
     */
    private DataFetcher<Mono<Map<String, Object>>> ordersDataFetcher() {
        return dataFetchingEnvironment -> {
            String userId = dataFetchingEnvironment.getArgument("userId");
            int page = dataFetchingEnvironment.getArgumentOrDefault("page", 1);
            int size = dataFetchingEnvironment.getArgumentOrDefault("size", 10);
            log.debug("GraphQL查询订单列表 - userId: {}, page: {}, size: {}", userId, page, size);

            List<Map<String, Object>> orders = new ArrayList<>();
            for (int i = 0; i < size; i++) {
                String orderId = "ORD" + String.format("%06d", (page - 1) * size + i + 1);
                List<Map<String, Object>> items = List.of(
                        Map.of(
                                "productId", "P001",
                                "productName", "Product 1",
                                "quantity", i + 1,
                                "price", 99.99
                        )
                );
                orders.add(Map.of(
                        "orderId", orderId,
                        "userId", userId != null ? userId : "1",
                        "items", items,
                        "totalAmount", 99.99 * (i + 1),
                        "status", i % 3 == 0 ? "CREATED" : i % 3 == 1 ? "PAID" : "SHIPPED",
                        "address", "北京市朝阳区",
                        "createdAt", "2026-01-01T00:00:00Z",
                        "updatedAt", "2026-01-01T00:00:00Z"
                ));
            }

            return Mono.just(Map.of(
                    "orders", orders,
                    "total", 50,
                    "page", page,
                    "size", size
            ));
        };
    }

    /**
     * 获取用户及其订单DataFetcher
     */
    private DataFetcher<Mono<Map<String, Object>>> userWithOrdersDataFetcher() {
        return dataFetchingEnvironment -> {
            String userId = dataFetchingEnvironment.getArgument("userId");
            log.debug("GraphQL查询用户及其订单 - userId: {}", userId);

            Map<String, Object> user = Map.of(
                    "id", userId,
                    "name", "User" + userId,
                    "email", "user" + userId + "@example.com",
                    "age", 25 + Integer.parseInt(userId) % 10,
                    "createdAt", "2026-01-01T00:00:00Z",
                    "updatedAt", "2026-01-01T00:00:00Z"
            );

            List<Map<String, Object>> orders = List.of(
                    Map.of(
                            "orderId", "ORD000001",
                            "userId", userId,
                            "items", List.of(Map.of(
                                    "productId", "P001",
                                    "productName", "Product 1",
                                    "quantity", 1,
                                    "price", 99.99
                            )),
                            "totalAmount", 99.99,
                            "status", "CREATED",
                            "address", "北京市朝阳区",
                            "createdAt", "2026-01-01T00:00:00Z",
                            "updatedAt", "2026-01-01T00:00:00Z"
                    )
            );

            return Mono.just(Map.of(
                    "user", user,
                    "orders", orders
            ));
        };
    }

    /**
     * 创建用户DataFetcher
     */
    @SuppressWarnings("unchecked")
    private DataFetcher<Mono<Map<String, Object>>> createUserDataFetcher() {
        return dataFetchingEnvironment -> {
            Map<String, Object> input = dataFetchingEnvironment.getArgument("input");
            log.debug("GraphQL创建用户 - input: {}", input);

            String name = (String) input.get("name");
            String email = (String) input.get("email");
            Integer age = (Integer) input.get("age");

            return Mono.just(Map.of(
                    "id", String.valueOf(System.currentTimeMillis()),
                    "name", name,
                    "email", email,
                    "age", age != null ? age : 0,
                    "createdAt", "2026-01-01T00:00:00Z",
                    "updatedAt", "2026-01-01T00:00:00Z"
            ));
        };
    }

    /**
     * 更新用户DataFetcher
     */
    @SuppressWarnings("unchecked")
    private DataFetcher<Mono<Map<String, Object>>> updateUserDataFetcher() {
        return dataFetchingEnvironment -> {
            String id = dataFetchingEnvironment.getArgument("id");
            Map<String, Object> input = dataFetchingEnvironment.getArgument("input");
            log.debug("GraphQL更新用户 - id: {}, input: {}", id, input);

            String name = (String) input.getOrDefault("name", "User" + id);
            String email = (String) input.getOrDefault("email", "user" + id + "@example.com");
            Integer age = (Integer) input.getOrDefault("age", 25);

            return Mono.just(Map.of(
                    "id", id,
                    "name", name,
                    "email", email,
                    "age", age,
                    "createdAt", "2026-01-01T00:00:00Z",
                    "updatedAt", "2026-01-01T00:00:00Z"
            ));
        };
    }

    /**
     * 删除用户DataFetcher
     */
    private DataFetcher<Mono<Map<String, Object>>> deleteUserDataFetcher() {
        return dataFetchingEnvironment -> {
            String id = dataFetchingEnvironment.getArgument("id");
            log.debug("GraphQL删除用户 - id: {}", id);

            return Mono.just(Map.of(
                    "success", true,
                    "message", "用户删除成功"
            ));
        };
    }

    /**
     * 创建订单DataFetcher
     */
    @SuppressWarnings("unchecked")
    private DataFetcher<Mono<Map<String, Object>>> createOrderDataFetcher() {
        return dataFetchingEnvironment -> {
            Map<String, Object> input = dataFetchingEnvironment.getArgument("input");
            log.debug("GraphQL创建订单 - input: {}", input);

            String userId = (String) input.get("userId");
            String address = (String) input.get("address");
            List<Map<String, Object>> itemInputs = (List<Map<String, Object>>) input.get("items");

            List<Map<String, Object>> items = new ArrayList<>();
            double totalAmount = 0;
            for (Map<String, Object> itemInput : itemInputs) {
                int quantity = (Integer) itemInput.get("quantity");
                double price = (Double) itemInput.get("price");
                totalAmount += quantity * price;
                items.add(Map.of(
                        "productId", itemInput.get("productId"),
                        "productName", itemInput.get("productName"),
                        "quantity", quantity,
                        "price", price
                ));
            }

            return Mono.just(Map.of(
                    "orderId", "ORD" + System.currentTimeMillis(),
                    "userId", userId,
                    "items", items,
                    "totalAmount", totalAmount,
                    "status", "CREATED",
                    "address", address,
                    "createdAt", "2026-01-01T00:00:00Z",
                    "updatedAt", "2026-01-01T00:00:00Z"
            ));
        };
    }

    /**
     * 更新订单状态DataFetcher
     */
    private DataFetcher<Mono<Map<String, Object>>> updateOrderStatusDataFetcher() {
        return dataFetchingEnvironment -> {
            String orderId = dataFetchingEnvironment.getArgument("orderId");
            String status = dataFetchingEnvironment.getArgument("status");
            log.debug("GraphQL更新订单状态 - orderId: {}, status: {}", orderId, status);

            List<Map<String, Object>> items = List.of(
                    Map.of(
                            "productId", "P001",
                            "productName", "Product 1",
                            "quantity", 2,
                            "price", 99.99
                    )
            );

            return Mono.just(Map.of(
                    "orderId", orderId,
                    "userId", "1",
                    "items", items,
                    "totalAmount", 199.98,
                    "status", status,
                    "address", "北京市朝阳区",
                    "createdAt", "2026-01-01T00:00:00Z",
                    "updatedAt", "2026-01-01T00:00:00Z"
            ));
        };
    }

    // ==================== 错误处理 ====================

    /**
     * 错误处理
     */
    private Mono<ServerResponse> handleError(Throwable throwable) {
        log.error("GraphQL处理失败: {}", throwable.getMessage(), throwable);

        int statusCode = 500;
        String errorCode = "GRAPHQL_ERROR";
        String errorMessage = throwable.getMessage();

        if (throwable instanceof IllegalArgumentException) {
            statusCode = 400;
            errorCode = "INVALID_REQUEST";
        }

        Map<String, Object> errorBody = Map.of(
                "errors", List.of(Map.of(
                        "code", errorCode,
                        "message", errorMessage
                )),
                "data", null
        );

        return ServerResponse.status(statusCode)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(errorBody);
    }

    /**
     * 返回坏请求响应
     */
    private Mono<ServerResponse> badRequest(String message) {
        log.warn("GraphQL坏请求: {}", message);

        Map<String, Object> errorBody = Map.of(
                "errors", List.of(Map.of(
                        "code", "BAD_REQUEST",
                        "message", message
                )),
                "data", null
        );

        return ServerResponse.badRequest()
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(errorBody);
    }

    /**
     * GraphQL请求记录
     */
    private record GraphQLRequest(String query, String operationName, Map<String, Object> variables) {
    }
}
