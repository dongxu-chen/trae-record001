package com.depguard.engine;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import org.springframework.stereotype.Component;

import java.io.*;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.*;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;
import java.util.stream.Collectors;
import java.util.zip.ZipEntry;

@Slf4j
@Component
@RequiredArgsConstructor
public class DependencyUsageAnalyzer {

    public UsageAnalysisResult analyzeUsage(String projectRootPath, List<DependencyInfo> dependencies) {
        Set<String> importedPackages = new HashSet<>();
        Set<String> usedClasses = new HashSet<>();
        Set<String> usedMethods = new HashSet<>();

        try {
            Files.walkFileTree(Paths.get(projectRootPath), new SimpleFileVisitor<Path>() {
                @Override
                public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                    String fileName = file.getFileName().toString();
                    try {
                        if (fileName.endsWith(".java")) {
                            analyzeJavaSource(file, importedPackages, usedClasses);
                        } else if (fileName.endsWith(".class")) {
                            analyzeClassFile(file, importedPackages, usedClasses, usedMethods);
                        } else if (fileName.endsWith(".jar")) {
                            analyzeJarClasses(file, usedClasses, usedMethods);
                        }
                    } catch (Exception e) {
                        log.warn("Error analyzing file: {}", file, e);
                    }
                    return FileVisitResult.CONTINUE;
                }
            });
        } catch (IOException e) {
            log.error("Error walking project directory", e);
        }

        List<DependencyUsageResult> results = new ArrayList<>();
        for (DependencyInfo dep : dependencies) {
            DependencyUsageResult result = analyzeDependencyUsage(dep, importedPackages, usedClasses, usedMethods);
            results.add(result);
        }

        long usedCount = results.stream().filter(r -> r.isUsed()).count();
        long unusedCount = results.stream().filter(r -> !r.isUsed() && "compile".equalsIgnoreCase(r.getScope())).count();
        long unclearCount = results.size() - usedCount - unusedCount;

