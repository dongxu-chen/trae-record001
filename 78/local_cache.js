(function() {
    'use strict';

    var COMMENT_CACHE_KEY = 'blog_comments_cache';
    var API_CACHE_PREFIX = 'github_api_cache_';
    var DEFAULT_DURATION = 5 * 60 * 1000;
    var MAX_STORAGE = 4 * 1024 * 1024;

    function getStorageSize() {
        var total = 0;
        for (var key in localStorage) {
            if (localStorage.hasOwnProperty(key)) {
                total += (localStorage[key].length + key.length) * 2;
            }
        }
        return total;
    }

    function cleanupOldCache() {
        var keys = [];
        for (var key in localStorage) {
            if (key.indexOf(API_CACHE_PREFIX) === 0 || key === COMMENT_CACHE_KEY) {
                try {
                    var data = JSON.parse(localStorage[key]);
                    if (data && data.timestamp) {
                        keys.push({ key: key, time: data.timestamp });
                    }
                } catch (e) {}
            }
        }
        keys.sort(function(a, b) { return a.time - b.time; });
        for (var i = 0; i < Math.floor(keys.length / 2); i++) {
            localStorage.removeItem(keys[i].key);
        }
    }

    function setItem(key, value) {
        try {
            localStorage.setItem(key, value);
            return true;
        } catch (e) {
            if (e.name === 'QuotaExceededError' || e.name === 'NS_ERROR_DOM_QUOTA_REACHED') {
                cleanupOldCache();
                try {
                    localStorage.setItem(key, value);
                    return true;
                } catch (e2) {
                    console.warn('localStorage 空间不足');
                    return false;
                }
            }
            return false;
        }
    }

    window.LocalCache = {
        saveComments: function(pageUrl, comments) {
            var data = {
                comments: comments,
                timestamp: Date.now()
            };
            var value = JSON.stringify(data);
            return setItem(COMMENT_CACHE_KEY + '_' + btoa(pageUrl).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''), value);
        },

        getComments: function(pageUrl) {
            var key = COMMENT_CACHE_KEY + '_' + btoa(pageUrl).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
            var cached = localStorage.getItem(key);
            if (cached) {
                try {
                    var data = JSON.parse(cached);
                    if (Date.now() - data.timestamp < DEFAULT_DURATION * 12) {
                        return data.comments;
                    }
                } catch (e) {}
            }
            return null;
        },

        savePendingReply: function(replyData) {
            var key = 'pending_replies';
            var pending = [];
            try {
                var existing = localStorage.getItem(key);
                if (existing) {
                    pending = JSON.parse(existing);
                }
            } catch (e) {}
            replyData.timestamp = Date.now();
            pending.push(replyData);
            return setItem(key, JSON.stringify(pending));
        },

        getPendingReplies: function() {
            var key = 'pending_replies';
            try {
                var data = localStorage.getItem(key);
                if (data) {
                    return JSON.parse(data);
                }
            } catch (e) {}
            return [];
        },

        clearPendingReplies: function() {
            localStorage.removeItem('pending_replies');
        },

        saveAPICache: function(url, data) {
            var key = API_CACHE_PREFIX + btoa(url).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
            var cacheData = {
                data: data,
                timestamp: Date.now()
            };
            return setItem(key, JSON.stringify(cacheData));
        },

        getAPICache: function(url, maxAge) {
            var key = API_CACHE_PREFIX + btoa(url).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
            var cached = localStorage.getItem(key);
            if (cached) {
                try {
                    var cacheData = JSON.parse(cached);
                    var age = maxAge || DEFAULT_DURATION;
                    if (Date.now() - cacheData.timestamp < age) {
                        return cacheData.data;
                    }
                } catch (e) {}
            }
            return null;
        },

        clearAll: function() {
            for (var key in localStorage) {
                if (key.indexOf(API_CACHE_PREFIX) === 0 || 
                    key.indexOf(COMMENT_CACHE_KEY) === 0 ||
                    key === 'pending_replies') {
                    localStorage.removeItem(key);
                }
            }
        },

        getStats: function() {
            return {
                size: getStorageSize(),
                used: (getStorageSize() / 1024).toFixed(2) + ' KB'
            };
        }
    };

})();
