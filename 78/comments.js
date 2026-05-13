(function() {
    'use strict';

    var RATE_LIMIT_KEY = 'github_rate_limit_reset';
    var CACHE_DURATION = 5 * 60 * 1000;

    function getConfig() {
        return window.COMMENT_CONFIG || {
            repo: '',
            owner: '',
            label: 'blog-comment',
            theme: 'github-light',
            token: ''
        };
    }

    function isValidConfig() {
        var config = getConfig();
        return config.repo && config.repo.indexOf('/') !== -1;
    }

    function isRateLimited() {
        if (!window.LocalCache) return { limited: false };

        var resetTime = localStorage.getItem(RATE_LIMIT_KEY);
        if (resetTime) {
            var remaining = parseInt(resetTime) * 1000 - Date.now();
            if (remaining > 0) {
                return { limited: true, remaining: remaining };
            }
            localStorage.removeItem(RATE_LIMIT_KEY);
        }
        return { limited: false };
    }

    function setRateLimit(resetTime) {
        localStorage.setItem(RATE_LIMIT_KEY, resetTime.toString());
    }

    function showError(message) {
        var container = document.getElementById('utterances-container');
        if (container) {
            container.innerHTML = '<div class="error-message">' + message + '</div>';
        }
    }

    function showLoading() {
        var container = document.getElementById('utterances-container');
        if (container) {
            container.innerHTML = '<div class="loading">加载评论中...</div>';
        }
    }

    function getPageUrl() {
        return window.location.pathname || '/';
    }

    function loadUtterances() {
        if (!isValidConfig()) {
            showError('请在 config.js 中配置 GitHub 仓库信息。');
            return;
        }

        var config = getConfig();
        var container = document.getElementById('utterances-container');
        if (!container) return;

        var existingScript = container.querySelector('script[src="https://utteranc.es/client.js"]');
        if (existingScript) return;

        var script = document.createElement('script');
        script.src = 'https://utteranc.es/client.js';
        script.setAttribute('repo', config.repo);
        script.setAttribute('issue-term', 'pathname');
        script.setAttribute('label', config.label || 'blog-comment');
        script.setAttribute('theme', config.theme || 'github-light');
        script.crossOrigin = 'anonymous';
        script.async = true;

        container.innerHTML = '';
        container.appendChild(script);
    }

    async function fetchGitHubAPI(url) {
        var config = getConfig();
        var options = {
            headers: {
                'Accept': 'application/vnd.github.v3+json'
            }
        };
        
        if (config.token) {
            options.headers['Authorization'] = 'token ' + config.token;
        }

        var response = await fetch(url, options);
        return response;
    }

    function renderCommentsUI(comments, issueNumber) {
        var container = document.getElementById('utterances-container');
        if (!container) return;

        if (!window.ReplySystem) {
            loadUtterances();
            return;
        }

        var html = '<div class="comments-header">GitHub 评论 (' + comments.length + ')</div>' +
            '<div class="manual-comments" id="manual-comments-list">' +
            window.ReplySystem.renderComments(comments) +
            '</div>' +
            '<div class="new-comment-section">' +
            '<h3 class="new-comment-title">发表评论</h3>' +
            '<div class="new-comment-form">' +
            '<textarea class="new-comment-textarea" placeholder="登录 GitHub 后可在此发表评论。支持 Markdown 和表情。" rows="4"></textarea>' +
            '<div class="new-comment-actions">' +
            '<button type="button" class="new-comment-emoji-btn" title="表情">😊</button>' +
            '<div class="new-comment-right">' +
            '<span class="new-comment-hint">评论将发送到 GitHub Issues</span>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '<div class="utterances-fallback">' +
            '<p>需要登录 GitHub 发表评论：</p>' +
            '</div>' +
            '</div>';

        container.innerHTML = html;

        var list = document.getElementById('manual-comments-list');
        if (list && window.ReplySystem) {
            window.ReplySystem.init(list);
            window.ReplySystem.onSubmitReply = function(replyData) {
                showError('请通过 Utterances 组件登录 GitHub 后发表回复。');
                loadUtterancesFallback(issueNumber);
            };
        }

        loadUtterancesFallback(issueNumber);

        var emojiBtn = container.querySelector('.new-comment-emoji-btn');
        var textarea = container.querySelector('.new-comment-textarea');
        if (emojiBtn && textarea && window.EmojiPicker) {
            window.EmojiPicker.attachToButton(emojiBtn, textarea);
        }
    }

    function loadUtterancesFallback(issueNumber) {
        var fallbackContainer = document.querySelector('.utterances-fallback');
        if (!fallbackContainer) return;

        var config = getConfig();
        var script = document.createElement('script');
        script.src = 'https://utteranc.es/client.js';
        script.setAttribute('repo', config.repo);
        script.setAttribute('issue-term', 'pathname');
        script.setAttribute('label', config.label || 'blog-comment');
        script.setAttribute('theme', config.theme || 'github-light');
        script.crossOrigin = 'anonymous';
        script.async = true;

        fallbackContainer.innerHTML = '';
        fallbackContainer.appendChild(script);
    }

    async function loadCommentsFromAPI() {
        if (!isValidConfig()) {
            showError('请在 config.js 中配置 GitHub 仓库信息。');
            loadUtterances();
            return;
        }

        var rateLimit = isRateLimited();
        if (rateLimit.limited) {
            console.warn('GitHub API 速率限制，剩余 ' + Math.ceil(rateLimit.remaining / 1000) + ' 秒后恢复');
            loadUtterances();
            return;
        }

        var pageUrl = getPageUrl();
        var cachedComments = null;
        if (window.LocalCache) {
            cachedComments = window.LocalCache.getComments(pageUrl);
        }

        if (cachedComments && cachedComments.comments) {
            renderCommentsUI(cachedComments.comments, cachedComments.issueNumber);
        } else {
            showLoading();
        }

        var config = getConfig();
        var repoParts = config.repo.split('/');
        var owner = repoParts[0];
        var repo = repoParts[1];

        try {
            var issuesUrl = 'https://api.github.com/repos/' + owner + '/' + repo + '/issues' +
                '?labels=' + encodeURIComponent(config.label || 'blog-comment') +
                '&state=open&per_page=100';

            var cachedIssues = null;
            if (window.LocalCache) {
                cachedIssues = window.LocalCache.getAPICache(issuesUrl);
            }

            var issues;
            if (cachedIssues) {
                issues = cachedIssues;
            } else {
                var issuesResponse = await fetchGitHubAPI(issuesUrl);

                if (issuesResponse.status === 403) {
                    var resetTime = issuesResponse.headers.get('X-RateLimit-Reset');
                    if (resetTime) {
                        setRateLimit(resetTime);
                    }
                    console.warn('GitHub API 403 速率限制，回退到 Utterances');
                    loadUtterances();
                    return;
                }

                if (!issuesResponse.ok) {
                    throw new Error('获取 Issues 失败: ' + issuesResponse.status);
                }

                issues = await issuesResponse.json();
                if (window.LocalCache) {
                    window.LocalCache.saveAPICache(issuesUrl, issues);
                }
            }

            var targetIssue = null;
            for (var i = 0; i < issues.length; i++) {
                var issue = issues[i];
                if (issue.title === pageUrl || 
                    issue.title.indexOf(pageUrl) !== -1 ||
                    issue.body && issue.body.indexOf(pageUrl) !== -1) {
                    targetIssue = issue;
                    break;
                }
            }

            if (!targetIssue) {
                var container = document.getElementById('utterances-container');
                if (container) {
                    container.innerHTML = '<div class="success-message">暂无评论，使用 Utterances 组件进行评论。</div>';
                }
                loadUtterances();
                return;
            }

            var commentsUrl = 'https://api.github.com/repos/' + owner + '/' + repo + '/issues/' + targetIssue.number + '/comments';

            var cachedCommentsData = null;
            if (window.LocalCache) {
                cachedCommentsData = window.LocalCache.getAPICache(commentsUrl);
            }

            var comments;
            if (cachedCommentsData) {
                comments = cachedCommentsData;
            } else {
                var commentsResponse = await fetchGitHubAPI(commentsUrl);

                if (commentsResponse.status === 403) {
                    var resetTime2 = commentsResponse.headers.get('X-RateLimit-Reset');
                    if (resetTime2) {
                        setRateLimit(resetTime2);
                    }
                    console.warn('GitHub API 403 速率限制，回退到 Utterances');
                    loadUtterances();
                    return;
                }

                if (!commentsResponse.ok) {
                    throw new Error('获取评论失败: ' + commentsResponse.status);
                }

                comments = await commentsResponse.json();
                if (window.LocalCache) {
                    window.LocalCache.saveAPICache(commentsUrl, comments);
                }
            }

            if (window.LocalCache) {
                window.LocalCache.saveComments(pageUrl, {
                    comments: comments,
                    issueNumber: targetIssue.number
                });
            }

            renderCommentsUI(comments, targetIssue.number);

        } catch (error) {
            console.error('加载评论失败:', error);
            loadUtterances();
        }
    }

    window.initComments = function() {
        loadCommentsFromAPI();
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', window.initComments);
    } else {
        window.initComments();
    }

})();
