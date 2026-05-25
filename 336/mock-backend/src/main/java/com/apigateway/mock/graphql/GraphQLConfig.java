package com.apigateway.mock.graphql;

import graphql.GraphQL;
import graphql.schema.GraphQLSchema;
import graphql.schema.idl.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;

import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;

@Slf4j
@Configuration
@RequiredArgsConstructor
public class GraphQLConfig {

    private final UserDataFetcher userDataFetcher;
    private final OrderDataFetcher orderDataFetcher;

    @Bean
    public GraphQLSchema graphQLSchema() throws IOException {
        ClassPathResource resource = new ClassPathResource("graphql/schema.graphqls");
        try (Reader reader = new InputStreamReader(resource.getInputStream())) {
            TypeDefinitionRegistry typeRegistry = new SchemaParser().parse(reader);
            RuntimeWiring wiring = buildRuntimeWiring();
            return new SchemaGenerator().makeExecutableSchema(typeRegistry, wiring);
        }
    }

    private RuntimeWiring buildRuntimeWiring() {
        return RuntimeWiring.newRuntimeWiring()
                .type(TypeRuntimeWiring.newTypeWiring("Query")
                        .dataFetcher("user", userDataFetcher.getUserById())
                        .dataFetcher("users", userDataFetcher.listUsers())
                        .dataFetcher("userCount", userDataFetcher.userCount())
                        .dataFetcher("order", orderDataFetcher.getOrderById())
                        .dataFetcher("orders", orderDataFetcher.listOrders())
                        .dataFetcher("orderCount", orderDataFetcher.orderCount())
                )
                .type(TypeRuntimeWiring.newTypeWiring("Mutation")
                        .dataFetcher("createUser", userDataFetcher.createUser())
                        .dataFetcher("updateUser", userDataFetcher.updateUser())
                        .dataFetcher("deleteUser", userDataFetcher.deleteUser())
                        .dataFetcher("createOrder", orderDataFetcher.createOrder())
                        .dataFetcher("updateOrderStatus", orderDataFetcher.updateOrderStatus())
                )
                .build();
    }

    @Bean
    public GraphQL graphQL(GraphQLSchema schema) {
        return GraphQL.newGraphQL(schema).build();
    }
}
