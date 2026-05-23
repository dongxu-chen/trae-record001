package com.configcenter.service;

import com.configcenter.dto.ConfigDTO;
import com.configcenter.dto.ConfigVersionDTO;
import org.eclipse.jgit.api.*;
import org.eclipse.jgit.api.errors.GitAPIException;
import org.eclipse.jgit.lib.*;
import org.eclipse.jgit.revwalk.RevCommit;
import org.eclipse.jgit.treewalk.TreeWalk;
import org.eclipse.jgit.treewalk.filter.PathFilter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.config.environment.Environment;
import org.springframework.cloud.config.server.environment.JGitEnvironmentRepository;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.ReentrantLock;

@Service
public class GitConfigService {

    @Value("${spring.cloud.config.server.git.uri}")
    private String gitUri;

    @Value("${config.version.max-versions:100}")
    private int maxVersions;

    @Value("${spring.cloud.config.server.git.default-label:master}")
    private String defaultLabel;

    private final JGitEnvironmentRepository environmentRepository;

    private final Map<String, ReentrantLock> appLocks = new ConcurrentHashMap<>();

    public GitConfigService(JGitEnvironmentRepository environmentRepository) {
        this.environmentRepository = environmentRepository;
    }

    @PostConstruct
    public void init() throws Exception {
        File gitDir = new File(gitUri);
        if (!gitDir.exists() || !new File(gitDir, ".git").exists()) {
            initGitRepository(gitDir);
        }
    }

    private void initGitRepository(File gitDir) throws Exception {
        if (!gitDir.exists()) {
            gitDir.mkdirs();
        }
        try (Git git = Git.init().setDirectory(gitDir).call()) {
            File readme = new File(gitDir, "README.md");
            Files.write(readme.toPath(), "# Config Repository\n".getBytes(StandardCharsets.UTF_8));
            git.add().addFilepattern("README.md").call();
            git.commit().setMessage("Initial commit").setAuthor("config-center", "config@center.com").call();
        }
    }

    private ReentrantLock getLock(String application) {
        return appLocks.computeIfAbsent(application, k -> new ReentrantLock());
    }

    public ConfigDTO publishConfig(ConfigDTO configDTO) throws Exception {
        ReentrantLock lock = getLock(configDTO.getApplication());
        lock.lock();
        try {
            File gitDir = new File(gitUri);
            try (Git git = Git.open(gitDir)) {
                git.pull().call();

                String fileName = getFileName(configDTO.getApplication(), configDTO.getProfile(), configDTO.getFormat());
                Path filePath = Paths.get(gitDir.getAbsolutePath(), configDTO.getApplication(), configDTO.getProfile(), fileName);

                Files.createDirectories(filePath.getParent());
                Files.write(filePath, configDTO.getContent().getBytes(StandardCharsets.UTF_8));

                git.add().addFilepattern(configDTO.getApplication() + "/" + configDTO.getProfile() + "/" + fileName).call();

                String message = String.format("Update config: %s/%s - %s",
                        configDTO.getApplication(), configDTO.getProfile(),
                        configDTO.getDescription() != null ? configDTO.getDescription() : "update");

                RevCommit commit = git.commit()
                        .setMessage(message)
                        .setAuthor(configDTO.getCreatedBy() != null ? configDTO.getCreatedBy() : "config-center", "config@center.com")
                        .call();

                configDTO.setVersion(commit.getName());
                configDTO.setCreateTime(LocalDateTime.ofInstant(commit.getAuthorIdent().getWhen().toInstant(), ZoneId.systemDefault()));

                cleanupOldVersions(git, configDTO.getApplication(), configDTO.getProfile());

                return configDTO;
            }
        } finally {
            lock.unlock();
        }
    }

    private String getFileName(String application, String profile, String format) {
        String baseName = application + "-" + profile;
        if ("json".equalsIgnoreCase(format)) {
            return baseName + ".json";
        }
        return baseName + ".yml";
    }

    public ConfigDTO getConfig(String application, String profile, String label) throws Exception {
        Environment environment = environmentRepository.findOne(application, profile, label != null ? label : defaultLabel);

        if (environment == null || environment.getPropertySources().isEmpty()) {
            return null;
        }

        File gitDir = new File(gitUri);
        try (Git git = Git.open(gitDir)) {
            String fileName = getFileName(application, profile, "yml");
            Path filePath = Paths.get(gitDir.getAbsolutePath(), application, profile, fileName);

            String content = "";
            String format = "yml";
            if (Files.exists(filePath)) {
                content = new String(Files.readAllBytes(filePath), StandardCharsets.UTF_8);
            } else {
                fileName = getFileName(application, profile, "json");
                filePath = Paths.get(gitDir.getAbsolutePath(), application, profile, fileName);
                if (Files.exists(filePath)) {
                    content = new String(Files.readAllBytes(filePath), StandardCharsets.UTF_8);
                    format = "json";
                }
            }

            ConfigDTO configDTO = new ConfigDTO();
            configDTO.setApplication(application);
            configDTO.setProfile(profile);
            configDTO.setLabel(label != null ? label : defaultLabel);
            configDTO.setContent(content);
            configDTO.setFormat(format);

            Iterable<RevCommit> commits = git.log().addPath(application + "/" + profile).setMaxCount(1).call();
            for (RevCommit commit : commits) {
                configDTO.setVersion(commit.getName());
                configDTO.setCreateTime(LocalDateTime.ofInstant(commit.getAuthorIdent().getWhen().toInstant(), ZoneId.systemDefault()));
                configDTO.setCreatedBy(commit.getAuthorIdent().getName());
            }

            return configDTO;
        }
    }

