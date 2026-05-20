import ConfigManager from '../src/index.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const configPath = path.join(__dirname, '../config/config.yaml');

const schema = {
  properties: {
    defaults: {
      properties: {
        timeout: { type: 'number' },
        enabled: { type: 'boolean' }
      }
    },
    server: {
      properties: {
        host: { required: true, type: 'string' },
        port: { required: true, type: 'number' },
        enabled: { type: 'boolean' },
        timeout: { type: 'number' }
      }
    },
    database: {
      properties: {
        host: { required: true, type: 'string' },
        port: { required: true, type: 'number' },
        name: { required: true, type: 'string' },
        username: { required: true, type: 'string' },
        password: { required: true, type: 'string' },
        enabled: { type: 'boolean' },
        timeout: { type: 'number' }
      }
    },
    logging: {
      properties: {
        level: { type: 'string' }
      }
    },
    features: { type: 'array' }
  }
};

async function main() {
  console.log('='.repeat(60));
  console.log('🚀 配置管理工具 - 完整功能演示');
  console.log('='.repeat(60) + '\n');

  const configManager = new ConfigManager({
    configPath,
    schema,
    autoReload: true,
    validateOnLoad: true,
    autoPush: false,
    encryption: {
      secretKey: process.env.CONFIG_ENCRYPTION_KEY || 'demo-secret-key-12345',
      paths: ['database.password', 'database.username']
    },
    audit: {
      logPath: path.join(__dirname, '../logs/audit.log'),
      consoleOutput: true
    },
    registry: {
      type: 'consul',
      host: 'localhost',
      port: 8500,
      basePath: '/config/myapp'
    }
  });

  configManager.on('loaded', (config) => {
    console.log('\n✅ 配置加载成功!');
  });

  configManager.on('changed', ({ oldConfig, newConfig }) => {
    console.log('\n🔄 配置已热更新!');
    console.log('旧配置 server.port:', oldConfig.server.port);
    console.log('新配置 server.port:', newConfig.server.port);
  });

  configManager.on('error', (error) => {
    console.error('❌ 错误:', error.message);
  });

  try {
    await configManager.init();

    console.log('\n' + '='.repeat(60));
    console.log('📖 1. 获取配置示例');
    console.log('='.repeat(60));
    console.log('server.host:', configManager.get('server.host'));
    console.log('server.port:', configManager.get('server.port'));
    console.log('server.timeout (来自锚点):', configManager.get('server.timeout'));
    console.log('database.name:', configManager.get('database.name'));
    console.log('logging.level:', configManager.get('logging.level'));
    console.log('features:', configManager.get('features'));
    console.log('不存在的配置项:', configManager.get('not.exist', '默认值'));

    console.log('\n' + '='.repeat(60));
    console.log('🔐 2. 配置加密示例');
    console.log('='.repeat(60));
    const encrypted = configManager.encrypt('my-secret-password');
    console.log('加密后的值:', encrypted.substring(0, 80) + '...');
    const decrypted = configManager.decrypt(encrypted);
    console.log('解密后的值:', decrypted);

    console.log('\n' + '='.repeat(60));
    console.log('🧪 3. 配置校验示例');
    console.log('='.repeat(60));
    const validation = configManager.validate();
    console.log('校验结果:', validation.valid ? '✅ 通过' : '❌ 失败');
    console.log('错误数量:', validation.errorCount);
    if (!validation.valid) {
      console.log('错误详情:', validation.message);
    }

    console.log('\n' + '='.repeat(60));
    console.log('📝 4. 审计日志示例');
    console.log('='.repeat(60));
    const history = await configManager.getAuditHistory({ limit: 10 });
    console.log(`最近 ${history.length} 条审计记录:`);
    history.slice(0, 5).forEach((entry, i) => {
      console.log(`  ${i + 1}. ${configManager.audit.formatEntry(entry)}`);
    });

    console.log('\n' + '='.repeat(60));
    console.log('☁️  5. 配置中心推送 (Consul)');
    console.log('='.repeat(60));
    console.log('注意: 如需测试推送，请确保 Consul 服务已启动 (localhost:8500)');
    console.log('启动 Consul: consul agent -dev -client=0.0.0.0');
    
    try {
      const pushResult = await configManager.pushToRegistry({ encrypt: true, prefix: 'production' });
      console.log('推送结果:', pushResult.success ? '✅ 成功' : '⚠️  部分失败');
      console.log('成功推送:', pushResult.pushed.length, '个配置项');
      if (pushResult.failed.length > 0) {
        console.log('失败项:', pushResult.failed.length, '个');
      }
    } catch (error) {
      console.log('Consul 连接失败 (如未启动可忽略):', error.message);
    }

    console.log('\n' + '='.repeat(60));
    console.log('👀 6. 热更新监听已启动');
    console.log('='.repeat(60));
    console.log('请修改 config/config.yaml 文件查看热更新效果');
    console.log('按 Ctrl+C 退出\n');

  } catch (error) {
    console.error('初始化失败:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

process.on('SIGINT', () => {
  console.log('\n' + '='.repeat(60));
  console.log('👋 正在退出...');
  console.log('='.repeat(60));
  process.exit(0);
});

main();
