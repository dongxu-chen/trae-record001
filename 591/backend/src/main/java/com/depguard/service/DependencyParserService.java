package com.depguard.service;

import com.depguard.engine.MavenDependencyTreeResolver;
import com.depguard.entity.DependencyRecord;
import com.depguard.entity.Repository;
import com.depguard.enums.BuildTool;
import com.depguard.repository.DependencyRecordRepository;
import com.depguard.repository.RepositoryRepository;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.maven.model.Dependency;
import org.apache.maven.model.Model;
import org.apache.maven.model.io.xpp3.MavenXpp3Reader;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.io.StringReader;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class DependencyParserService {

    private final DependencyRecordRepository dependencyRecordRepository;
    private final RepositoryRepository repositoryRepository;
    private final GitHubIntegrationService gitHubIntegrationService;
    private final MavenDependencyTreeResolver dependencyTreeResolver;

    private static final Pattern GRADLE_DEPENDENCY_PATTERN =
            Pattern.compile("(?:implementation|api|compileOnly|runtimeOnly|testImplementation|testCompileOnly|testRuntimeOnly|annotationProcessor)\\s+['\"]([^:'\"]+):([^:'\"]+):([^:'\"]+)['\"]");

    private static final String MAVEN_CENTRAL_SEARCH_URL =
            "https://search.maven.org/solrsearch/select?q=g:%s+AND+a:%s&rows=1&wt=json";

    private final RestTemplate restTemplate = new RestTemplate();

    @Data
    @AllArgsConstructor
    public static class ParsedDependency {
        private String groupId;
        private String artifactId;
        private String version;
        private String scope;
        private boolean isDirect;
        private Boolean isOutdated;
        private String latestVersion;
    }

    public List<ParsedDependency> parseDependencies(Repository repo) {
        String[] parts = repo.getFullName().split("/");
        String owner = parts[0];
        String name = parts[1];

        if (repo.getBuildTool() == BuildTool.MAVEN) {
            return parseMavenDependencies(owner, name, repo.getDefaultBranch());
        } else {
            return parseGradleDependencies(owner, name, repo.getDefaultBranch());
        }
    }

    public List<ParsedDependency> parseMavenDependencies(String owner, String repoName, String branch) {
        try {
            String pomContent = gitHubIntegrationService.getFileContent(owner, repoName, "pom.xml");
            if (pomContent == null) {
                return Collections.emptyList();
            }

            MavenXpp3Reader reader = new MavenXpp3Reader();
            Model model = reader.read(new StringReader(pomContent));

            List<ParsedDependency> dependencies = new ArrayList<>();
            if (model.getDependencies() != null) {
                for (Dependency dep : model.getDependencies()) {
                    String latestVersion = fetchLatestVersion(dep.getGroupId(), dep.getArtifactId());
                    boolean outdated = latestVersion != null && !latestVersion.equals(dep.getVersion())
                            && compareVersions(dep.getVersion(), latestVersion) < 0;

                    dependencies.add(new ParsedDependency(
                            dep.getGroupId(), dep.getArtifactId(), dep.getVersion(),
                            dep.getScope() != null ? dep.getScope() : "compile",
                            true, outdated, latestVersion
                    ));
                }
            }

            if (model.getDependencyManagement() != null && model.getDependencyManagement().getDependencies() != null) {
                for (Dependency dep : model.getDependencyManagement().getDependencies()) {
                    String latestVersion = fetchLatestVersion(dep.getGroupId(), dep.getArtifactId());
                    boolean outdated = latestVersion != null && !latestVersion.equals(dep.getVersion())
                            && compareVersions(dep.getVersion(), latestVersion) < 0;

                    dependencies.add(new ParsedDependency(
                            dep.getGroupId(), dep.getArtifactId(), dep.getVersion(),
                            dep.getScope() != null ? dep.getScope() : "compile",
                            false, outdated, latestVersion
                    ));
                }
            }

            return dependencies;
        } catch (Exception e) {
            log.error("Failed to parse Maven pom.xml for {}/{}: {}", owner, repoName, e.getMessage());
            return Collections.emptyList();
        }
    }

    public List<ParsedDependency> parseGradleDependencies(String owner, String repoName, String branch) {
        try {
            String gradleContent = gitHubIntegrationService.getFileContent(owner, repoName, "build.gradle");
            if (gradleContent == null) {
                gradleContent = gitHubIntegrationService.getFileContent(owner, repoName, "build.gradle.kts");
            }
            if (gradleContent == null) {
                return Collections.emptyList();
            }

            List<ParsedDependency> dependencies = new ArrayList<>();
            Matcher matcher = GRADLE_DEPENDENCY_PATTERN.matcher(gradleContent);

            while (matcher.find()) {
                String groupId = matcher.group(1);
                String artifactId = matcher.group(2);
                String version = matcher.group(3);

                String latestVersion = fetchLatestVersion(groupId, artifactId);
                boolean outdated = latestVersion != null && !latestVersion.equals(version)
                        && compareVersions(version, latestVersion) < 0;

                dependencies.add(new ParsedDependency(
                        groupId, artifactId, version, "implementation", true, outdated, latestVersion
                ));
            }

            return dependencies;
        } catch (Exception e) {
            log.error("Failed to parse Gradle build file for {}/{}: {}", owner, repoName, e.getMessage());
            return Collections.emptyList();
        }
    }

    public List<DependencyRecord> saveDependencies(Long scanId, List<ParsedDependency> dependencies) {
        List<DependencyRecord> records = new ArrayList<>();
        for (ParsedDependency dep : dependencies) {
            DependencyRecord record = new DependencyRecord();
            record.setScanId(scanId);
            record.setGroupId(dep.getGroupId());
            record.setArtifactId(dep.getArtifactId());
            record.setVersion(dep.getVersion());
            record.setLatestVersion(dep.getLatestVersion());
            record.setScope(dep.getScope());
            record.setIsDirect(dep.isDirect());
            record.setIsOutdated(dep.getIsOutdated());
            records.add(dependencyRecordRepository.save(record));
        }
        return records;
    }

    @Cacheable(value = "dependencyConflicts")
    public List<Map<String, Object>> detectConflicts(Long repoId) {
        List<DependencyRecord> allDeps = dependencyRecordRepository.findAll();

        Map<String, List<DependencyRecord>> grouped = allDeps.stream()
                .collect(Collectors.groupingBy(d -> d.getGroupId() + ":" + d.getArtifactId()));

        List<Map<String, Object>> conflicts = new ArrayList<>();
        for (Map.Entry<String, List<DependencyRecord>> entry : grouped.entrySet()) {
            Set<String> versions = entry.getValue().stream()
                    .map(DependencyRecord::getVersion)
                    .collect(Collectors.toSet());

            if (versions.size() > 1) {
                String[] ga = entry.getKey().split(":");
                Map<String, Object> conflict = new HashMap<>();
                conflict.put("groupId", ga[0]);
                conflict.put("artifactId", ga[1]);
                conflict.put("versions", new ArrayList<>(versions));
                conflict.put("conflictCount", versions.size());
                conflicts.add(conflict);
            }
        }

        return conflicts;
    }

    @Cacheable(value = "latestVersions")
    public String fetchLatestVersion(String groupId, String artifactId) {
        try {
            String url = String.format(MAVEN_CENTRAL_SEARCH_URL, groupId, artifactId);
            @SuppressWarnings("unchecked")
            Map<String, Object> response = restTemplate.getForObject(url, Map.class);

            if (response != null && response.containsKey("response")) {
                @SuppressWarnings("unchecked")
                Map<String, Object> responseBody = (Map<String, Object>) response.get("response");
                @SuppressWarnings("unchecked")
                List<Map<String, Object>> docs = (List<Map<String, Object>>) responseBody.get("docs");
                if (docs != null && !docs.isEmpty()) {
                    return (String) docs.get(0).get("latestVersion");
                }
            }
        } catch (Exception e) {
            log.warn("Failed to fetch latest version for {}:{}: {}", groupId, artifactId, e.getMessage());
        }
        return null;
    }

    public int compareVersions(String v1, String v2) {
        if (v1 == null || v2 == null) return 0;

        String[] parts1 = v1.replace("-SNAPSHOT", "").split("\\.");
        String[] parts2 = v2.replace("-SNAPSHOT", "").split("\\.");

        int maxLength = Math.max(parts1.length, parts2.length);
        for (int i = 0; i < maxLength; i++) {
            int num1 = i < parts1.length ? parseVersionPart(parts1[i]) : 0;
            int num2 = i < parts2.length ? parseVersionPart(parts2[i]) : 0;

            if (num1 != num2) {
                return Integer.compare(num1, num2);
            }
        }
        return 0;
    }

    private int parseVersionPart(String part) {
        try {
            return Integer.parseInt(part.replaceAll("[^0-9].*", ""));
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    public List<DependencyRecord> getDependenciesByScan(Long scanId) {
        return dependencyRecordRepository.findByScanId(scanId);
    }

    public List<DependencyRecord> getDependenciesByGA(String groupId, String artifactId) {
        return dependencyRecordRepository.findByGroupIdAndArtifactId(groupId, artifactId);
    }

    public List<Map<String, Object>> detectFullTreeConflicts() {
        List<Repository> allRepos = repositoryRepository.findAll();
        Map<Long, List<MavenDependencyTreeResolver.TreeDependency>> serviceDependencies = new HashMap<>();

        for (Repository repo : allRepos) {
            List<ParsedDependency> parsedDeps = parseDependencies(repo);
            List<MavenDependencyTreeResolver.TreeDependency> treeDeps = new ArrayList<>();
            for (ParsedDependency dep : parsedDeps) {
                if (dep.isDirect()) {
                    treeDeps.addAll(dependencyTreeResolver.resolveFullDependencyTree(
                            dep.getGroupId(), dep.getArtifactId(), dep.getVersion()));
                }
            }
            serviceDependencies.put((long) repo.getId(), treeDeps);
        }

        List<MavenDependencyTreeResolver.ConflictDetectionResult> conflicts =
                dependencyTreeResolver.detectTransitiveConflicts(serviceDependencies);

        return conflicts.stream().map(conflict -> {
            Map<String, Object> map = new HashMap<>();
            map.put("groupId", conflict.getGroupId());
            map.put("artifactId", conflict.getArtifactId());
            map.put("recommendedVersion", conflict.getRecommendedVersion());
            map.put("severity", conflict.getSeverity());
            map.put("conflictType", "TRANSITIVE");

            List<Map<String, Object>> versions = conflict.getServiceVersions().stream()
                    .map(sv -> {
                        Map<String, Object> v = new HashMap<>();
                        v.put("serviceId", sv.getRepoId());
                        v.put("service", sv.getServiceName());
                        v.put("version", sv.getVersion());
                        return v;
                    })
                    .collect(Collectors.toList());
            map.put("versions", versions);

            return map;
        }).collect(Collectors.toList());
    }

    public List<MavenDependencyTreeResolver.TreeDependency> resolveFullDependencyTreeForRepo(Repository repo) {
        List<ParsedDependency> parsedDeps = parseDependencies(repo);
        List<MavenDependencyTreeResolver.TreeDependency> result = new ArrayList<>();

        for (ParsedDependency dep : parsedDeps) {
            if (dep.isDirect()) {
                result.addAll(dependencyTreeResolver.resolveFullDependencyTree(
                        dep.getGroupId(), dep.getArtifactId(), dep.getVersion()));
            }
        }

        return result;
    }
}