    public List<ConfigVersionDTO> getVersionHistory(String application, String profile) throws Exception {
        List<ConfigVersionDTO> versions = new ArrayList<>();
        File gitDir = new File(gitUri);

        try (Git git = Git.open(gitDir)) {
            Repository repository = git.getRepository();
            String pathPrefix = application + "/" + profile + "/";

            Iterable<RevCommit> commits = git.log()
                    .add(repository.resolve(defaultLabel))
                    .setMaxCount(maxVersions)
                    .call();

            String currentVersion = null;
            int count = 0;
            for (RevCommit commit : commits) {
                if (count >= maxVersions) break;

                String changedPath = getChangedPath(commit, pathPrefix);
                if (changedPath != null) {
                    ConfigVersionDTO versionDTO = new ConfigVersionDTO();
                    versionDTO.setVersion(commit.getName());
                    versionDTO.setApplication(application);
                    versionDTO.setProfile(profile);
                    versionDTO.setDescription(commit.getShortMessage());
                    versionDTO.setCreateTime(LocalDateTime.ofInstant(commit.getAuthorIdent().getWhen().toInstant(), ZoneId.systemDefault()));
                    versionDTO.setCreatedBy(commit.getAuthorIdent().getName());
                    versionDTO.setFormat(changedPath.endsWith(".json") ? "json" : "yml");

                    if (currentVersion == null) {
                        currentVersion = commit.getName();
                        versionDTO.setCurrent(true);
                    }

                    versions.add(versionDTO);
                    count++;
                }
            }
        }

        return versions;
    }

    private String getChangedPath(RevCommit commit, String pathPrefix) {
        if (commit.getParentCount() == 0) return null;

        RevCommit parent = commit.getParent(0);
        try (TreeWalk treeWalk = new TreeWalk(commit.getRepository())) {
            treeWalk.addTree(parent.getTree());
            treeWalk.addTree(commit.getTree());
            treeWalk.setRecursive(true);
            treeWalk.setFilter(PathFilter.create(pathPrefix));

            while (treeWalk.next()) {
                String path = treeWalk.getPathString();
                if (path.startsWith(pathPrefix) && (path.endsWith(".yml") || path.endsWith(".yaml") || path.endsWith(".json"))) {
                    return path;
                }
            }
        } catch (Exception e) {
            return null;
        }
        return null;
    }

    public ConfigDTO rollbackToVersion(String application, String profile, String version) throws Exception {
        File gitDir = new File(gitUri);
        try (Git git = Git.open(gitDir)) {
            Repository repository = git.getRepository();
            ObjectId commitId = repository.resolve(version);
            if (commitId == null) {
                throw new IllegalArgumentException("Version not found: " + version);
            }

            String pathPrefix = application + "/" + profile + "/";
            String content = null;
            String format = "yml";

            try (RevCommit commit = repository.parseCommit(commitId)) {
                try (TreeWalk treeWalk = TreeWalk.forPath(repository, pathPrefix.substring(0, pathPrefix.length() - 1), commit.getTree())) {
                    if (treeWalk != null && treeWalk.isSubtree()) {
                        treeWalk.enterSubtree();
                        while (treeWalk.next()) {
                            String path = treeWalk.getPathString();
                            if (path.endsWith(".yml") || path.endsWith(".yaml") || path.endsWith(".json")) {
                                format = path.endsWith(".json") ? "json" : "yml";
                                ObjectLoader loader = repository.open(treeWalk.getObjectId(0));
                                content = new String(loader.getBytes(), StandardCharsets.UTF_8);
                                break;
                            }
                        }
                    }
                }
            }

            if (content == null) {
                throw new IllegalArgumentException("Config not found in version: " + version);
            }

            ConfigDTO configDTO = new ConfigDTO();
            configDTO.setApplication(application);
            configDTO.setProfile(profile);
            configDTO.setContent(content);
            configDTO.setFormat(format);
            configDTO.setDescription("Rollback to version: " + version.substring(0, 8));
            configDTO.setCreatedBy("config-center");

            return publishConfig(configDTO);
        }
    }

    private void cleanupOldVersions(Git git, String application, String profile) throws GitAPIException, IOException {
    }

    public String getConfigContentByVersion(String application, String profile, String version) throws Exception {
        File gitDir = new File(gitUri);
        try (Git git = Git.open(gitDir)) {
            Repository repository = git.getRepository();
            ObjectId commitId = repository.resolve(version);
            if (commitId == null) {
                throw new IllegalArgumentException("Version not found: " + version);
            }

            String pathPrefix = application + "/" + profile + "/";

            try (RevCommit commit = repository.parseCommit(commitId)) {
                try (TreeWalk treeWalk = TreeWalk.forPath(repository, application + "/" + profile, commit.getTree())) {
                    if (treeWalk != null && treeWalk.isSubtree()) {
                        treeWalk.enterSubtree();
                        while (treeWalk.next()) {
                            String path = treeWalk.getPathString();
                            if (path.endsWith(".yml") || path.endsWith(".yaml") || path.endsWith(".json")) {
                                ObjectLoader loader = repository.open(treeWalk.getObjectId(0));
                                return new String(loader.getBytes(), StandardCharsets.UTF_8);
                            }
                        }
                    }
                }
            }
        }
        return null;
    }
}
