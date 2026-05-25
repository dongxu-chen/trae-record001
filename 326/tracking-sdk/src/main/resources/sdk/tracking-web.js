(function(window) {
    'use strict';

    function TrackingSDK(options) {
        if (!(this instanceof TrackingSDK)) {
            return new TrackingSDK(options);
        }

        this.options = Object.assign({
            serverUrl: 'http://localhost:8080/tracking',
            appId: 'default_app',
            appVersion: '1.0.0',
            channel: 'web',
            debug: false,
            batchSize: 20,
            flushInterval: 5000,
            autoTrackPageView: true,
            autoTrackClick: true,
            autoTrackExpose: false,
            sessionTimeout: 30 * 60 * 1000
        }, options || {});

        this.queue = [];
        this.anonymousId = this.getStorage('tracking_anonymous_id') || this.generateId('anon_');
        this.deviceId = this.getStorage('tracking_device_id') || this.generateId('dev_');
        this.sessionId = this.getStorage('tracking_session_id');
        this.userId = this.getStorage('tracking_user_id');
        this.lastActivityTime = parseInt(this.getStorage('tracking_last_activity') || '0');

        this.setStorage('tracking_anonymous_id', this.anonymousId);
        this.setStorage('tracking_device_id', this.deviceId);

        this.init();
    }

    TrackingSDK.prototype = {
        constructor: TrackingSDK,

        init: function() {
            var self = this;

            this.checkSession();

            if (this.options.autoTrackPageView) {
                this.trackPageView();
            }

            if (this.options.autoTrackClick) {
                document.addEventListener('click', function(e) {
                    self.handleClick(e);
                }, true);
            }

            if (this.options.flushInterval > 0) {
                setInterval(function() {
                    self.flush();
                }, this.options.flushInterval);
            }

            window.addEventListener('beforeunload', function() {
                self.flush(true);
            });

            document.addEventListener('visibilitychange', function() {
                if (!document.hidden) {
                    self.checkSession();
                }
            });

            this.log('SDK initialized', {
                anonymousId: this.anonymousId,
                deviceId: this.deviceId,
                sessionId: this.sessionId
            });
        },

        checkSession: function() {
            var now = Date.now();
            if (!this.sessionId || (now - this.lastActivityTime) > this.options.sessionTimeout) {
                this.sessionId = this.generateId('sess_');
                this.setStorage('tracking_session_id', this.sessionId);
                this.log('New session created', this.sessionId);
            }
            this.lastActivityTime = now;
            this.setStorage('tracking_last_activity', String(now));
        },

        generateId: function(prefix) {
            return prefix + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        },

        getStorage: function(key) {
            try {
                return localStorage.getItem(key);
            } catch (e) {
                return null;
            }
        },

        setStorage: function(key, value) {
            try {
                localStorage.setItem(key, value);
            } catch (e) {}
        },

        getCommonProperties: function() {
            return {
                appId: this.options.appId,
                appVersion: this.options.appVersion,
                channel: this.options.channel,
                platform: 'web',
                anonymousId: this.anonymousId,
                userId: this.userId,
                sessionId: this.sessionId,
                deviceId: this.deviceId,
                os: this.getOS(),
                osVersion: this.getOSVersion(),
                screenWidth: window.screen.width,
                screenHeight: window.screen.height,
                networkType: this.getNetworkType(),
                userAgent: navigator.userAgent,
                referrer: document.referrer,
                url: location.href,
                title: document.title,
                timestamp: Date.now()
            };
        },

        getOS: function() {
            var ua = navigator.userAgent;
            if (ua.indexOf('Windows') > -1) return 'Windows';
            if (ua.indexOf('Mac OS') > -1) return 'Mac OS';
            if (ua.indexOf('Linux') > -1) return 'Linux';
            if (ua.indexOf('Android') > -1) return 'Android';
            if (ua.indexOf('iPhone') > -1 || ua.indexOf('iPad') > -1) return 'iOS';
            return 'Unknown';
        },

        getOSVersion: function() {
            var ua = navigator.userAgent;
            var match;
            if ((match = ua.match(/Windows NT ([\d.]+)/))) return match[1];
            if ((match = ua.match(/Android ([\d.]+)/))) return match[1];
            if ((match = ua.match(/OS ([\d_]+)/))) return match[1].replace(/_/g, '.');
            return null;
        },

        getNetworkType: function() {
            if (navigator.connection && navigator.connection.effectiveType) {
                return navigator.connection.effectiveType;
            }
            return navigator.onLine ? 'online' : 'offline';
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

        trackPageView: function(properties) {
            var props = Object.assign({
                pageUrl: location.href,
                pageTitle: document.title,
                referrer: document.referrer,
                referrerDomain: this.getReferrerDomain()
            }, properties || {});

            this.track('page_view', props);
        },

        getReferrerDomain: function() {
            try {
                var a = document.createElement('a');
                a.href = document.referrer;
                return a.hostname;
            } catch (e) {
                return null;
            }
        },

        handleClick: function(e) {
            var target = e.target;
            var element = this.findTrackElement(target);
            if (!element) return;

            var eventName = element.getAttribute('data-track-event') || 'click';
            var properties = {};

            var trackProps = element.getAttribute('data-track-props');
            if (trackProps) {
                try {
                    properties = JSON.parse(trackProps);
                } catch (err) {}
            }

            ['data-track-id', 'data-track-name', 'data-track-type'].forEach(function(attr) {
                var value = element.getAttribute(attr);
                if (value) {
                    properties[attr.replace('data-track-', '')] = value;
                }
            });

            if (element.tagName) {
                properties.tagName = element.tagName.toLowerCase();
            }
            if (element.innerText && element.innerText.trim().length < 50) {
                properties.text = element.innerText.trim();
            }

            var rect = element.getBoundingClientRect();
            properties.position = {
                x: Math.round(rect.left + rect.width / 2),
                y: Math.round(rect.top + rect.height / 2)
            };

            this.track(eventName, properties);
        },

        findTrackElement: function(element) {
            while (element && element.nodeType === 1) {
                if (element.getAttribute('data-track-event') ||
                    element.getAttribute('data-track-id') ||
                    element.getAttribute('data-track-name')) {
                    return element;
                }
                element = element.parentNode;
            }
            return null;
        },

        login: function(userId) {
            this.userId = userId;
            this.setStorage('tracking_user_id', userId);
            this.track('login', {
                loginType: 'account',
                userId: userId
            });
            this.log('User logged in:', userId);
        },

        logout: function() {
            var oldUserId = this.userId;
            this.track('logout', {
                userId: oldUserId
            });
            this.userId = null;
            localStorage.removeItem('tracking_user_id');
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

            var sendData = function() {
                var xhr = new XMLHttpRequest();
                var url = self.options.serverUrl + (events.length > 1 ? '/v1/track/batch' : '/v1/track');

                xhr.open('POST', url, !immediate);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.withCredentials = true;

                xhr.onreadystatechange = function() {
                    if (xhr.readyState === 4) {
                        self.log('Event sent, status:', xhr.status);
                        if (callback) callback(xhr.status === 200, xhr.responseText);
                    }
                };

                if (events.length === 1) {
                    xhr.send(JSON.stringify(events[0]));
                } else {
                    xhr.send(JSON.stringify(events));
                }
            };

            if (navigator.sendBeacon && !immediate) {
                try {
                    var blob = new Blob([JSON.stringify(events.length > 1 ? events : events[0])], {
                        type: 'application/json'
                    });
                    var result = navigator.sendBeacon(
                        this.options.serverUrl + (events.length > 1 ? '/v1/track/batch' : '/v1/track'),
                        blob
                    );
                    if (result) {
                        this.log('Event sent via sendBeacon');
                        if (callback) callback(true);
                        return;
                    }
                } catch (e) {}
            }

            sendData();
        },

        log: function() {
            if (this.options.debug && window.console) {
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

    window.Tracking = TrackingSDK;

    if (typeof define === 'function' && define.amd) {
        define(function() { return TrackingSDK; });
    }

    window.TrackingSDK = new TrackingSDK();

})(window);
