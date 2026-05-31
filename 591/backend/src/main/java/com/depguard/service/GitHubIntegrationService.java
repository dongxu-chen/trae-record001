package com.depguard.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.kohsuke.github.GHBranch;
import org.kohsuke.github.GHContent;
import org.kohsuke.github.GHRepository;
import org.kohsuke.github.GitHub;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class GitHubIntegrationService {

    private final GitHub gitHub;

    @Value("${depguard.github.token:}")
    private String githubToken;

    public String getFileContent(String owner, String repoName, String filePath) {
        try {
            GHRepository repository = gitHub.getRepository(owner + "/" + repoName);
            GHContent content = repository.getFileContent(filePath);
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(content.read()))) {
                return reader.lines().collect(Collectors.joining("\n"));
            }
        } catch (IOException e) {
            log.warn("Failed to get file content {}/{} - {}: {}", owner, repoName, filePath, e.getMessage());
            return null;
        }
    }

    public Map<String, Object> getRepositoryInfo(String owner, String repoName) {
        try {
            GHRepository repository = gitHub.getRepository(owner + "/" + repoName);
            Map<String, Object> info = new HashMap<>();
            info.put("name", repository.getName());
            info.put("fullName", repository.getFullName());
            info.put("htmlUrl", repository.getHtmlUrl());
            info.put("defaultBranch", repository.getDefaultBranch());
            info.put("description", repository.getDescription());
            info.put("language", repository.getLanguage());
            info.put("stars", repository.getStargazersCount());
            info.put("forks", repository.getForks());
            return info;
        } catch (IOException e) {
            log.error("Failed to get repository info for {}/{}: {}", owner, repoName, e.getMessage());
            throw new RuntimeException("GitHub API error: " + e.getMessage(), e);
        }
    }

    public String createBranch(String owner, String repoName, String branchName, String baseBranch) {
        try {
            GHRepository repository = gitHub.getRepository(owner + "/" + repoName);
            GHBranch base = repository.getBranch(baseBranch);
            String sha = base.getSHA1();
            repository.createRef("refs/heads/" + branchName, sha);
            log.info("Created branch {} in {}/{} from {}", branchName, owner, repoName, baseBranch);
            return branchName;
        } catch (IOException e) {
            log.error("Failed to create branch {} in {}/{}: {}", branchName, owner, repoName, e.getMessage());
            throw new RuntimeException("Failed to create branch: " + e.getMessage(), e);
        }
    }

    public void updateFileContent(String owner, String repoName, String branchName,
                                  String filePath, String content, String commitMessage) {
        try {
            GHRepository repository = gitHub.getRepository(owner + "/" + repoName);
            GHContent existingFile = repository.getFileContent(filePath, branchName);
            existingFile.update(content, commitMessage, branchName);
            log.info("Updated file {} in {}/{} on branch {}", filePath, owner, repoName, branchName);
        } catch (IOException e) {
            log.error("Failed to update file {} in {}/{}: {}", filePath, owner, repoName, e.getMessage());
            throw new RuntimeException("Failed to update file: " + e.getMessage(), e);
        }
    }

    public String createPullRequest(String owner, String repoName, String headBranch,
                                    String baseBranch, String title, String body) {
        try {
            GHRepository repository = gitHub.getRepository(owner + "/" + repoName);
            var pr = repository.createPullRequest(title, headBranch, baseBranch, body);
            log.info("Created PR #{} in {}/{}: {}", pr.getNumber(), owner, repoName, title);
            return pr.getHtmlUrl().toString();
        } catch (IOException e) {
            log.error("Failed to create PR in {}/{}: {}", owner, repoName, e.getMessage());
            throw new RuntimeException("Failed to create pull request: " + e.getMessage(), e);
        }
    }

    public boolean isAuthenticated() {
        try {
            gitHub.getMyself();
            return true;
        } catch (IOException e) {
            return false;
        }
    }

    public String createUpgradePR(String owner, String repoName, String baseBranch,
                                  String filePath, String updatedContent,
                                  String groupId, String artifactId,
                                  String currentVersion, String targetVersion) {
        String branchName = "depguard/upgrade-" + artifactId + "-" + targetVersion;
        String commitMessage = String.format("build(deps): upgrade %s:%s from %s to %s",
                groupId, artifactId, currentVersion, targetVersion);
        String prTitle = String.format("Upgrade %s:%s %s → %s", groupId, artifactId, currentVersion, targetVersion);
        String prBody = String.format(
                "## DepGuard: Dependency Upgrade\n\n" +
                "**Dependency:** `%s:%s`\n" +
                "**Current Version:** `%s`\n" +
                "**Target Version:** `%s`\n\n" +
                "This PR was automatically generated by DepGuard.",
                groupId, artifactId, currentVersion, targetVersion);

        createBranch(owner, repoName, branchName, baseBranch);
        updateFileContent(owner, repoName, branchName, filePath, updatedContent, commitMessage);
        return createPullRequest(owner, repoName, branchName, baseBranch, prTitle, prBody);
    }
}
