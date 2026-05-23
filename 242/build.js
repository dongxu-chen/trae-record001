const fs = require('fs');
const terser = require('terser');

async function build() {
  const code = fs.readFileSync('src/index.js', 'utf-8');
  
  const result = await terser.minify(code, {
    compress: {
      dead_code: true,
      drop_console: false,
      drop_debugger: true,
      unused: true
    },
    mangle: {
      toplevel: true
    }
  });

  if (result.error) {
    console.error('Minify error:', result.error);
    process.exit(1);
  }

  if (!fs.existsSync('dist')) {
    fs.mkdirSync('dist');
  }

  fs.writeFileSync('dist/perf-sdk.min.js', result.code);
  fs.writeFileSync('dist/perf-sdk.esm.js', result.code);

  const size = Buffer.byteLength(result.code, 'utf8');
  console.log(`Build successful!`);
  console.log(`dist/perf-sdk.min.js: ${size} bytes (${(size/1024).toFixed(2)} KB)`);
  console.log(`Size < 10KB: ${size < 10240 ? 'YES ✓' : 'NO ✗'}`);
}

build().catch(console.error);
