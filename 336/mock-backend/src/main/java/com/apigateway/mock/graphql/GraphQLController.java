package com.apigateway.mock.graphql;

import graphql.ExecutionInput;
import graphql.ExecutionResult;
import graphql.GraphQL;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/graphql")
@RequiredArgsConstructor
public class GraphQLController {

    private final GraphQL graphQL;

    @PostMapping
    public ResponseEntity<Map<String, Object>> execute(@RequestBody Map<String, Object> request) {
        String query = (String) request.get("query");
        Map<String, Object> variables = (Map<String, Object>) request.get("variables");

        log.info("GraphQL请求: query={}, variables={}", query, variables);

        ExecutionInput executionInput = ExecutionInput.newExecutionInput()
                .query(query)
                .variables(variables != null ? variables : Map.of())
                .build();

        ExecutionResult result = graphQL.execute(executionInput);

        return ResponseEntity.ok(result.toSpecification());
    }

    @GetMapping
    public ResponseEntity<Map<String, Object>> executeGet(
            @RequestParam String query,
            @RequestParam(required = false) Map<String, Object> variables) {

        log.info("GraphQL GET请求: query={}, variables={}", query, variables);

        ExecutionInput executionInput = ExecutionInput.newExecutionInput()
                .query(query)
                .variables(variables != null ? variables : Map.of())
                .build();

        ExecutionResult result = graphQL.execute(executionInput);

        return ResponseEntity.ok(result.toSpecification());
    }
}
