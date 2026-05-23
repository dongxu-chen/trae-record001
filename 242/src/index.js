const queue = [];
const trackMap = new Map();
const metrics = {};
let config = {
  reportUrl: '',
  sampleRate: 1,
  recordSampleRate: 0.01,
  appId: '',
  userId: '',
  batchSize: 10,
  delay: 2000,
  enableRecord: false
};
let isInited = false;
let sampled = null;
let timer = null;
let firstInputTime = 0;
let recordState = null;

function hashDjb2(str) {
  let hash = 5381;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash) + str.charCodeAt(i);
  }
  return Math.abs(hash) / 2147483647;
}

function getDeviceId() {
  const key = '__perf_did';
  try {
    let did = localStorage.getItem(key);
    if (!did) {
      did = 'd_' + Math.random().toString(36).slice(2, 14) + Date.now().toString(36);
      localStorage.setItem(key, did);
    }
    return did;
  } catch (e) {
    return 'd_' + Date.now();
  }
}

function shouldSample() {
  if (sampled !== null) return sampled;
  const id = config.userId || getDeviceId();
  const seed = id + '|' + config.appId;
  sampled = hashDjb2(seed) < config.sampleRate;
  return sampled;
}

function shouldRecord() {
  if (!config.enableRecord) return false;
  const id = config.userId || getDeviceId();
  const seed = id + '|' + config.appId + '|record';
  return hashDjb2(seed) < config.recordSampleRate;
}

function now() {
  return performance.now ? performance.now() : Date.now();
}

function round(n) {
  return n > 0 ? Math.round(n * 100) / 100 : 0;
}

function enqueue(data) {
  if (!shouldSample()) return;
  queue.push({
    ...data,
    timestamp: Date.now(),
    appId: config.appId,
    userId: config.userId,
    url: location.href,
    ua: navigator.userAgent
  });
  if (queue.length >= config.batchSize) flush();
}

function flush() {
  if (!queue.length || !config.reportUrl) return;
  const data = queue.splice(0, queue.length);
  const body = JSON.stringify(data);
  try {
    if (navigator.sendBeacon) {
      navigator.sendBeacon(config.reportUrl, body);
    } else {
      const img = new Image();
      img.src = config.reportUrl + '?d=' + encodeURIComponent(body.slice(0, 2000));
    }
  } catch (e) {}
}

function startTimer() {
  if (timer) return;
  timer = setInterval(flush, config.delay);
}

function startTrack(name, data) {
  trackMap.set(name, {
    startTime: now(),
    data
  });
}

function endTrack(name, extraData) {
  const track = trackMap.get(name);
  if (!track) return null;
  trackMap.delete(name);
  const duration = round(now() - track.startTime);
  enqueue({
    type: 'track',
    name,
    duration,
    data: { ...track.data, ...extraData }
  });
  return duration;
}

function trackEvent(name, data) {
  enqueue({
    type: 'event',
    name,
    data
  });
}

function supportLayoutShift() {
  try {
    return window.PerformanceObserver &&
      PerformanceObserver.supportedEntryTypes &&
      PerformanceObserver.supportedEntryTypes.includes('layout-shift');
  } catch (e) {
    return false;
  }
}

function isSafari() {
  return /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
}

