(function(w, d, s, q, o){
  w[q] = w[q] || [];
  var e = d.createElement(s),
      t = d.getElementsByTagName(s)[0];
  e.async = 1;
  e.src = o;
  t.parentNode.insertBefore(e, t);
})(window, document, 'script', '__perf_queue', './dist/perf-sdk.min.js');

__perf_queue.push(['init', {
  reportUrl: 'https://your-server.com/report',
  appId: 'your-app-id',
  sampleRate: 0.1
}]);
