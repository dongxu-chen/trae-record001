const { spawn } = require('child_process');
const path = require('path');

const npmPath = 'npm';
const args = ['install'];
const cwd = path.resolve(__dirname);

console.log('Installing dependencies...');

const npm = spawn(npmPath, args, {
  cwd,
  stdio: 'inherit',
  shell: true
});

npm.on('close', (code) => {
  console.log(`npm install exited with code ${code}`);
  process.exit(code);
});
