function TrackingSDK(options) {
    if (!(this instanceof TrackingSDK)) {
        return new TrackingSDK(options);
    }

    this.options = Object.assign({
        serverUrl: 'http://localhost:8080/tracking',
        appId: 'default_app',
        appVersion: '1.0.0',
        channel: 'miniapp',
        platform: 'miniapp',
        debug: false,
        batchSize: 20,
        flushInterval: 5000,
        autoTrackPageView: true,
        autoTrackAppLaunch: true,
        autoTrackAppShow: true,
        autoTrackAppHide: true,
        sessionTimeout: 30 * 60 * 1000
    }, options || {});

    this.queue = [];
    this.anonymousId = wx.getStorageSync('tracking_anonymous_id') || this.generateId('anon_');
    this.deviceId = wx.getStorageSync('tracking_device_id') || this.generateId('dev_');
    this.sessionId = wx.getStorageSync('tracking_session_id');
    this.userId = wx.getStorageSync('tracking_user_id');
    this.lastActivityTime = wx.getStorageSync('tracking_last_activity') || 0;

    wx.setStorageSync('tracking_anonymous_id', this.anonymousId);
    wx.setStorageSync('tracking_device_id', this.deviceId);

    this.init();
}

TrackingSDK.prototype = {
    constructor: TrackingSDK,

    init: function() {
        var self = this;

        this.checkSession();

        if (this.options.autoTrackAppLaunch) {
            wx.onAppLaunch(function(res) {
                self.track('app_launch', {
                    scene: res.scene,
                    query: res.query,
                    shareTicket: res.shareTicket,
                    path: res.path
                });
            });
        }

        if (this.options.autoTrackAppShow) {
            wx.onAppShow(function(res) {
                self.checkSession();
                self.track('app_show', {
                    scene: res.scene,
                    query: res.query,
                    path: res.path
                });
            });
        }

        if (this.options.autoTrackAppHide) {
            wx.onAppHide(function() {
                self.track('app_hide');
                self.flush(true);
            });
        }

        if (this.options.flushInterval > 0) {
            setInterval(function() {
                self.flush();
            }, this.options.flushInterval);
        }

        this.getSystemInfo();
        this.getNetworkType();

        this.log('SDK initialized', {
            anonymousId: this.anonymousId,
            deviceId: this.deviceId,
            sessionId: this.sessionId
        });
    },

    getSystemInfo: function() {
        try {
            var info = wx.getSystemInfoSync();
            this.systemInfo = info;
            this.os = info.platform;
            this.osVersion = info.system;
            this.deviceModel = info.model;
            this.screenWidth = info.windowWidth;
            this.screenHeight = info.windowHeight;
        } catch (e) {}
    },

    getNetworkType: function(callback) {
        var self = this;
        wx.getNetworkType({
            success: function(res) {
                self.networkType = res.networkType;
                if (callback) callback(res.networkType);
            }
        });
    },

    checkSession: function() {
        var now = Date.now();
        if (!this.sessionId || (now - this.lastActivityTime) > this.options.sessionTimeout) {
            this.sessionId = this.generateId('sess_');
            wx.setStorageSync('tracking_session_id', this.sessionId);
            this.log('New session created', this.sessionId);
        }
        this.lastActivityTime = now;
        wx.setStorageSync('tracking_last_activity', now);
    },

    generateId: function(prefix) {
        return prefix + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    },

    getCommonProperties: function() {
        return {
            appId: this.options.appId,
            appVersion: this.options.appVersion,
            channel: this.options.channel,
            platform: this.options.platform,
            anonymousId: this.anonymousId,
            userId: this.userId,
            sessionId: this.sessionId,
            deviceId: this.deviceId,
            os: this.os,
            osVersion: this.osVersion,
            deviceModel: this.deviceModel,
            screenWidth: this.screenWidth,
            screenHeight: this.screenHeight,
            networkType: this.networkType,
            timestamp: Date.now()
        };
    },

    track: function(eventName, properties, callback) {
        this.checkSession();

        var event = Object.assign(
            this.getCommonProperties(),
            { event: eventName },
            { properties: properties || {} }
        );

        this.queue.push(event);

        this.log('Track event:', event);

        if (this.queue.length >= this.options.batchSize) {
            this.flush(false, callback);
        } else if (callback) {
            setTimeout(callback, 0);
        }
    },

    trackPageView: function(page, properties) {
        var pages = getCurrentPages();
        var currentPage = pages[pages.length - 1];
        var props = Object.assign({
            pagePath: currentPage ? currentPage.route : page,
            pageOptions: currentPage ? currentPage.options : {},
            referrerPage: this.currentPage
        }, properties || {});

        this.currentPage = currentPage ? currentPage.route : page;

        this.track('page_view', props);
    },

    trackClick: function(element, properties) {
        var props = Object.assign({
            elementId: element.id || element.dataset.trackId,
            elementName: element.dataset.trackName || element.dataset.trackEvent,
            elementType: element.dataset.trackType
        }, properties || {});

        this.track('click', props);
    },

    login: function(userId, userInfo) {
        this.userId = userId;
        wx.setStorageSync('tracking_user_id', userId);
        var props = Object.assign({
            loginType: 'wechat',
            userId: userId
        }, userInfo || {});
        this.track('login', props);
        this.log('User logged in:', userId);
    },

    logout: function() {
        var oldUserId = this.userId;
        this.track('logout', { userId: oldUserId });
        this.userId = null;
        wx.removeStorageSync('tracking_user_id');
        this.log('User logged out:', oldUserId);
    },

    setUserProfile: function(profile) {
        this.track('profile_set', profile);
    },

    flush: function(immediate, callback) {
        if (this.queue.length === 0) {
            if (callback) callback();
            return;
        }

        var events = this.queue.slice();
        this.queue = [];

        var self = this;
        var url = this.options.serverUrl + (events.length > 1 ? '/v1/track/batch' : '/v1/track');
        var data = events.length === 1 ? events[0] : events;

        wx.request({
            url: url,
            method: 'POST',
            data: data,
            header: {
                'Content-Type': 'application/json'
            },
            success: function(res) {
                self.log('Event sent, status:', res.statusCode);
                if (callback) callback(res.statusCode === 200, res.data);
            },
            fail: function(err) {
                self.queue = events.concat(self.queue);
                self.log('Event send failed:', err);
                if (callback) callback(false, err);
            }
        });
    },

    log: function() {
        if (this.options.debug && console) {
            console.log('[TrackingSDK]', Array.prototype.slice.call(arguments));
        }
    },

    getDistinctId: function() {
        return this.userId || this.anonymousId;
    },

    getSessionId: function() {
        return this.sessionId;
    }
};

module.exports = TrackingSDK;
