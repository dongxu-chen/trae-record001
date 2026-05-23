const terser = require('@rollup/plugin-terser');

module.exports = {
  input: 'src/index.js',
  output: [
    {
      file: 'dist/perf-sdk.min.js',
      format: 'iife',
      name: 'PerfSDK',
      plugins: [terser()],
      sourcemap: false
    },
    {
      file: 'dist/perf-sdk.esm.js',
      format: 'esm',
      plugins: [terser()],
      sourcemap: false
    }
  ]
};
