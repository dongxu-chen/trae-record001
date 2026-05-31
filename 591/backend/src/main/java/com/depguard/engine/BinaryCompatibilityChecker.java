package com.depguard.engine;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.*;
import java.net.URL;
import java.util.*;
import java.util.jar.JarEntry;
import java.util.jar.JarInputStream;

@Slf4j
@Component
public class BinaryCompatibilityChecker {

    private static final String MAVEN_CENTRAL_JAR_URL = "https://repo1.maven.org/maven2/%s/%s/%s/%s-%s.jar";

    public CompatibilityCheckResult checkBinaryCompatibility(String groupId, String artifactId,
                                                              String currentVersion, String targetVersion) {

        CompatibilityCheckResult result = new CompatibilityCheckResult();
        result.setGroupId(groupId);
        result.setArtifactId(artifactId);
        result.setCurrentVersion(currentVersion);
        result.setTargetVersion(targetVersion);

        try {
            Set<ClassInfo> currentClasses = extractClassInfo(groupId, artifactId, currentVersion);
            Set<ClassInfo> targetClasses = extractClassInfo(groupId, artifactId, targetVersion);

            Map<String, ClassInfo> currentClassMap = new HashMap<>();
            for (ClassInfo ci : currentClasses) {
                currentClassMap.put(ci.getClassName(), ci);
            }

            Map<String, ClassInfo> targetClassMap = new HashMap<>();
            for (ClassInfo ci : targetClasses) {
                targetClassMap.put(ci.getClassName(), ci);
            }

            List<String> removedClasses = new ArrayList<>();
            List<String> removedMethods = new ArrayList<>();
            List<String> removedFields = new ArrayList<>();
            List<String> methodSignatureChanges = new ArrayList<>();
            List<String> breakingChanges = new ArrayList<>();

            for (String className : currentClassMap.keySet()) {
                if (!targetClassMap.containsKey(className)) {
                    removedClasses.add(className);
                } else {
                    ClassInfo current = currentClassMap.get(className);
                    ClassInfo target = targetClassMap.get(className);

                    Map<String, MethodInfo> currentMethodMap = new HashMap<>();
                    for (MethodInfo mi : current.getMethods()) {
                        currentMethodMap.put(mi.getSignature(), mi);
                    }

                    Map<String, MethodInfo> targetMethodMap = new HashMap<>();
                    for (MethodInfo mi : target.getMethods()) {
                        targetMethodMap.put(mi.getSignature(), mi);
                    }

                    for (String sig : currentMethodMap.keySet()) {
                        if (!targetMethodMap.containsKey(sig)) {
                            MethodInfo cm = currentMethodMap.get(sig);
                            if (cm.isPublic() || cm.isProtected()) {
                                removedMethods.add(className + "." + sig);
                            }
                        } else {
                            MethodInfo currentMethod = currentMethodMap.get(sig);
                            MethodInfo targetMethod = targetMethodMap.get(sig);

                            if ((currentMethod.isPublic() != targetMethod.isPublic()) ||
                                (currentMethod.isProtected() != targetMethod.isProtected())) {
                                methodSignatureChanges.add(className + "." + sig +
                                        " (access changed from " +
                                        getAccess(currentMethod) + " to " + getAccess(targetMethod) + ")");
                            }
                        }
                    }

                    Map<String, FieldInfo> currentFieldMap = new HashMap<>();
                    for (FieldInfo fi : current.getFields()) {
                        currentFieldMap.put(fi.getName(), fi);
                    }

                    Map<String, FieldInfo> targetFieldMap = new HashMap<>();
                    for (FieldInfo fi : target.getFields()) {
                        targetFieldMap.put(fi.getName(), fi);
                    }

                    for (String fieldName : currentFieldMap.keySet()) {
                        if (!targetFieldMap.containsKey(fieldName)) {
                            FieldInfo cf = currentFieldMap.get(fieldName);
                            if (cf.isPublic() || cf.isProtected()) {
                                removedFields.add(className + "." + fieldName);
                            }
                        } else {
                            FieldInfo cf = currentFieldMap.get(fieldName);
                            FieldInfo tf = targetFieldMap.get(fieldName);
                            if (!cf.getType().equals(tf.getType())) {
                                removedFields.add(className + "." + fieldName +
                                        " (type changed from " + cf.getType() + " to " + tf.getType() + ")");
                            }
                            if ((cf.isPublic() != tf.isPublic()) || (cf.isProtected() != tf.isProtected())) {
                                methodSignatureChanges.add(className + "." + fieldName +
                                        " (access changed)");
                            }
                        }
                    }
                }
            }

            result.setRemovedClasses(removedClasses);
            result.setRemovedMethods(removedMethods);
            result.setRemovedFields(removedFields);
            result.setMethodSignatureChanges(methodSignatureChanges);

            int totalIssues = removedClasses.size() + removedMethods.size() +
                    removedFields.size() + methodSignatureChanges.size();

            double compatibilityScore = calculateCompatibilityScore(totalIssues, currentClasses.size());

            result.setBinaryCompatible(totalIssues == 0);
            result.setCompatibilityScore(compatibilityScore);

            if (totalIssues > 0) {
                breakingChanges.addAll(removedClasses);
                breakingChanges.addAll(removedMethods);
                breakingChanges.addAll(removedFields);
                breakingChanges.addAll(methodSignatureChanges);
            }

            result.setBreakingChanges(breakingChanges);

        } catch (Exception e) {
            log.warn("Binary compatibility check failed for {}:{}: {} -> {}: {}",
                    groupId, artifactId, currentVersion, targetVersion, e.getMessage());
            result.setCompatibilityScore(70.0);
            result.setBinaryCompatible(false);
            result.setBreakingChanges(Collections.singletonList("Binary compatibility check failed, falling back to version-based analysis"));
        }

        return result;
    }

