package com.configcenter.server.service;

import org.eclipse.jgit.api.Git;
import org.eclipse.jgit.api.errors.GitAPIException;
import org.eclipse.jgit.lib.ObjectId;
import org.eclipse.jgit.revwalk.RevCommit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.config.server.environment.JGitEnvironmentRepository;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

@Service
public class GitService {

    private static final Logger logger = LoggerFactory.getLogger(GitService.class);

    @Value("${spring.cloud.config.server.git.uri}")
    private String gitUri;

    @Value("${spring.cloud.config.server.git.username:}")
    private String gitUsername;

    @Value("${spring.cloud.config.server.git.password:}")
    private String gitPassword;

    @Value("${spring.cloud.config.server.git.basedir:${user.dir}/config-repo-local}")
    private String baseDir;

    private Git git;

    @PostConstruct
    public void init() {
        try {
            File repoDir = new File(baseDir);
            if (repoDir.exists() && new File(repoDir, ".git").exists()) {
                git = Git.open(repoDir);
                git.pull().call();
                logger.info("已打开已存在的Git仓库: {}", baseDir);
            } else {
                if (repoDir.exists()) {
                    deleteDirectory(repoDir);
                }
                repoDir.mkdirs();
                git = Git.cloneRepository()
                        .setURI(gitUri)
                        .setDirectory(repoDir)
                        .call();
                logger.info("已克隆Git仓库: {}", gitUri);
            }
        } catch (Exception e) {
            logger.error("初始化Git仓库失败", e);
            throw new RuntimeException("初始化Git仓库失败: " + e.getMessage(), e);
        }
    }

    public String commitAndPush(String application, String profile, String label,
                                 String configContent, String commitMessage) {
        try {
            String fileName = getConfigFileName(application, profile);
            Path configDir = Paths.get(baseDir, label);
            Files.createDirectories(configDir);

            File configFile = configDir.resolve(fileName).toFile();
            try (FileWriter writer = new FileWriter(configFile)) {
                writer.write(configContent);
            }

            git.add().addFilepattern(label + "/" + fileName).call();

            RevCommit commit = git.commit()
                    .setMessage("[" + application + "] " + commitMessage)
                    .call();

            ObjectId commitId = commit.getId();
            logger.info("配置已提交到Git, Commit ID: {}", commitId.getName());

            git.push().call();
            logger.info("配置已推送到远程仓库");

            return commitId.getName();
        } catch (IOException | GitAPIException e) {
            logger.error("Git操作失败", e);
            throw new RuntimeException("Git操作失败: " + e.getMessage(), e);
        }
    }

    public String getConfigContent(String application, String profile, String label) {
        try {
            String fileName = getConfigFileName(application, profile);
            Path configFile = Paths.get(baseDir, label, fileName);

            if (Files.exists(configFile)) {
                return new String(Files.readAllBytes(configFile));
            }
            return null;
        } catch (IOException e) {
            logger.error("读取配置文件失败", e);
            return null;
        }
    }

    private String getConfigFileName(String application, String profile) {
        if (profile == null || profile.isEmpty() || "default".equals(profile)) {
            return application + ".yml";
        }
        return application + "-" + profile + ".yml";
    }

    private void deleteDirectory(File directory) {
        File[] files = directory.listFiles();
        if (files != null) {
            for (File file : files) {
                if (file.isDirectory()) {
                    deleteDirectory(file);
                } else {
                    file.delete();
                }
            }
        }
        directory.delete();
    }
}