function initCLSPolyfill() {
  let clsValue = 0;
  let lastPositions = new Map();
  let isObserving = true;
  let lastReportTime = 0;
  const REPORT_INTERVAL = 1000;

  function getViewportSize() {
    return {
      width: window.innerWidth,
      height: window.innerHeight
    };
  }

  function calculateImpact(element) {
    const rect = element.getBoundingClientRect();
    const viewport = getViewportSize();
    if (rect.bottom < 0 || rect.top > viewport.height ||
        rect.right < 0 || rect.left > viewport.width) {
      return 0;
    }
    const visibleWidth = Math.min(rect.right, viewport.width) - Math.max(rect.left, 0);
    const visibleHeight = Math.min(rect.bottom, viewport.height) - Math.max(rect.top, 0);
    return (visibleWidth * visibleHeight) / (viewport.width * viewport.height);
  }

  function checkLayout() {
    if (!isObserving) return;
    const viewport = getViewportSize();
    const elements = document.body.querySelectorAll('*');
    let maxShift = 0;
    let hasShift = false;

    for (let i = 0; i < elements.length && i < 200; i++) {
      const el = elements[i];
      const id = el;
      const rect = el.getBoundingClientRect();
      const posKey = `${Math.round(rect.left)},${Math.round(rect.top)}`;
      const lastPos = lastPositions.get(id);

      if (lastPos && lastPos !== posKey) {
        const [lastX, lastY] = lastPos.split(',').map(Number);
        const dx = Math.abs(rect.left - lastX) / viewport.width;
        const dy = Math.abs(rect.top - lastY) / viewport.height;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const impact = calculateImpact(el);

        if (distance > 0.005 && impact > 0.001) {
          const shiftScore = distance * impact;
          if (shiftScore > maxShift) maxShift = shiftScore;
          hasShift = true;
        }
      }
      lastPositions.set(id, posKey);
    }

    if (hasShift && Date.now() - lastReportTime > REPORT_INTERVAL) {
      clsValue += maxShift * 0.3;
      lastReportTime = Date.now();
      metrics.CLS = clsValue;
      enqueue({
        type: 'metric',
        metric: 'CLS',
        value: round(clsValue),
        method: 'polyfill'
      });
    }
  }

  try {
    const observer = new MutationObserver((mutations) => {
      for (const mut of mutations) {
        if (mut.type === 'childList' || mut.type === 'attributes') {
          requestAnimationFrame(checkLayout);
          break;
        }
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['style', 'class']
    });

    window.addEventListener('scroll', () => {
      requestAnimationFrame(checkLayout);
    }, { passive: true });

    window.addEventListener('resize', () => {
      lastPositions.clear();
      requestAnimationFrame(checkLayout);
    });
  } catch (e) {}

  setTimeout(() => {
    checkLayout();
  }, 100);
}

function initMetrics() {
  const po = window.PerformanceObserver;
  if (!po) return;

  try {
    new po((list) => {
      for (const entry of list.getEntries()) {
        const name = entry.name;
        if (name === 'first-paint') {
          metrics.FP = entry.startTime;
          enqueue({
            type: 'metric',
            metric: 'FP',
            value: round(entry.startTime)
          });
        } else if (name === 'first-contentful-paint') {
          metrics.FCP = entry.startTime;
          enqueue({
            type: 'metric',
            metric: 'FCP',
            value: round(entry.startTime)
          });
        }
      }
    }).observe({ entryTypes: ['paint'] });
  } catch (e) {}

  try {
    let lcpValue = 0;
    const lcpObserver = new po((list) => {
      const entries = list.getEntries();
      const last = entries[entries.length - 1];
      if (last && last.startTime > lcpValue) {
        lcpValue = last.startTime;
        metrics.LCP = lcpValue;
        enqueue({
          type: 'metric',
          metric: 'LCP',
          value: round(lcpValue),
          element: last.element?.tagName || ''
        });
      }
    });
    lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
    setTimeout(() => lcpObserver.disconnect(), 5000);
  } catch (e) {}

  try {
    if (supportLayoutShift()) {
      let clsValue = 0;
      new po((list) => {
        for (const entry of list.getEntries()) {
          if (!entry.hadRecentInput) {
            clsValue += entry.value;
          }
        }
        metrics.CLS = clsValue;
        enqueue({
          type: 'metric',
          metric: 'CLS',
          value: round(clsValue),
          method: 'native'
        });
      }).observe({ entryTypes: ['layout-shift'] });
    } else if (isSafari()) {
      initCLSPolyfill();
    }
  } catch (e) {}

  try {
    new po((list) => {
      const first = list.getEntries()[0];
      if (first) {
        firstInputTime = first.startTime;
        metrics.FID = first.processingStart - first.startTime;
        enqueue({
          type: 'metric',
          metric: 'FID',
          value: round(first.processingStart - first.startTime)
        });
      }
    }).observe({ entryTypes: ['first-input'] });
  } catch (e) {}

  try {
    let tbtValue = 0;
    new po((list) => {
      for (const entry of list.getEntries()) {
        if (entry.duration > 50) {
          tbtValue += entry.duration - 50;
        }
      }
      metrics.TBT = tbtValue;
      enqueue({
        type: 'metric',
        metric: 'TBT',
        value: round(tbtValue)
      });
    }).observe({ entryTypes: ['longtask'] });
  } catch (e) {}
}

function initResources() {
  const po = window.PerformanceObserver;
  const reported = new Set();
  let totalResourceSize = 0;
  let imageCount = 0;
  let largeImageCount = 0;

  const handleEntries = (entries) => {
    for (const entry of entries) {
      if (reported.has(entry.name)) continue;
      if (entry.initiatorType === 'xmlhttprequest' || entry.initiatorType === 'fetch') {
        continue;
      }
      reported.add(entry.name);
      
      if (entry.transferSize) {
        totalResourceSize += entry.transferSize;
      }
      if (entry.initiatorType === 'img') {
        imageCount++;
        if ((entry.transferSize || 0) > 100 * 1024) {
          largeImageCount++;
        }
      }
      
      enqueue({
        type: 'resource',
        url: entry.name,
        type: entry.initiatorType || 'other',
        duration: round(entry.duration),
        size: entry.transferSize || 0,
        dns: round(entry.domainLookupEnd - entry.domainLookupStart),
        tcp: round(entry.connectEnd - entry.connectStart),
        ttfb: round(entry.responseStart - entry.requestStart)
      });
    }
    metrics.totalResourceSize = totalResourceSize;
    metrics.imageCount = imageCount;
    metrics.largeImageCount = largeImageCount;
  };

  if (po) {
    try {
      new po((list) => handleEntries(list.getEntries())).observe({ entryTypes: ['resource'] });
    } catch (e) {}
  }

  setTimeout(() => {
    const entries = performance.getEntriesByType('resource');
    handleEntries(entries);
  }, 3000);
}

function initErrors() {
  window.addEventListener('error', (e) => {
    enqueue({
      type: 'error',
      errorType: 'js',
      message: e.message,
      filename: e.filename,
      lineno: e.lineno,
      colno: e.colno,
      stack: e.error?.stack?.slice(0, 500) || ''
    });
  }, true);

  window.addEventListener('unhandledrejection', (e) => {
    enqueue({
      type: 'error',
      errorType: 'promise',
      message: e.reason?.message || String(e.reason).slice(0, 200),
      stack: e.reason?.stack?.slice(0, 500) || ''
    });
  }, true);
}

function initXhr() {
  const origOpen = XMLHttpRequest.prototype.open;
  const origSend = XMLHttpRequest.prototype.send;
  let slowApiCount = 0;

  XMLHttpRequest.prototype.open = function (method, url) {
    this._method = method;
    this._url = url;
    this._startTime = now();
    return origOpen.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function () {
    const onEnd = () => {
      const duration = round(now() - this._startTime);
      if (duration > 3000) slowApiCount++;
      metrics.slowApiCount = slowApiCount;
      enqueue({
        type: 'api',
        method: this._method,
        url: this._url,
        status: this.status,
        duration
      });
    };
    this.addEventListener('load', onEnd);
    this.addEventListener('error', onEnd);
    this.addEventListener('abort', onEnd);
    return origSend.apply(this, arguments);
  };
}

function initFetch() {
  if (!window.fetch) return;
  const origFetch = window.fetch;
  let slowApiCount = 0;
  window.fetch = function (url, opts = {}) {
    const startTime = now();
    const method = opts.method || 'GET';
    return origFetch.apply(this, arguments).then((res) => {
      const duration = round(now() - startTime);
      if (duration > 3000) slowApiCount++;
      metrics.slowApiCount = slowApiCount;
      enqueue({
        type: 'api',
        method,
        url: typeof url === 'string' ? url : url.href,
        status: res.status,
        duration
      });
      return res;
    }).catch((err) => {
      const duration = round(now() - startTime);
      enqueue({
        type: 'api',
        method,
        url: typeof url === 'string' ? url : url.href,
        status: 0,
        duration,
        error: err.message
      });
      throw err;
    });
  };
}

function calculateFirstScreen() {
  const viewportHeight = window.innerHeight;
  const images = document.querySelectorAll('img');
  let maxImageLoadTime = 0;

  for (const img of images) {
    const rect = img.getBoundingClientRect();
    if (rect.top < viewportHeight && rect.bottom > 0) {
      if (img.complete) {
        maxImageLoadTime = Math.max(maxImageLoadTime, performance.now());
      }
    }
  }

  const nav = performance.getEntriesByType('navigation')[0];
  const domContentLoaded = nav ? nav.domContentLoadedEventEnd : 0;

  return Math.max(domContentLoaded, maxImageLoadTime);
}

function calculateScore() {
  const scores = [];
  const suggestions = [];

  const lcp = metrics.LCP || 0;
  const cls = metrics.CLS || 0;
  const fid = metrics.FID || 0;
  const fcp = metrics.FCP || 0;
  const tbt = metrics.TBT || 0;

  if (lcp > 0) {
    if (lcp <= 2500) {
      scores.push(30);
    } else if (lcp <= 4000) {
      scores.push(15);
      suggestions.push('LCP偏慢，建议优化首屏资源加载');
    } else {
      scores.push(5);
      suggestions.push('LCP过慢，急需优化最大内容绘制');
    }
  }

  if (cls >= 0) {
    if (cls <= 0.1) {
      scores.push(25);
    } else if (cls <= 0.25) {
      scores.push(12);
      suggestions.push('CLS偏高，建议固定元素尺寸减少布局偏移');
    } else {
      scores.push(3);
      suggestions.push('CLS过高，存在严重布局跳动问题');
    }
  }

  if (fid > 0) {
    if (fid <= 100) {
      scores.push(25);
    } else if (fid <= 300) {
      scores.push(12);
      suggestions.push('FID偏慢，建议减少主线程阻塞');
    } else {
      scores.push(3);
      suggestions.push('FID过慢，主线程阻塞严重');
    }
  }

  if (fcp > 0) {
    if (fcp <= 1800) {
      scores.push(10);
    } else if (fcp <= 3000) {
      scores.push(5);
      suggestions.push('FCP偏慢，建议优化首屏内容');
    } else {
      scores.push(2);
      suggestions.push('FCP过慢，白屏时间过长');
    }
  }

  if (tbt > 0) {
    if (tbt <= 200) {
      scores.push(10);
    } else if (tbt <= 600) {
      scores.push(5);
      suggestions.push('TBT偏高，建议拆分长任务');
    } else {
      scores.push(2);
      suggestions.push('TBT过高，长任务过多');
    }
  }

  if (metrics.totalResourceSize > 5 * 1024 * 1024) {
    suggestions.push('页面资源总体积过大，建议压缩资源');
  }
  if (metrics.largeImageCount > 0) {
    suggestions.push(`存在${metrics.largeImageCount}张大于100KB的图片，建议压缩图片`);
  }
  if (metrics.slowApiCount > 2) {
    suggestions.push(`存在${metrics.slowApiCount}个慢接口，建议优化API响应`);
  }

  const totalScore = scores.reduce((a, b) => a + b, 0);
  
  return {
    score: Math.min(100, totalScore),
    level: totalScore >= 80 ? 'good' : totalScore >= 50 ? 'medium' : 'poor',
    suggestions
  };
}

function initNavigatorDomReady() {
  const nav = performance.getEntriesByType('navigation')[0];
  if (nav) {
    enqueue({
      type: 'navigation',
      phase: 'dom_ready',
      dns: round(nav.domainLookupEnd - nav.domainLookupStart),
      tcp: round(nav.connectEnd - nav.connectStart),
      ssl: round(nav.secureConnectionStart ? nav.connectEnd - nav.secureConnectionStart : 0),
      ttfb: round(nav.responseStart - nav.requestStart),
      domReady: round(nav.domContentLoadedEventEnd - nav.startTime),
      domParse: round(nav.domInteractive - nav.responseEnd),
      response: round(nav.responseEnd - nav.responseStart)
    });
  }
}

function initNavigatorLoad() {
  const nav = performance.getEntriesByType('navigation')[0];
  const firstScreen = calculateFirstScreen();
  metrics.FST = firstScreen;

  if (nav) {
    enqueue({
      type: 'navigation',
      phase: 'load',
      dns: round(nav.domainLookupEnd - nav.domainLookupStart),
      tcp: round(nav.connectEnd - nav.connectStart),
      ssl: round(nav.secureConnectionStart ? nav.connectEnd - nav.secureConnectionStart : 0),
      ttfb: round(nav.responseStart - nav.requestStart),
      domReady: round(nav.domContentLoadedEventEnd - nav.startTime),
      load: round(nav.loadEventEnd - nav.startTime),
      domParse: round(nav.domInteractive - nav.responseEnd),
      firstScreen: round(firstScreen - nav.startTime),
      response: round(nav.responseEnd - nav.responseStart),
      redirect: round(nav.redirectEnd - nav.redirectStart)
    });
  }

  enqueue({
    type: 'metric',
    metric: 'FST',
    value: round(firstScreen)
  });

  let tti = 0;
  if (window.PerformanceLongTaskTiming) {
    const longTasks = performance.getEntriesByType('longtask');
    if (longTasks.length > 0) {
      const lastLongTask = longTasks[longTasks.length - 1];
      tti = Math.max(firstScreen, lastLongTask.startTime + lastLongTask.duration);
    } else {
      tti = firstScreen;
    }
  } else {
    tti = firstScreen + 50;
  }
  metrics.TTI = tti;

  enqueue({
    type: 'metric',
    metric: 'TTI',
    value: round(tti)
  });

  setTimeout(() => {
    const perfResult = calculateScore();
    enqueue({
      type: 'score',
      score: perfResult.score,
      level: perfResult.level,
      suggestions: perfResult.suggestions
    });
  }, 1000);
}

function initRecord() {
  if (!shouldRecord()) return;
  
  const events = [];
  let domSnapshot = null;
  let eventId = 0;

  function captureDomSnapshot() {
    try {
      const html = document.documentElement.outerHTML;
      let compressed = '';
      for (let i = 0; i < html.length; i += 200) {
        compressed += html.slice(i, i + 200).length + '|';
      }
      return {
        time: now(),
        hash: compressed.slice(0, 100),
        width: window.innerWidth,
        height: window.innerHeight,
        url: location.href
      };
    } catch (e) {
      return null;
    }
  }

  function recordEvent(type, data) {
    if (events.length >= 500) return;
    events.push({
      id: ++eventId,
      type,
      time: round(now()),
      data
    });
  }

  domSnapshot = captureDomSnapshot();

  document.addEventListener('click', (e) => {
    const target = e.target;
    recordEvent('click', {
      tag: target.tagName,
      id: target.id,
      className: target.className?.slice(0, 50),
      x: Math.round(e.clientX),
      y: Math.round(e.clientY),
      text: target.textContent?.slice(0, 30)
    });
  }, true);

  document.addEventListener('input', (e) => {
    const target = e.target;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
      recordEvent('input', {
        tag: target.tagName,
        id: target.id,
        type: target.type,
        length: target.value?.length || 0
      });
    }
  }, true);

  document.addEventListener('scroll', () => {
    recordEvent('scroll', {
      x: Math.round(window.scrollX),
      y: Math.round(window.scrollY)
    });
  }, { passive: true });

  window.addEventListener('resize', () => {
    recordEvent('resize', {
      width: window.innerWidth,
      height: window.innerHeight
    });
  });

  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      recordEvent('navigate', { url: lastUrl });
    }
  }).observe(document, { subtree: true, childList: true });

  recordState = {
    snapshot: domSnapshot,
    events
  };

  setTimeout(() => {
    if (recordState && recordState.events.length > 0) {
      enqueue({
        type: 'record',
        snapshot: recordState.snapshot,
        events: recordState.events.slice(0, 200)
      });
    }
  }, 10000);

  window.addEventListener('beforeunload', () => {
    if (recordState && recordState.events.length > 0) {
      const data = {
        type: 'record',
        snapshot: recordState.snapshot,
        events: recordState.events.slice(0, 100)
      };
      try {
        navigator.sendBeacon(config.reportUrl, JSON.stringify([{
          ...data,
          timestamp: Date.now(),
          appId: config.appId,
          userId: config.userId,
          url: location.href,
          ua: navigator.userAgent
        }]));
      } catch (e) {}
    }
  });
}

