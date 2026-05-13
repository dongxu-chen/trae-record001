(function() {
    'use strict';

    var replyFormCache = {};

    function generateId() {
        return 'reply-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }

    function formatDate(dateString) {
        var date = new Date(dateString);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function escapeHTML(str) {
        if (!str) return '';
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function parseReplyContext(body) {
        if (!body) return { text: body, replyTo: null };
        var match = body.match(/^> \[reply to: (.+?)\]\((\d+)\)\n\n/);
        if (match) {
            return {
                text: body.substring(match[0].length),
                replyTo: {
                    author: match[1],
                    id: parseInt(match[2])
                }
            };
        }
        return { text: body, replyTo: null };
    }

    function renderReplyContext(replyTo) {
        if (!replyTo) return '';
        return '<div class="reply-context">' +
            '<span class="reply-context-label">回复</span>' +
            '<span class="reply-context-user">@' + escapeHTML(replyTo.author) + '</span>' +
            '</div>';
    }

    function renderCommentItem(comment, depth, hasChildren) {
        var parsed = parseReplyContext(comment.body);
        var avatar = comment.user ? comment.user.avatar_url : '';
        var author = comment.user ? comment.user.login : '匿名';
        var date = formatDate(comment.created_at);
        var commentId = comment.id || generateId();

        var html = '<div class="comment-item" data-comment-id="' + commentId + '" data-depth="' + depth + '">' +
            '<div class="comment-header">' +
            '<img src="' + avatar + '" class="comment-avatar" alt="' + escapeHTML(author) + '">' +
            '<span class="comment-author">' + escapeHTML(author) + '</span>' +
            '<span class="comment-date">· ' + date + '</span>' +
            '<div class="comment-actions">' +
            '<button class="reply-btn" data-reply-to="' + commentId + '" data-reply-author="' + escapeHTML(author) + '">回复</button>' +
            '</div>' +
            '</div>' +
            (parsed.replyTo ? renderReplyContext(parsed.replyTo) : '') +
            '<div class="comment-body">' + (parsed.text || comment.body) + '</div>' +
            '</div>';

        return html;
    }

    function buildCommentTree(comments) {
        var map = {};
        var roots = [];

        for (var i = 0; i < comments.length; i++) {
            var comment = comments[i];
            var parsed = parseReplyContext(comment.body);
            comment._parsed = parsed;
            comment._replies = [];
            map[comment.id] = comment;
        }

        for (var j = 0; j < comments.length; j++) {
            var c = comments[j];
            if (c._parsed && c._parsed.replyTo && map[c._parsed.replyTo.id]) {
                map[c._parsed.replyTo.id]._replies.push(c);
            } else {
                roots.push(c);
            }
        }

        return roots;
    }

    function renderNestedComments(comments, depth) {
        if (!comments || comments.length === 0) return '';

        var currentDepth = depth || 0;
        var html = '<div class="comments-nested level-' + currentDepth + '">';

        for (var i = 0; i < comments.length; i++) {
            var comment = comments[i];
            var hasChildren = comment._replies && comment._replies.length > 0;

            html += renderCommentItem(comment, currentDepth, hasChildren);

            if (hasChildren) {
                html += renderNestedComments(comment._replies, currentDepth + 1);
            }
        }

        html += '</div>';
        return html;
    }

    function createReplyForm(commentId, replyAuthor) {
        var formId = 'reply-form-' + commentId;

        if (replyFormCache[formId]) {
            return replyFormCache[formId];
        }

        var form = document.createElement('div');
        form.className = 'reply-form-container';
        form.id = formId;
        form.innerHTML = '<div class="reply-form">' +
            '<div class="reply-form-header">' +
            '<span class="reply-to-label">回复 @' + escapeHTML(replyAuthor) + '</span>' +
            '<button type="button" class="cancel-reply-btn">取消</button>' +
            '</div>' +
            '<textarea class="reply-textarea" placeholder="写下你的回复..." rows="3"></textarea>' +
            '<div class="reply-form-actions">' +
            '<button type="button" class="emoji-trigger-btn" title="表情">😊</button>' +
            '<div class="reply-actions-right">' +
            '<span class="char-count">0 / 500</span>' +
            '<button type="button" class="submit-reply-btn">发送回复</button>' +
            '</div>' +
            '</div>' +
            '</div>';

        replyFormCache[formId] = form;
        return form;
    }

    function insertReplyForm(commentElement, form) {
        var existing = commentElement.querySelector('.reply-form-container');
        if (existing) {
            existing.remove();
            return false;
        }

        commentElement.appendChild(form);
        var textarea = form.querySelector('.reply-textarea');
        if (textarea) {
            textarea.focus();
        }

        bindReplyFormEvents(form, commentElement);
        return true;
    }

    function bindReplyFormEvents(form, commentElement) {
        var textarea = form.querySelector('.reply-textarea');
        var emojiBtn = form.querySelector('.emoji-trigger-btn');
        var charCount = form.querySelector('.char-count');
        var submitBtn = form.querySelector('.submit-reply-btn');
        var cancelBtn = form.querySelector('.cancel-reply-btn');

        if (textarea) {
            textarea.addEventListener('input', function() {
                var count = this.value.length;
                if (charCount) {
                    charCount.textContent = count + ' / 500';
                    charCount.classList.toggle('over-limit', count > 500);
                }
                if (submitBtn) {
                    submitBtn.disabled = count === 0 || count > 500;
                }
            });
        }

        if (emojiBtn && textarea && window.EmojiPicker) {
            window.EmojiPicker.attachToButton(emojiBtn, textarea);
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', function() {
                form.remove();
                if (window.EmojiPicker) {
                    window.EmojiPicker.hide();
                }
            });
        }

        if (submitBtn) {
            submitBtn.addEventListener('click', function() {
                var commentId = commentElement.getAttribute('data-comment-id');
                var author = commentElement.querySelector('.comment-author');
                var replyAuthor = author ? author.textContent : '';
                var content = textarea ? textarea.value.trim() : '';

                if (content && content.length <= 500 && window.ReplySystem && window.ReplySystem.onSubmitReply) {
                    window.ReplySystem.onSubmitReply({
                        commentId: commentId,
                        replyAuthor: replyAuthor,
                        content: content
                    });
                }
            });
        }
    }

    function handleReplyButtonClick(e) {
        var btn = e.target.closest('.reply-btn');
        if (!btn) return;

        e.preventDefault();
        e.stopPropagation();

        var commentId = btn.getAttribute('data-reply-to');
        var replyAuthor = btn.getAttribute('data-reply-author');
        var commentItem = btn.closest('.comment-item');

        if (!commentItem) return;

        var form = createReplyForm(commentId, replyAuthor);
        insertReplyForm(commentItem, form);
    }

    window.ReplySystem = {
        renderComments: function(comments) {
            if (!comments || comments.length === 0) {
                return '<div class="no-comments">暂无评论</div>';
            }

            var tree = buildCommentTree(comments);
            return renderNestedComments(tree, 0);
        },

        renderCommentTree: buildCommentTree,

        parseReplyContext: parseReplyContext,

        buildReplyContent: function(replyData) {
            var prefix = '> [reply to: ' + replyData.replyAuthor + '](' + replyData.commentId + ')\n\n';
            return prefix + replyData.content;
        },

        init: function(container) {
            container.addEventListener('click', function(e) {
                if (e.target.closest('.reply-btn')) {
                    handleReplyButtonClick(e);
                }
            });
        },

        onSubmitReply: null,

        clearCache: function() {
            replyFormCache = {};
        }
    };

})();
