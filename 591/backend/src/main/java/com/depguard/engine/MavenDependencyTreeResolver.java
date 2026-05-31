package com.depguard.engine;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.maven.repository.internal.MavenRepositorySystemUtils;
import org.eclipse.aether.DefaultRepositorySystemSession;
import org.eclipse.aether.RepositorySystem;
import org.eclipse.aether.artifact.Artifact;
import org.eclipse.aether.artifact.DefaultArtifact;
import org.eclipse.aether.collection.CollectRequest;
import org.eclipse.aether.collection.DependencyCollectionException;
import org.eclipse.aether.connector.basic.BasicRepositoryConnectorFactory;
import org.eclipse.aether.graph.Dependency;
import org.eclipse.aether.graph.DependencyNode;
import org.eclipse.aether.impl.DefaultServiceLocator;
import org.eclipse.aether.repository.RemoteRepository;
import org.eclipse.aether.resolution.DependencyRequest;
import org.eclipse.aether.resolution.DependencyResolutionException;
import org.eclipse.aether.spi.connector.RepositoryConnectorFactory;
import org.eclipse.aether.spi.connector.transport.TransporterFactory;
import org.eclipse.aether.transport.http.HttpTransporterFactory;
import org.eclipse.aether.util.graph.visitor.PreorderNodeListGenerator;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Slf4j
@Component
public class MavenDependencyTreeResolver {

    private final RepositorySystem repositorySystem;
    private final DefaultRepositorySystemSession session;
    private final List<RemoteRepository> repositories;

    public MavenDependencyTreeResolver() {
        this.repositorySystem = createRepositorySystem();
        this.session = createSession(repositorySystem);
        this.repositories = createRepositories();
    }

    private RepositorySystem createRepositorySystem() {
        DefaultServiceLocator locator = MavenRepositorySystemUtils.newServiceLocator();
        locator.addService(RepositoryConnectorFactory.class, BasicRepositoryConnectorFactory.class);
        locator.addService(TransporterFactory.class, HttpTransporterFactory.class);
        return locator.getService(RepositorySystem.class);
    }

    private DefaultRepositorySystemSession createSession(RepositorySystem system) {
        DefaultRepositorySystemSession session = MavenRepositorySystemUtils.newSession();
        session.setLocalRepositoryManager(system.newLocalRepositoryManager(session,
                new org.eclipse.aether.repository.LocalRepository(System.getProperty("java.io.tmpdir") + "/depguard-repo")));
        return session;
    }

    private List<RemoteRepository> createRepositories() {
        List<RemoteRepository> repos = new ArrayList<>();
        repos.add(new RemoteRepository.Builder("central", "default",
                "https://repo1.maven.org/maven2/").build());
        return repos;
    }

    public List<TreeDependency> resolveFullDependencyTree(String groupId, String artifactId, String version) {
        String coords = groupId + ":" + artifactId + ":" + version;
        return resolveFullDependencyTree(coords);
    }

    public List<TreeDependency> resolveFullDependencyTree(String artifactCoords) {
        try {
            Artifact artifact = new DefaultArtifact(artifactCoords);

            CollectRequest collectRequest = new CollectRequest();
            collectRequest.setRoot(new Dependency(artifact, "compile"));
            collectRequest.setRepositories(repositories);

            DependencyNode root = repositorySystem.collectDependencies(session, collectRequest).getRoot();

            DependencyRequest dependencyRequest = new DependencyRequest();
            dependencyRequest.setRoot(root);
            repositorySystem.resolveDependencies(session, dependencyRequest);

            PreorderNodeListGenerator generator = new PreorderNodeListGenerator();
            root.accept(generator);

            List<TreeDependency> deps = new ArrayList<>();
            Map<String, TreeDependency> visited = new ConcurrentHashMap<>();

            buildTree(root, deps, 0, visited);

            return deps;

        } catch (DependencyCollectionException | DependencyResolutionException e) {
            log.warn("Failed to resolve dependency tree for {}: {}", artifactCoords, e.getMessage());
            return Collections.emptyList();
        }
    }

    private void buildTree(DependencyNode node, List<TreeDependency> deps, int depth, Map<String, TreeDependency> visited) {
        if (node.getArtifact() == null) return;

        Artifact artifact = node.getArtifact();
        String key = artifact.getGroupId() + ":" + artifact.getArtifactId() + ":" + artifact.getVersion();

        if (visited.containsKey(key)) {
            return;
        }

        TreeDependency dep = new TreeDependency(
                artifact.getGroupId(),
                artifact.getArtifactId(),
                artifact.getVersion(),
                depth == 0,
                depth
        );

        visited.put(key, dep);
        deps.add(dep);

        List<TreeDependency> children = new ArrayList<>();
        for (DependencyNode child : node.getChildren()) {
            if (child.getArtifact() != null) {
                buildTree(child, children, depth + 1, visited);
            }
        }
        dep.setTransitiveDependencies(children);
    }

    public DependencyTreeResult analyzeAllDependencies(List<DependencyParserServiceWrapper.ParsedDependency> directDeps) {
        List<TreeDependency> allDeps = new ArrayList<>();
        Set<String> conflictedArtifacts = new HashSet<>();
        Map<String, Set<String>> artifactVersions = new HashMap<>();

        for (DependencyParserServiceWrapper.ParsedDependency dep : directDeps) {
            if (dep.isDirect()) {
                List<TreeDependency> tree = resolveFullDependencyTree(
                        dep.getGroupId(), dep.getArtifactId(), dep.getVersion());
                collectVersions(tree, artifactVersions);
                allDeps.addAll(tree);
            }
        }

        for (Map.Entry<String, Set<String>> entry : artifactVersions.entrySet()) {
            if (entry.getValue().size() > 1) {
                conflictedArtifacts.add(entry.getKey());
            }
        }

        return new DependencyTreeResult(allDeps, conflictedArtifacts, artifactVersions);
    }

