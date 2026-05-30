package com.hotconfig.processor;

import com.hotconfig.annotation.HotConfig;
import com.hotconfig.annotation.HotValue;
import com.squareup.javapoet.*;

import javax.annotation.processing.*;
import javax.lang.model.SourceVersion;
import javax.lang.model.element.*;
import javax.lang.model.type.TypeMirror;
import javax.tools.Diagnostic;
import java.io.IOException;
import java.util.*;

@SupportedAnnotationTypes("com.hotconfig.annotation.HotConfig")
@SupportedSourceVersion(SourceVersion.RELEASE_11)
public class HotConfigAnnotationProcessor extends AbstractProcessor {

    private Filer filer;
    private Messager messager;

    @Override
    public synchronized void init(ProcessingEnvironment processingEnv) {
        super.init(processingEnv);
        this.filer = processingEnv.getFiler();
        this.messager = processingEnv.getMessager();
    }

    @Override
    public boolean process(Set<? extends TypeElement> annotations, RoundEnvironment roundEnv) {
        for (Element element : roundEnv.getElementsAnnotatedWith(HotConfig.class)) {
            if (element.getKind() != ElementKind.CLASS) {
                messager.printMessage(Diagnostic.Kind.ERROR, "@HotConfig 只能标注在类上", element);
                continue;
            }
            TypeElement classElement = (TypeElement) element;
            try {
                generateProxyClass(classElement);
            } catch (Exception e) {
                messager.printMessage(Diagnostic.Kind.ERROR, "生成代理类失败: " + e.getMessage(), element);
            }
        }
        return true;
    }

    private void generateProxyClass(TypeElement classElement) throws IOException {
        HotConfig hotConfig = classElement.getAnnotation(HotConfig.class);
        String className = classElement.getSimpleName().toString();
        String packageName = processingEnv.getElementUtils().getPackageOf(classElement).getQualifiedName().toString();
        String proxyClassName = className + "HotConfigProxy";

        ClassName proxyClass = ClassName.get(packageName, proxyClassName);
        ClassName superClass = ClassName.get(packageName, className);

        List<ExecutableElement> getterMethods = findGetterMethods(classElement);
        List<VariableElement> hotValueFields = findHotValueFields(classElement);

        MethodSpec.Builder constructorBuilder = MethodSpec.constructorBuilder()
                .addModifiers(Modifier.PUBLIC)
                .addParameter(ClassName.get("com.hotconfig.core", "ConfigManager"), "configManager")
                .addStatement("this.configManager = configManager");

        FieldSpec configManagerField = FieldSpec.builder(
                ClassName.get("com.hotconfig.core", "ConfigManager"),
                "configManager",
                Modifier.PRIVATE,
                Modifier.FINAL
        ).build();

        FieldSpec prefixField = FieldSpec.builder(
                String.class,
                "prefix",
                Modifier.PRIVATE,
                Modifier.FINAL
        ).initializer("$S", hotConfig.prefix()).build();

        TypeSpec.Builder classBuilder = TypeSpec.classBuilder(proxyClassName)
                .addModifiers(Modifier.PUBLIC)
                .superclass(superClass)
                .addField(configManagerField)
                .addField(prefixField)
                .addMethod(constructorBuilder.build());

        for (VariableElement field : hotValueFields) {
            HotValue hotValue = field.getAnnotation(HotValue.class);
            String configKey = hotValue.value();
            String fullKey = hotConfig.prefix().isEmpty() ? configKey : hotConfig.prefix() + "." + configKey;
            TypeMirror fieldType = field.asType();
            String fieldName = field.getSimpleName().toString();
            String getterName = "get" + capitalize(fieldName);

            MethodSpec getterMethod = MethodSpec.methodBuilder(getterName)
                    .addModifiers(Modifier.PUBLIC)
                    .returns(TypeName.get(fieldType))
                    .addStatement("$T value = ($T) configManager.getValue($S, $T.class, $S)",
                            TypeName.get(fieldType),
                            TypeName.get(fieldType),
                            fullKey,
                            TypeName.get(fieldType),
                            hotValue.defaultValue())
                    .addStatement("return value")
                    .build();

            classBuilder.addMethod(getterMethod);
        }

        for (ExecutableElement getter : getterMethods) {
            String methodName = getter.getSimpleName().toString();
            TypeMirror returnType = getter.getReturnType();
            String fieldName = extractFieldName(methodName);
            VariableElement field = findFieldByName(classElement, fieldName);

            if (field != null && field.getAnnotation(HotValue.class) != null) {
                continue;
            }

            MethodSpec overrideGetter = MethodSpec.overriding(getter)
                    .addStatement("return super.$N()", methodName)
                    .build();
            classBuilder.addMethod(overrideGetter);
        }

        JavaFile javaFile = JavaFile.builder(packageName, classBuilder.build())
                .addFileComment("Generated by HotConfig Annotation Processor. DO NOT MODIFY!")
                .build();

        javaFile.writeTo(filer);
        messager.printMessage(Diagnostic.Kind.NOTE, "Generated proxy class: " + packageName + "." + proxyClassName);
    }

    private List<ExecutableElement> findGetterMethods(TypeElement classElement) {
        List<ExecutableElement> getters = new ArrayList<>();
        for (Element enclosed : classElement.getEnclosedElements()) {
            if (enclosed.getKind() == ElementKind.METHOD) {
                ExecutableElement method = (ExecutableElement) enclosed;
                String name = method.getSimpleName().toString();
                if (name.startsWith("get") && name.length() > 3
                        && method.getParameters().isEmpty()
                        && !method.getReturnType().toString().equals("void")) {
                    getters.add(method);
                }
            }
        }
        return getters;
    }

    private List<VariableElement> findHotValueFields(TypeElement classElement) {
        List<VariableElement> fields = new ArrayList<>();
        for (Element enclosed : classElement.getEnclosedElements()) {
            if (enclosed.getKind() == ElementKind.FIELD) {
                VariableElement field = (VariableElement) enclosed;
                if (field.getAnnotation(HotValue.class) != null) {
                    fields.add(field);
                }
            }
        }
        return fields;
    }

    private VariableElement findFieldByName(TypeElement classElement, String fieldName) {
        for (Element enclosed : classElement.getEnclosedElements()) {
            if (enclosed.getKind() == ElementKind.FIELD) {
                VariableElement field = (VariableElement) enclosed;
                if (field.getSimpleName().toString().equals(fieldName)) {
                    return field;
                }
            }
        }
        return null;
    }

    private String capitalize(String str) {
        return str.substring(0, 1).toUpperCase() + str.substring(1);
    }

    private String extractFieldName(String getterName) {
        if (getterName.startsWith("get") && getterName.length() > 3) {
            String field = getterName.substring(3);
            return field.substring(0, 1).toLowerCase() + field.substring(1);
        }
        return null;
    }
}