    private double calculateCompatibilityScore(int issues, int totalClasses) {
        if (totalClasses == 0) return 80.0;

        double issueRatio = (double) issues / totalClasses;

        if (issueRatio == 0) return 95.0;
        if (issueRatio < 0.01) return 90.0;
        if (issueRatio < 0.05) return 80.0;
        if (issueRatio < 0.1) return 70.0;
        if (issueRatio < 0.2) return 60.0;
        if (issueRatio < 0.3) return 50.0;
        if (issueRatio < 0.5) return 40.0;
        return 30.0;
    }

    private String getAccess(MethodInfo mi) {
        if (mi.isPublic()) return "public";
        if (mi.isProtected()) return "protected";
        if (mi.isPrivate()) return "private";
        return "package-private";
    }

    private Set<ClassInfo> extractClassInfo(String groupId, String artifactId, String version) throws IOException {
        Set<ClassInfo> classes = new HashSet<>();

        String jarUrl = buildJarUrl(groupId, artifactId, artifactId, version);
        log.debug("Downloading JAR: {}", jarUrl);

        try (InputStream is = new URL(jarUrl).openStream();
             JarInputStream jis = new JarInputStream(is)) {

            JarEntry entry;
            while ((entry = jis.getNextJarEntry()) != null) {
                if (entry.getName().endsWith(".class") && !entry.getName().contains("META-INF")) {
                    String className = entry.getName().replace("/", ".").replace(".class", "");

                    try {
                        org.objectweb.asm.ClassReader cr = new org.objectweb.asm.ClassReader(jis);
                        ClassInfo ci = new ClassInfo(className);
                        ci.setAccess(cr.getAccess());

                        org.objectweb.asm.ClassVisitor cv = new org.objectweb.asm.ClassVisitor(org.objectweb.asm.Opcodes.ASM9) {
                            @Override
                            public org.objectweb.asm.MethodVisitor visitMethod(int access, String name, String descriptor,
                                                                               String signature, String[] exceptions) {
                                ci.addMethod(new MethodInfo(name, descriptor, access));
                                return super.visitMethod(access, name, descriptor, signature, exceptions);
                            }

                            @Override
                            public org.objectweb.asm.FieldVisitor visitField(int access, String name, String descriptor,
                                                                             String signature, Object value) {
                                ci.addField(new FieldInfo(name, descriptor, access));
                                return super.visitField(access, name, descriptor, signature, value);
                            }
                        };

                        cr.accept(cv, org.objectweb.asm.ClassReader.SKIP_CODE | org.objectweb.asm.ClassReader.SKIP_FRAMES);
                        classes.add(ci);
                    } catch (Exception e) {
                        log.debug("Failed to parse class {}: {}", className, e.getMessage());
                    }
                }
            }
        } catch (FileNotFoundException e) {
            log.warn("JAR not found: {}", jarUrl);
        }

        return classes;
    }