        return new UsageAnalysisResult(
                results,
                usedCount,
                unusedCount,
                unclearCount,
                importedPackages,
                usedClasses
        );
    }

    private void analyzeJavaSource(Path file, Set<String> importedPackages, Set<String> usedClasses) throws IOException {
        List<String> lines = Files.readAllLines(file);
        for (String line : lines) {
            line = line.trim();
            if (line.startsWith("import ")) {
                String imp = line.substring(7, line.length() - 1).trim();
                if (imp.endsWith(".*")) {
                    importedPackages.add(imp.substring(0, imp.length() - 2));
                } else {
                    usedClasses.add(imp);
                    int lastDot = imp.lastIndexOf('.');
                    if (lastDot > 0) {
                        importedPackages.add(imp.substring(0, lastDot));
                    }
                }
            }
        }
    }

    private void analyzeClassFile(Path file, Set<String> importedPackages, Set<String> usedClasses, Set<String> usedMethods) throws IOException {
        try (InputStream is = Files.newInputStream(file)) {
            analyzeClassBytes(is, usedClasses, usedMethods);
        }
    }

    private void analyzeJarClasses(Path jarFile, Set<String> usedClasses, Set<String> usedMethods) throws IOException {
        try (JarFile jar = new JarFile(jarFile.toFile())) {
            Enumeration<JarEntry> entries = jar.entries();
            while (entries.hasMoreElements()) {
                JarEntry entry = entries.nextElement();
                if (entry.getName().endsWith(".class") && !entry.getName().startsWith("META-INF")) {
                    try (InputStream is = jar.getInputStream(entry)) {
                        analyzeClassBytes(is, usedClasses, usedMethods);
                    } catch (Exception e) {
                        log.trace("Error analyzing class in JAR: {}", entry.getName(), e);
                    }
                }
            }
        }
    }

    private void analyzeClassBytes(InputStream is, Set<String> usedClasses, Set<String> usedMethods) throws IOException {
        ClassReader reader = new ClassReader(is);
        reader.accept(new ClassVisitor(Opcodes.ASM9) {
            @Override
            public void visit(int version, int access, String name, String signature, String superName, String[] interfaces) {
                if (superName != null) {
                    usedClasses.add(superName.replace('/', '.'));
                }
                if (interfaces != null) {
                    for (String iface : interfaces) {
                        usedClasses.add(iface.replace('/', '.'));
                    }
                }
                super.visit(version, access, name, signature, superName, interfaces);
            }

            @Override
            public MethodVisitor visitMethod(int access, String name, String descriptor, String signature, String[] exceptions) {
                return new MethodVisitor(Opcodes.ASM9) {
                    @Override
                    public void visitTypeInsn(int opcode, String type) {
                        if (type != null) {
                            usedClasses.add(type.replace('/', '.'));
                        }
                        super.visitTypeInsn(opcode, type);
                    }

                    @Override
                    public void visitMethodInsn(int opcode, String owner, String name, String descriptor, boolean isInterface) {
                        if (owner != null) {
                            usedClasses.add(owner.replace('/', '.'));
                            usedMethods.add(owner.replace('/', '.') + "." + name + descriptor);
                        }
                        super.visitMethodInsn(opcode, owner, name, descriptor, isInterface);
                    }

                    @Override
                    public void visitFieldInsn(int opcode, String owner, String name, String descriptor) {
                        if (owner != null) {
                            usedClasses.add(owner.replace('/', '.'));
                        }
                        if (descriptor != null && descriptor.startsWith("L")) {
                            String type = descriptor.substring(1, descriptor.length() - 1).replace('/', '.');
                            usedClasses.add(type);
                        }
                        super.visitFieldInsn(opcode, owner, name, descriptor);
                    }

                    @Override
                    public void visitLocalVariable(String name, String descriptor, String signature, org.objectweb.asm.Label start, org.objectweb.asm.Label end, int index) {
                        if (descriptor != null && descriptor.startsWith("L")) {
                            String type = descriptor.substring(1, descriptor.length() - 1).replace('/', '.');
                            usedClasses.add(type);
                        }
                        super.visitLocalVariable(name, descriptor, signature, start, end, index);
                    }
                };
            }
        }, ClassReader.SKIP_DEBUG | ClassReader.SKIP_FRAMES);
    }

    private DependencyUsageResult analyzeDependencyUsage(DependencyInfo dep,
                                                         Set<String> importedPackages,
                                                         Set<String> usedClasses,
                                                         Set<String> usedMethods) {
        String groupId = dep.getGroupId();
        String artifactId = dep.getArtifactId();

        Set<String> candidatePackages = generateCandidatePackages(groupId, artifactId);

        boolean isDirectlyUsed = false;
        Set<String> usedPackageMatches = new HashSet<>();
        Set<String> usedClassMatches = new HashSet<>();

        for (String pkg : candidatePackages) {
            for (String imported : importedPackages) {
                if (imported.startsWith(pkg) || pkg.startsWith(imported)) {
                    isDirectlyUsed = true;
                    usedPackageMatches.add(imported);
                }
            }

            for (String usedClass : usedClasses) {
                if (usedClass.startsWith(pkg)) {
                    isDirectlyUsed = true;
                    usedClassMatches.add(usedClass);
                }
            }
        }

        boolean isTestScope = "test".equalsIgnoreCase(dep.getScope());
        boolean isProvidedScope = "provided".equalsIgnoreCase(dep.getScope());
        boolean isRuntimeScope = "runtime".equalsIgnoreCase(dep.getScope());

        boolean probablyUsed = isDirectlyUsed || isProvidedScope || isRuntimeScope ||
                isCommonlyUsed(groupId, artifactId);

        double usageConfidence = isDirectlyUsed ? 95.0 :
                probablyUsed ? 50.0 : 10.0;

        List<String> usageEvidence = new ArrayList<>();
        if (!usedPackageMatches.isEmpty()) {
            usageEvidence.add("使用的包: " + String.join(", ", usedPackageMatches));
        }
        if (!usedClassMatches.isEmpty()) {
            List<String> classList = usedClassMatches.stream().limit(5).collect(Collectors.toList());
            usageEvidence.add("使用的类: " + String.join(", ", classList));
            if (usedClassMatches.size() > 5) {
                usageEvidence.add("... 另有 " + (usedClassMatches.size() - 5) + " 个类被使用");
            }
        }

        if (!isDirectlyUsed && isTestScope) {
            usageEvidence.add("测试范围依赖，可能通过测试框架间接使用");
        }
        if (!isDirectlyUsed && isProvidedScope) {
            usageEvidence.add("Provided范围依赖，由运行环境提供");
        }
        if (!isDirectlyUsed && isRuntimeScope) {
            usageEvidence.add("Runtime范围依赖，通过反射或SPI动态加载");
        }

        return new DependencyUsageResult(
                dep,
                probablyUsed,
                isDirectlyUsed,
                usageConfidence,
                usageEvidence,
                isTestScope || isProvidedScope || isRuntimeScope
        );
    }

    private Set<String> generateCandidatePackages(String groupId, String artifactId) {
        Set<String> packages = new HashSet<>();

        packages.add(groupId);
        packages.add(groupId + "." + artifactId);

        if (artifactId.startsWith("spring-boot-starter-")) {
            String module = artifactId.substring("spring-boot-starter-".length());
            packages.add("org.springframework.boot." + module);
            packages.add("org.springframework." + module);
        }

        if (artifactId.startsWith("spring-boot-starter")) {
            packages.add("org.springframework.boot.autoconfigure");
            packages.add("org.springframework.context.annotation");
        }

        if (groupId.equals("org.projectlombok") && artifactId.equals("lombok")) {
            packages.add("lombok");
        }

        if (groupId.startsWith("org.junit")) {
            packages.add("org.junit.jupiter.api");
            packages.add("org.junit.Test");
        }

        return packages;
    }

    private boolean isCommonlyUsed(String groupId, String artifactId) {
        Set<String> commonlyUsed = new HashSet<>();
        commonlyUsed.add("org.springframework.boot:spring-boot-starter-web");
        commonlyUsed.add("org.springframework.boot:spring-boot-starter-data-jpa");
        commonlyUsed.add("org.springframework.boot:spring-boot-starter-security");
        commonlyUsed.add("org.springframework.boot:spring-boot-starter-validation");
        commonlyUsed.add("org.springframework.boot:spring-boot-starter-actuator");
        commonlyUsed.add("org.projectlombok:lombok");
        commonlyUsed.add("com.fasterxml.jackson.core:jackson-databind");
        commonlyUsed.add("org.slf4j:slf4j-api");
        commonlyUsed.add("ch.qos.logback:logback-classic");
        commonlyUsed.add("mysql:mysql-connector-java");
        commonlyUsed.add("org.postgresql:postgresql");
        commonlyUsed.add("com.h2database:h2");
        commonlyUsed.add("org.apache.commons:commons-lang3");
        commonlyUsed.add("com.google.guava:guava");

        return commonlyUsed.contains(groupId + ":" + artifactId);
    }

    @lombok.Data
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class DependencyInfo {
        private String groupId;
        private String artifactId;
        private String version;
        private String scope;
        private Boolean isDirect;
    }

    @lombok.Data
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class DependencyUsageResult {
        private DependencyInfo dependency;
        private boolean isUsed;
        private boolean isDirectlyUsed;
        private double usageConfidence;
        private List<String> usageEvidence;
        private boolean isSpecialScope;
    }

    @lombok.Data
    @lombok.NoArgsConstructor
    @lombok.AllArgsConstructor
    public static class UsageAnalysisResult {
        private List<DependencyUsageResult> dependencyResults;
        private long usedCount;
        private long unusedCount;
        private long unclearCount;
        private Set<String> allImportedPackages;
        private Set<String> allUsedClasses;

        public List<DependencyUsageResult> getUnusedDependencies() {
            return dependencyResults.stream()
                    .filter(r -> !r.isUsed() && !r.isSpecialScope())
                    .collect(Collectors.toList());
        }
    }
}
