#!/usr/bin/env node

/**
 * postinstall 脚本：安装 Python 依赖
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const PYTHON_REQUIREMENTS = path.join(__dirname, '..', 'python', 'requirements.txt');

// 查找 Python
async function findPython() {
  const pythonCommands = ['python3', 'python', 'python3.14', 'python3.13', 'python3.12', 'python3.11', 'python3.10'];

  for (const cmd of pythonCommands) {
    try {
      const result = await spawnAsync(cmd, ['--version']);
      if (result.stdout && result.stdout.includes('Python')) {
        return cmd;
      }
    } catch {
      // 继续尝试
    }
  }

  return null;
}

function spawnAsync(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: 'pipe',
      shell: process.platform === 'win32',
      ...options
    });

    let stdout = '';
    let stderr = '';

    if (child.stdout) {
      child.stdout.on('data', (data) => {
        stdout += data.toString();
      });
    }

    if (child.stderr) {
      child.stderr.on('data', (data) => {
        stderr += data.toString();
      });
    }

    child.on('close', (exitCode) => {
      if (exitCode === 0) {
        resolve({ stdout, stderr });
      } else {
        reject(new Error(`Command failed: ${command} ${args.join(' ')}`));
      }
    });

    child.on('error', reject);
  });
}

async function main() {
  if (!fs.existsSync(PYTHON_REQUIREMENTS)) {
    console.warn('requirements.txt not found, skipping Python dependency installation');
    return;
  }

  const pythonCmd = await findPython();
  if (!pythonCmd) {
    console.warn('Python not found, skipping Python dependency installation');
    console.warn('Please install Python 3.10+ and run: pip install -r python/requirements.txt');
    return;
  }

  try {
    // 检查是否已安装
    await spawnAsync(pythonCmd, ['-c', 'import mcp']);
    console.log('Python dependencies already installed');
  } catch {
    // 安装依赖
    console.log('Installing Python dependencies...');
    try {
      await spawnAsync(pythonCmd, ['-m', 'pip', 'install', '-r', PYTHON_REQUIREMENTS], {
        stdio: 'inherit'
      });
      console.log('Python dependencies installed successfully');
    } catch {
      console.warn('Failed to install Python dependencies during postinstall');
      console.warn('Please run manually: pip install -r python/requirements.txt');
    }
  }
}

main().catch(() => {
  // 静默失败，不要阻塞 npm install
});