    private String buildJarUrl(String groupId, String artifactId, String jarName, String version) {
        return String.format(MAVEN_CENTRAL_JAR_URL,
                groupId.replace(".", "/"),
                artifactId,
                version,
                jarName,
                version);
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ClassInfo {
        private String className;
        private int access;
        private Set<MethodInfo> methods = new HashSet<>();
        private Set<FieldInfo> fields = new HashSet<>();

        public ClassInfo(String className) {
            this.className = className;
        }

        public void addMethod(MethodInfo mi) {
            this.methods.add(mi);
        }

        public void addField(FieldInfo fi) {
            this.fields.add(fi);
        }

        public boolean isPublic() {
            return (access & org.objectweb.asm.Opcodes.ACC_PUBLIC) != 0;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            ClassInfo classInfo = (ClassInfo) o;
            return Objects.equals(className, classInfo.className);
        }

        @Override
        public int hashCode() {
            return Objects.hash(className);
        }
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MethodInfo {
        private String name;
        private String descriptor;
        private int access;

        public MethodInfo(String name, String descriptor, int access) {
            this.name = name;
            this.descriptor = descriptor;
            this.access = access;
        }

        public String getSignature() {
            return name + descriptor;
        }

        public boolean isPublic() {
            return (access & org.objectweb.asm.Opcodes.ACC_PUBLIC) != 0;
        }

        public boolean isProtected() {
            return (access & org.objectweb.asm.Opcodes.ACC_PROTECTED) != 0;
        }

        public boolean isPrivate() {
            return (access & org.objectweb.asm.Opcodes.ACC_PRIVATE) != 0;
        }

        public boolean isStatic() {
            return (access & org.objectweb.asm.Opcodes.ACC_STATIC) != 0;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            MethodInfo that = (MethodInfo) o;
            return Objects.equals(getSignature(), that.getSignature());
        }

        @Override
        public int hashCode() {
            return Objects.hash(getSignature());
        }
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class FieldInfo {
        private String name;
        private String type;
        private int access;

        public FieldInfo(String name, String type, int access) {
            this.name = name;
            this.type = type;
            this.access = access;
        }

        public boolean isPublic() {
            return (access & org.objectweb.asm.Opcodes.ACC_PUBLIC) != 0;
        }

        public boolean isProtected() {
            return (access & org.objectweb.asm.Opcodes.ACC_PROTECTED) != 0;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            FieldInfo fieldInfo = (FieldInfo) o;
            return Objects.equals(name, fieldInfo.name);
        }

        @Override
        public int hashCode() {
            return Objects.hash(name);
        }
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CompatibilityCheckResult {
        private String groupId;
        private String artifactId;
        private String currentVersion;
        private String targetVersion;
        private boolean binaryCompatible;
        private double compatibilityScore;
        private List<String> removedClasses = new ArrayList<>();
        private List<String> removedMethods = new ArrayList<>();
        private List<String> removedFields = new ArrayList<>();
        private List<String> methodSignatureChanges = new ArrayList<>();
        private List<String> breakingChanges = new ArrayList<>();

        public int getTotalIssues() {
            return removedClasses.size() + removedMethods.size() +
                    removedFields.size() + methodSignatureChanges.size();
        }
    }
}
