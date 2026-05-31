package com.schemaregistry.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.schemaregistry.model.GeneratedCode;
import com.schemaregistry.model.SchemaType;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class CodeGenerationService {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private static final String DEFAULT_PACKAGE = "com.schemaregistry.generated";

    public List<GeneratedCode> generateAllLanguages(String schemaText, SchemaType type, String className, String packageName) {
        List<GeneratedCode> codes = new ArrayList<>();
        String pkg = packageName != null ? packageName : DEFAULT_PACKAGE;

        codes.add(generateJavaCode(schemaText, type, className, pkg));
        codes.add(generatePythonCode(schemaText, type, className));
        codes.add(generateGoCode(schemaText, type, className));

        return codes;
    }

    public GeneratedCode generateJavaCode(String schemaText, SchemaType type, String className, String packageName) {
        String pkg = packageName != null ? packageName : DEFAULT_PACKAGE;
        String name = className != null ? className : extractClassName(schemaText, type);
        StringBuilder code = new StringBuilder();

        code.append("package ").append(pkg).append(";\n\n");
        code.append("import java.util.Objects;\n");
        code.append("import com.fasterxml.jackson.annotation.JsonProperty;\n\n");

        switch (type) {
            case AVRO:
                generateJavaFromAvro(schemaText, name, code);
                break;
            case JSON_SCHEMA:
                generateJavaFromJsonSchema(schemaText, name, code);
                break;
            case PROTOBUF:
                generateJavaFromProtobuf(schemaText, name, code);
                break;
        }

        return GeneratedCode.builder()
                .language("Java")
                .fileName(name + ".java")
                .code(code.toString())
                .packageName(pkg)
                .className(name)
                .build();
    }

    private void generateJavaFromAvro(String schemaText, String className, StringBuilder code) {
        try {
            JsonNode schema = objectMapper.readTree(schemaText);
            JsonNode fields = schema.path("fields");

            code.append("public class ").append(className).append(" {\n\n");

            List<Map.Entry<String, String>> fieldList = new ArrayList<>();

            if (fields.isArray()) {
                for (JsonNode field : fields) {
                    String fieldName = field.path("name").asText();
                    String fieldType = mapAvroTypeToJava(field.path("type"));
                    fieldList.add(new AbstractMap.SimpleEntry<>(fieldName, fieldType));

                    code.append("    @JsonProperty(\"").append(fieldName).append("\")\n");
                    code.append("    private ").append(fieldType).append(" ").append(fieldName).append(";\n\n");
                }
            }

            code.append("    public ").append(className).append("() {}\n\n");

            code.append("    public ").append(className).append("(");
            for (int i = 0; i < fieldList.size(); i++) {
                if (i > 0) code.append(", ");
                code.append(fieldList.get(i).getValue()).append(" ").append(fieldList.get(i).getKey());
            }
            code.append(") {\n");
            for (Map.Entry<String, String> field : fieldList) {
                code.append("        this.").append(field.getKey()).append(" = ").append(field.getKey()).append(";\n");
            }
            code.append("    }\n\n");

            for (Map.Entry<String, String> field : fieldList) {
                String getterName = "get" + capitalize(field.getKey());
                String setterName = "set" + capitalize(field.getKey());
                code.append("    public ").append(field.getValue()).append(" ").append(getterName).append("() {\n");
                code.append("        return ").append(field.getKey()).append(";\n");
                code.append("    }\n\n");
                code.append("    public void ").append(setterName).append("(").append(field.getValue()).append(" ").append(field.getKey()).append(") {\n");
                code.append("        this.").append(field.getKey()).append(" = ").append(field.getKey()).append(";\n");
                code.append("    }\n\n");
            }

            generateEqualsAndHashCode(className, fieldList, code);
            generateToString(className, fieldList, code);

            code.append("}\n");
        } catch (Exception e) {
            throw new RuntimeException("Failed to generate Java code from Avro schema: " + e.getMessage(), e);
        }
    }

    private void generateJavaFromJsonSchema(String schemaText, String className, StringBuilder code) {
        try {
            JsonNode schema = objectMapper.readTree(schemaText);
            JsonNode properties = schema.path("properties");

            code.append("public class ").append(className).append(" {\n\n");

            List<Map.Entry<String, String>> fieldList = new ArrayList<>();

            if (properties.isObject()) {
                Iterator<Map.Entry<String, JsonNode>> fields = properties.fields();
                while (fields.hasNext()) {
                    Map.Entry<String, JsonNode> field = fields.next();
                    String fieldName = field.getKey();
                    String fieldType = mapJsonTypeToJava(field.getValue().path("type").asText());
                    fieldList.add(new AbstractMap.SimpleEntry<>(fieldName, fieldType));

                    code.append("    @JsonProperty(\"").append(fieldName).append("\")\n");
                    code.append("    private ").append(fieldType).append(" ").append(fieldName).append(";\n\n");
                }
            }

            code.append("    public ").append(className).append("() {}\n\n");

            generateGettersSetters(fieldList, code);
            generateEqualsAndHashCode(className, fieldList, code);
            generateToString(className, fieldList, code);

            code.append("}\n");
        } catch (Exception e) {
            throw new RuntimeException("Failed to generate Java code from JSON Schema: " + e.getMessage(), e);
        }
    }

    private void generateJavaFromProtobuf(String schemaText, String className, StringBuilder code) {
        List<Map.Entry<String, String>> fieldList = extractProtobufFields(schemaText);

        code.append("public class ").append(className).append(" {\n\n");

        for (Map.Entry<String, String> field : fieldList) {
            code.append("    @JsonProperty(\"").append(field.getKey()).append("\")\n");
            code.append("    private ").append(field.getValue()).append(" ").append(field.getKey()).append(";\n\n");
        }

        code.append("    public ").append(className).append("() {}\n\n");

        generateGettersSetters(fieldList, code);
        generateEqualsAndHashCode(className, fieldList, code);
        generateToString(className, fieldList, code);

        code.append("}\n");
    }

    private void generateGettersSetters(List<Map.Entry<String, String>> fieldList, StringBuilder code) {
        for (Map.Entry<String, String> field : fieldList) {
            String getterName = "get" + capitalize(field.getKey());
            String setterName = "set" + capitalize(field.getKey());
            code.append("    public ").append(field.getValue()).append(" ").append(getterName).append("() {\n");
            code.append("        return ").append(field.getKey()).append(";\n");
            code.append("    }\n\n");
            code.append("    public void ").append(setterName).append("(").append(field.getValue()).append(" ").append(field.getKey()).append(") {\n");
            code.append("        this.").append(field.getKey()).append(" = ").append(field.getKey()).append(";\n");
            code.append("    }\n\n");
        }
    }

    private void generateEqualsAndHashCode(String className, List<Map.Entry<String, String>> fieldList, StringBuilder code) {
        code.append("    @Override\n");
        code.append("    public boolean equals(Object o) {\n");
        code.append("        if (this == o) return true;\n");
        code.append("        if (o == null || getClass() != o.getClass()) return false;\n");
        code.append("        ").append(className).append(" that = (").append(className).append(") o;\n");
        if (fieldList.isEmpty()) {
            code.append("        return true;\n");
        } else {
            code.append("        return ");
            for (int i = 0; i < fieldList.size(); i++) {
                if (i > 0) code.append(" &&\n                ");
                String fieldName = fieldList.get(i).getKey();
                code.append("Objects.equals(").append(fieldName).append(", that.").append(fieldName).append(")");
            }
            code.append(";\n");
        }
        code.append("    }\n\n");

        code.append("    @Override\n");
        code.append("    public int hashCode() {\n");
        code.append("        return Objects.hash(");
        for (int i = 0; i < fieldList.size(); i++) {
            if (i > 0) code.append(", ");
            code.append(fieldList.get(i).getKey());
        }
        code.append(");\n");
        code.append("    }\n\n");
    }

    private void generateToString(String className, List<Map.Entry<String, String>> fieldList, StringBuilder code) {
        code.append("    @Override\n");
        code.append("    public String toString() {\n");
        code.append("        return \"").append(className).append("{\" +\n");
        for (int i = 0; i < fieldList.size(); i++) {
            String fieldName = fieldList.get(i).getKey();
            code.append("                \"").append(fieldName).append("='\" + ").append(fieldName).append(" + '\\''");
            if (i < fieldList.size() - 1) code.append(" +\n                \",");
            code.append("\n");
        }
        code.append("                '}';\n");
        code.append("    }\n\n");
    }

    public GeneratedCode generatePythonCode(String schemaText, SchemaType type, String className) {
        String name = className != null ? className : extractClassName(schemaText, type);
        StringBuilder code = new StringBuilder();

        code.append("from dataclasses import dataclass\n");
        code.append("from typing import Optional, List, Dict, Any\n");
        code.append("import json\n\n");

        switch (type) {
            case AVRO:
                generatePythonFromAvro(schemaText, name, code);
                break;
            case JSON_SCHEMA:
                generatePythonFromJsonSchema(schemaText, name, code);
                break;
            case PROTOBUF:
                generatePythonFromProtobuf(schemaText, name, code);
                break;
        }

        return GeneratedCode.builder()
                .language("Python")
                .fileName(toSnakeCase(name) + ".py")
                .code(code.toString())
                .className(name)
                .build();
    }

    private void generatePythonFromAvro(String schemaText, String className, StringBuilder code) {
        try {
            JsonNode schema = objectMapper.readTree(schemaText);
            JsonNode fields = schema.path("fields");

            code.append("@dataclass\n");
            code.append("class ").append(className).append(":\n");

            List<String> fieldList = new ArrayList<>();

            if (fields.isArray()) {
                for (JsonNode field : fields) {
                    String fieldName = field.path("name").asText();
                    String fieldType = mapAvroTypeToPython(field.path("type"));
                    String defaultVal = extractPythonDefault(field);
                    fieldList.add(fieldName);

                    if (defaultVal != null) {
                        code.append("    ").append(fieldName).append(": ").append(fieldType).append(" = ").append(defaultVal).append("\n");
                    } else {
                        code.append("    ").append(fieldName).append(": ").append(fieldType).append("\n");
                    }
                }
            }

            code.append("\n    def to_dict(self) -> dict:\n");
            code.append("        return {\n");
            for (String field : fieldList) {
                code.append("            '").append(field).append("': self.").append(field).append(",\n");
            }
            code.append("        }\n\n");

            code.append("    @classmethod\n");
            code.append("    def from_dict(cls, data: dict) -> '").append(className).append("':\n");
            code.append("        return cls(\n");
            for (int i = 0; i < fieldList.size(); i++) {
                String field = fieldList.get(i);
                code.append("            ").append(field).append("=data.get('").append(field).append("')");
                if (i < fieldList.size() - 1) code.append(",");
                code.append("\n");
            }
            code.append("        )\n\n");

            code.append("    def to_json(self) -> str:\n");
            code.append("        return json.dumps(self.to_dict())\n\n");

            code.append("    @classmethod\n");
            code.append("    def from_json(cls, json_str: str) -> '").append(className).append("':\n");
            code.append("        return cls.from_dict(json.loads(json_str))\n");

        } catch (Exception e) {
            throw new RuntimeException("Failed to generate Python code from Avro schema: " + e.getMessage(), e);
        }
    }

    private void generatePythonFromJsonSchema(String schemaText, String className, StringBuilder code) {
        try {
            JsonNode schema = objectMapper.readTree(schemaText);
            JsonNode properties = schema.path("properties");

            code.append("@dataclass\n");
            code.append("class ").append(className).append(":\n");

            List<String> fieldList = new ArrayList<>();

            if (properties.isObject()) {
                Iterator<Map.Entry<String, JsonNode>> fields = properties.fields();
                while (fields.hasNext()) {
                    Map.Entry<String, JsonNode> field = fields.next();
                    String fieldName = field.getKey();
                    String fieldType = mapJsonTypeToPython(field.getValue().path("type").asText());
                    fieldList.add(fieldName);
                    code.append("    ").append(fieldName).append(": Optional[").append(fieldType).append("] = None\n");
                }
            }

            generatePythonUtilityMethods(className, fieldList, code);
        } catch (Exception e) {
            throw new RuntimeException("Failed to generate Python code from JSON Schema: " + e.getMessage(), e);
        }
    }

    private void generatePythonFromProtobuf(String schemaText, String className, StringBuilder code) {
        List<Map.Entry<String, String>> protoFields = extractProtobufFields(schemaText);

        code.append("@dataclass\n");
        code.append("class ").append(className).append(":\n");

        List<String> fieldList = new ArrayList<>();

        for (Map.Entry<String, String> field : protoFields) {
            fieldList.add(field.getKey());
            String pyType = mapProtobufTypeToPython(field.getValue());
            code.append("    ").append(field.getKey()).append(": Optional[").append(pyType).append("] = None\n");
        }

        generatePythonUtilityMethods(className, fieldList, code);
    }

    private void generatePythonUtilityMethods(String className, List<String> fieldList, StringBuilder code) {
        code.append("\n    def to_dict(self) -> dict:\n");
        code.append("        return {\n");
        for (String field : fieldList) {
            code.append("            '").append(field).append("': self.").append(field).append(",\n");
        }
        code.append("        }\n\n");

        code.append("    @classmethod\n");
        code.append("    def from_dict(cls, data: dict) -> '").append(className).append("':\n");
        code.append("        return cls(\n");
        for (int i = 0; i < fieldList.size(); i++) {
            String field = fieldList.get(i);
            code.append("            ").append(field).append("=data.get('").append(field).append("')");
            if (i < fieldList.size() - 1) code.append(",");
            code.append("\n");
        }
        code.append("        )\n\n");

        code.append("    def to_json(self) -> str:\n");
        code.append("        return json.dumps(self.to_dict())\n\n");

        code.append("    @classmethod\n");
        code.append("    def from_json(cls, json_str: str) -> '").append(className).append("':\n");
        code.append("        return cls.from_dict(json.loads(json_str))\n");
    }

    public GeneratedCode generateGoCode(String schemaText, SchemaType type, String className) {
        String name = className != null ? className : extractClassName(schemaText, type);
        StringBuilder code = new StringBuilder();

        code.append("package generated\n\n");
        code.append("import (\n");
        code.append("    \"encoding/json\"\n");
        code.append("    \"fmt\"\n");
        code.append(")\n\n");

        switch (type) {
            case AVRO:
                generateGoFromAvro(schemaText, name, code);
                break;
            case JSON_SCHEMA:
                generateGoFromJsonSchema(schemaText, name, code);
                break;
            case PROTOBUF:
                generateGoFromProtobuf(schemaText, name, code);
                break;
        }

        return GeneratedCode.builder()
                .language("Go")
                .fileName(toSnakeCase(name) + ".go")
                .code(code.toString())
                .className(name)
                .build();
    }

    private void generateGoFromAvro(String schemaText, String className, StringBuilder code) {
        try {
            JsonNode schema = objectMapper.readTree(schemaText);
            JsonNode fields = schema.path("fields");

            code.append("type ").append(className).append(" struct {\n");

            List<String> fieldList = new ArrayList<>();

            if (fields.isArray()) {
                for (JsonNode field : fields) {
                    String fieldName = field.path("name").asText();
                    String fieldType = mapAvroTypeToGo(field.path("type"));
                    fieldList.add(fieldName);
                    code.append("    ").append(capitalize(fieldName)).append(" ").append(fieldType)
                            .append(" `json:\"").append(fieldName).append("\"`\n");
                }
            }

            code.append("}\n\n");

            generateGoUtilityMethods(className, fieldList, code);
        } catch (Exception e) {
            throw new RuntimeException("Failed to generate Go code from Avro schema: " + e.getMessage(), e);
        }
    }

    private void generateGoFromJsonSchema(String schemaText, String className, StringBuilder code) {
        try {
            JsonNode schema = objectMapper.readTree(schemaText);
            JsonNode properties = schema.path("properties");

            code.append("type ").append(className).append(" struct {\n");

            List<String> fieldList = new ArrayList<>();

            if (properties.isObject()) {
                Iterator<Map.Entry<String, JsonNode>> fields = properties.fields();
                while (fields.hasNext()) {
                    Map.Entry<String, JsonNode> field = fields.next();
                    String fieldName = field.getKey();
                    String fieldType = mapJsonTypeToGo(field.getValue().path("type").asText());
                    fieldList.add(fieldName);
                    code.append("    ").append(capitalize(fieldName)).append(" ").append(fieldType)
                            .append(" `json:\"").append(fieldName).append(",omitempty\"`\n");
                }
            }

            code.append("}\n\n");

            generateGoUtilityMethods(className, fieldList, code);
        } catch (Exception e) {
            throw new RuntimeException("Failed to generate Go code from JSON Schema: " + e.getMessage(), e);
        }
    }

    private void generateGoFromProtobuf(String schemaText, String className, StringBuilder code) {
        List<Map.Entry<String, String>> protoFields = extractProtobufFields(schemaText);

        code.append("type ").append(className).append(" struct {\n");

        List<String> fieldList = new ArrayList<>();

        for (Map.Entry<String, String> field : protoFields) {
            fieldList.add(field.getKey());
            String goType = mapProtobufTypeToGo(field.getValue());
            code.append("    ").append(capitalize(field.getKey())).append(" ").append(goType)
                    .append(" `json:\"").append(field.getKey()).append(",omitempty\"`\n");
        }

        code.append("}\n\n");

        generateGoUtilityMethods(className, fieldList, code);
    }

    private void generateGoUtilityMethods(String className, List<String> fieldList, StringBuilder code) {
        code.append("func (m *").append(className).append(") ToJSON() ([]byte, error) {\n");
        code.append("    return json.Marshal(m)\n");
        code.append("}\n\n");

        code.append("func (m *").append(className).append(") FromJSON(data []byte) error {\n");
        code.append("    return json.Unmarshal(data, m)\n");
        code.append("}\n\n");

        code.append("func (m *").append(className).append(") String() string {\n");
        code.append("    return fmt.Sprintf(\"").append(className).append("{");
        for (int i = 0; i < fieldList.size(); i++) {
            if (i > 0) code.append(" ");
            code.append(fieldList.get(i)).append(": %+v");
        }
        code.append("}\", ");
        for (int i = 0; i < fieldList.size(); i++) {
            if (i > 0) code.append(", ");
            code.append("m.").append(capitalize(fieldList.get(i)));
        }
        code.append(")\n");
        code.append("}\n");
    }

    private String mapAvroTypeToJava(JsonNode typeNode) {
        if (typeNode.isTextual()) {
            return mapSimpleAvroTypeToJava(typeNode.asText());
        } else if (typeNode.isArray()) {
            StringBuilder union = new StringBuilder();
            boolean hasNull = false;
            for (JsonNode type : typeNode) {
                if ("null".equals(type.asText())) {
                    hasNull = true;
                } else {
                    union.append(mapSimpleAvroTypeToJava(type.asText()));
                }
            }
            return hasNull ? union.toString() : union.toString();
        }
        return "Object";
    }

    private String mapSimpleAvroTypeToJava(String type) {
        switch (type) {
            case "string": return "String";
            case "int": return "Integer";
            case "long": return "Long";
            case "float": return "Float";
            case "double": return "Double";
            case "boolean": return "Boolean";
            case "bytes": return "byte[]";
            case "array": return "List<Object>";
            case "map": return "Map<String, Object>";
            default: return "Object";
        }
    }

    private String mapJsonTypeToJava(String type) {
        switch (type) {
            case "string": return "String";
            case "integer": return "Integer";
            case "number": return "Double";
            case "boolean": return "Boolean";
            case "array": return "List<Object>";
            case "object": return "Map<String, Object>";
            default: return "Object";
        }
    }

    private String mapAvroTypeToPython(JsonNode typeNode) {
        if (typeNode.isTextual()) {
            return mapSimpleAvroTypeToPython(typeNode.asText());
        } else if (typeNode.isArray()) {
            boolean hasNull = false;
            String mainType = "Any";
            for (JsonNode type : typeNode) {
                if ("null".equals(type.asText())) {
                    hasNull = true;
                } else {
                    mainType = mapSimpleAvroTypeToPython(type.asText());
                }
            }
            return hasNull ? "Optional[" + mainType + "]" : mainType;
        }
        return "Any";
    }

    private String mapSimpleAvroTypeToPython(String type) {
        switch (type) {
            case "string": return "str";
            case "int":
            case "long": return "int";
            case "float":
            case "double": return "float";
            case "boolean": return "bool";
            case "bytes": return "bytes";
            case "array": return "List[Any]";
            case "map": return "Dict[str, Any]";
            default: return "Any";
        }
    }

    private String mapJsonTypeToPython(String type) {
        switch (type) {
            case "string": return "str";
            case "integer": return "int";
            case "number": return "float";
            case "boolean": return "bool";
            case "array": return "List[Any]";
            case "object": return "Dict[str, Any]";
            default: return "Any";
        }
    }

    private String mapProtobufTypeToPython(String type) {
        switch (type.toLowerCase()) {
            case "string": return "str";
            case "int32":
            case "int64":
            case "uint32":
            case "uint64":
            case "sint32":
            case "sint64": return "int";
            case "float":
            case "double": return "float";
            case "bool": return "bool";
            case "bytes": return "bytes";
            default: return "Any";
        }
    }

    private String mapAvroTypeToGo(JsonNode typeNode) {
        if (typeNode.isTextual()) {
            return mapSimpleAvroTypeToGo(typeNode.asText());
        } else if (typeNode.isArray()) {
            boolean hasNull = false;
            String mainType = "interface{}";
            for (JsonNode type : typeNode) {
                if ("null".equals(type.asText())) {
                    hasNull = true;
                } else {
                    mainType = mapSimpleAvroTypeToGo(type.asText());
                }
            }
            return hasNull ? "*" + mainType : mainType;
        }
        return "interface{}";
    }

    private String mapSimpleAvroTypeToGo(String type) {
        switch (type) {
            case "string": return "string";
            case "int": return "int32";
            case "long": return "int64";
            case "float": return "float32";
            case "double": return "float64";
            case "boolean": return "bool";
            case "bytes": return "[]byte";
            case "array": return "[]interface{}";
            case "map": return "map[string]interface{}";
            default: return "interface{}";
        }
    }

    private String mapJsonTypeToGo(String type) {
        switch (type) {
            case "string": return "string";
            case "integer": return "int64";
            case "number": return "float64";
            case "boolean": return "bool";
            case "array": return "[]interface{}";
            case "object": return "map[string]interface{}";
            default: return "interface{}";
        }
    }

    private String mapProtobufTypeToGo(String type) {
        switch (type.toLowerCase()) {
            case "string": return "string";
            case "int32":
            case "sint32": return "int32";
            case "int64":
            case "sint64":
            case "uint64": return "int64";
            case "uint32": return "uint32";
            case "float": return "float32";
            case "double": return "float64";
            case "bool": return "bool";
            case "bytes": return "[]byte";
            default: return "interface{}";
        }
    }

    private String extractPythonDefault(JsonNode field) {
        JsonNode defaultNode = field.path("default");
        if (!defaultNode.isMissingNode()) {
            if (defaultNode.isNull()) {
                return "None";
            } else if (defaultNode.isTextual()) {
                return "\"" + defaultNode.asText() + "\"";
            } else {
                return defaultNode.toString();
            }
        }
        return null;
    }

    private String extractClassName(String schemaText, SchemaType type) {
        try {
            switch (type) {
                case AVRO:
                case JSON_SCHEMA:
                    JsonNode schema = objectMapper.readTree(schemaText);
                    if (schema.has("name")) {
                        return capitalize(schema.get("name").asText());
                    }
                    break;
                case PROTOBUF:
                    Pattern messagePattern = Pattern.compile("message\\s+(\\w+)");
                    Matcher matcher = messagePattern.matcher(schemaText);
                    if (matcher.find()) {
                        return capitalize(matcher.group(1));
                    }
                    break;
            }
        } catch (Exception e) {
            // ignore
        }
        return "SchemaClass";
    }

    private List<Map.Entry<String, String>> extractProtobufFields(String schemaText) {
        List<Map.Entry<String, String>> fields = new ArrayList<>();
        Pattern fieldPattern = Pattern.compile("(?:required|optional|repeated)\\s+(\\w+)\\s+(\\w+)\\s*=\\s*\\d+");
        Matcher matcher = fieldPattern.matcher(schemaText);
        while (matcher.find()) {
            fields.add(new AbstractMap.SimpleEntry<>(matcher.group(2), matcher.group(1)));
        }
        return fields;
    }

    private String capitalize(String str) {
        if (str == null || str.isEmpty()) return str;
        return str.substring(0, 1).toUpperCase() + str.substring(1);
    }

    private String toSnakeCase(String str) {
        if (str == null || str.isEmpty()) return str;
        return str.replaceAll("([a-z])([A-Z])", "$1_$2").toLowerCase();
    }
}