function init(opts = {}) {
  if (isInited) return;
  isInited = true;

  config = { ...config, ...opts };

  if (!shouldSample()) return;

  initErrors();
  initXhr();
  initFetch();
  initMetrics();
  initResources();

  if (config.enableRecord) {
    initRecord();
  }

  if (document.readyState === 'interactive' || document.readyState === 'complete') {
    setTimeout(initNavigatorDomReady, 0);
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      setTimeout(initNavigatorDomReady, 0);
    });
  }

  if (document.readyState === 'complete') {
    setTimeout(initNavigatorLoad, 0);
  } else {
    window.addEventListener('load', () => {
      setTimeout(initNavigatorLoad, 0);
    });
  }

  startTimer();
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flush();
  });
  window.addEventListener('beforeunload', flush);
}

function setUserId(id) {
  const oldId = config.userId;
  config.userId = id;
  if (oldId !== id) {
    sampled = null;
  }
}

function setTag(key, value) {
  config[key] = value;
}

function reportCustom(data) {
  enqueue({ type: 'custom', data });
}

function getPerformanceScore() {
  return calculateScore();
}

const PerfSDK = {
  init,
  setUserId,
  setTag,
  report: reportCustom,
  flush,
  startTrack,
  endTrack,
  trackEvent,
  getPerformanceScore
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = PerfSDK;
} else if (typeof define === 'function' && define.amd) {
  define([], () => PerfSDK);
} else {
  window.PerfSDK = PerfSDK;
}

const queueToProcess = window.__perf_queue || [];
for (const item of queueToProcess) {
  if (item[0] === 'init') init(item[1]);
  else if (item[0] === 'setUserId') setUserId(item[1]);
  else if (item[0] === 'report') reportCustom(item[1]);
  else if (item[0] === 'startTrack') startTrack(item[1], item[2]);
  else if (item[0] === 'endTrack') endTrack(item[1], item[2]);
  else if (item[0] === 'trackEvent') trackEvent(item[1], item[2]);
}