    private void collectVersions(List<TreeDependency> deps, Map<String, Set<String>> artifactVersions) {
        for (TreeDependency dep : deps) {
            String key = dep.getGroupId() + ":" + dep.getArtifactId();
            artifactVersions.computeIfAbsent(key, k -> new HashSet<>()).add(dep.getVersion());
            if (dep.getTransitiveDependencies() != null) {
                collectVersions(dep.getTransitiveDependencies(), artifactVersions);
            }
        }
    }

    public List<ConflictDetectionResult> detectTransitiveConflicts(Map<Long, List<TreeDependency>> serviceDependencies) {
        Map<String, Map<Long, Set<String>>> artifactServiceVersions = new HashMap<>();

        for (Map.Entry<Long, List<TreeDependency>> entry : serviceDependencies.entrySet()) {
            Long repoId = entry.getKey();
            List<TreeDependency> deps = entry.getValue();
            collectServiceVersions(deps, repoId, artifactServiceVersions);
        }

        List<ConflictDetectionResult> conflicts = new ArrayList<>();
        for (Map.Entry<String, Map<Long, Set<String>>> artifactEntry : artifactServiceVersions.entrySet()) {
            String artifact = artifactEntry.getKey();
            Map<Long, Set<String>> serviceVersionMap = artifactEntry.getValue();

            Set<String> allVersions = new HashSet<>();
            for (Set<String> versions : serviceVersionMap.values()) {
                allVersions.addAll(versions);
            }

            if (allVersions.size() > 1) {
                List<ConflictDetectionResult.ServiceVersion> svcVersions = new ArrayList<>();
                String recommended = findLatestVersion(allVersions);

                for (Map.Entry<Long, Set<String>> svcEntry : serviceVersionMap.entrySet()) {
                    for (String ver : svcEntry.getValue()) {
                        svcVersions.add(new ConflictDetectionResult.ServiceVersion(
                                svcEntry.getKey(), findServiceName(svcEntry.getKey()), ver));
                    }
                }

                conflicts.add(new ConflictDetectionResult(
                        artifact.split(":")[0],
                        artifact.split(":")[1],
                        svcVersions,
                        recommended,
                        calculateSeverity(svcVersions)
                ));
            }
        }

        return conflicts;
    }

    private void collectServiceVersions(List<TreeDependency> deps, Long repoId,
                                        Map<String, Map<Long, Set<String>>> artifactServiceVersions) {
        for (TreeDependency dep : deps) {
            String key = dep.getGroupId() + ":" + dep.getArtifactId();
            artifactServiceVersions
                    .computeIfAbsent(key, k -> new HashMap<>())
                    .computeIfAbsent(repoId, k -> new HashSet<>())
                    .add(dep.getVersion());

            if (dep.getTransitiveDependencies() != null) {
                collectServiceVersions(dep.getTransitiveDependencies(), repoId, artifactServiceVersions);
            }
        }
    }

    private String findLatestVersion(Set<String> versions) {
        return versions.stream().max((v1, v2) -> {
            String[] p1 = v1.replace("-SNAPSHOT", "").split("\\.");
            String[] p2 = v2.replace("-SNAPSHOT", "").split("\\.");
            int max = Math.max(p1.length, p2.length);
            for (int i = 0; i < max; i++) {
                int n1 = i < p1.length ? parsePart(p1[i]) : 0;
                int n2 = i < p2.length ? parsePart(p2[i]) : 0;
                if (n1 != n2) return Integer.compare(n1, n2);
            }
            return 0;
        }).orElse(null);
    }

    private int parsePart(String s) {
        try {
            return Integer.parseInt(s.replaceAll("[^0-9].*", ""));
        } catch (Exception e) {
            return 0;
        }
    }

    private String calculateSeverity(List<ConflictDetectionResult.ServiceVersion> versions) {
        Set<String> uniqueVersions = new HashSet<>();
        for (ConflictDetectionResult.ServiceVersion sv : versions) {
            uniqueVersions.add(sv.getVersion());
        }
        int count = uniqueVersions.size();
        if (count >= 3) return "HIGH";
        if (count == 2) return "MEDIUM";
        return "LOW";
    }

    private String findServiceName(Long repoId) {
        return "service-" + repoId;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TreeDependency {
        private String groupId;
        private String artifactId;
        private String version;
        private boolean isDirect;
        private int depth;
        private List<TreeDependency> transitiveDependencies = new ArrayList<>();
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DependencyTreeResult {
        private List<TreeDependency> allDependencies;
        private Set<String> conflictedArtifacts;
        private Map<String, Set<String>> artifactVersions;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ConflictDetectionResult {
        private String groupId;
        private String artifactId;
        private List<ServiceVersion> serviceVersions;
        private String recommendedVersion;
        private String severity;

        @Data
        @NoArgsConstructor
        @AllArgsConstructor
        public static class ServiceVersion {
            private Long repoId;
            private String serviceName;
            private String version;
        }
    }
}
