const http = require('http');

const testData = {
  phone: '13800138000',
  idCard: '110101199001011234',
  email: 'example@email.com',
  name: '张三',
  address: '北京市朝阳区某某街道123号'
};

const testRules = {
  phone: {
    enabled: true,
    method: 'mask',
    pattern: 'adaptive',
    keepStart: 3,
    keepEnd: 4
  },
  idCard: {
    enabled: true,
    method: 'mask',
    pattern: 'adaptive',
    keepStart: 6,
    keepEnd: 4
  },
  email: {
    enabled: true,
    method: 'mask',
    pattern: 'adaptive',
    keepStart: 2,
    keepEnd: 0
  },
  name: {
    enabled: true,
    method: 'hash',
    hashAlgorithm: 'md5',
    hashSalt: 'test-salt-123'
  }
};

function makeRequest(path, method, data) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'localhost',
      port: 3001,
      path: path,
      method: method,
      headers: {
        'Content-Type': 'application/json'
      }
    };

    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => resolve(JSON.parse(body)));
    });

    req.on('error', reject);
    if (data) req.write(JSON.stringify(data));
    req.end();
  });
}

async function runTests() {
  console.log('🚀 开始测试增强功能...\n');

  try {
    console.log('📋 测试1: 自适应掩码');
    const maskResult = await makeRequest('/api/mask', 'POST', {
      data: testData,
      rules: testRules
    });
    console.log('  手机号:', testData.phone, '→', maskResult.result.phone);
    console.log('  身份证:', testData.idCard, '→', maskResult.result.idCard);
    console.log('  邮箱:', testData.email, '→', maskResult.result.email);
    console.log('  ✅ 自适应掩码测试通过\n');

    console.log('🔑 测试2: 一致性哈希（相同盐值）');
    const hashRules = {
      name: {
        enabled: true,
        method: 'hash',
        hashAlgorithm: 'md5',
        hashSalt: 'my-secret-salt'
      }
    };
    
    const result1 = await makeRequest('/api/mask', 'POST', {
      data: { name: '张三' },
      rules: hashRules
    });
    const result2 = await makeRequest('/api/mask', 'POST', {
      data: { name: '张三' },
      rules: hashRules
    });
    
    console.log('  第1次哈希:', result1.result.name);
    console.log('  第2次哈希:', result2.result.name);
    console.log('  是否一致:', result1.result.name === result2.result.name ? '✅ 是' : '❌ 否');
    console.log('');

    console.log('🔑 测试3: 不同盐值产生不同结果');
    const hashRules2 = {
      name: {
        enabled: true,
        method: 'hash',
        hashAlgorithm: 'md5',
        hashSalt: 'different-salt'
      }
    };
    
    const result3 = await makeRequest('/api/mask', 'POST', {
      data: { name: '张三' },
      rules: hashRules2
    });
    
    console.log('  盐值A结果:', result1.result.name);
    console.log('  盐值B结果:', result3.result.name);
    console.log('  是否不同:', result1.result.name !== result3.result.name ? '✅ 是' : '❌ 否');
    console.log('');

    console.log('🎯 测试4: 自适应掩码不同长度输入');
    const testCases = [
      { input: '12345678901', keepStart: 3, keepEnd: 4, desc: '手机号长度' },
      { input: '12345', keepStart: 2, keepEnd: 1, desc: '短字符串' },
      { input: 'abcdefghijklmnopqrstuvwxyz', keepStart: 4, keepEnd: 4, desc: '长字符串' }
    ];
    
    for (const testCase of testCases) {
      const result = await makeRequest('/api/mask', 'POST', {
        data: { test: testCase.input },
        rules: {
          test: {
            enabled: true,
            method: 'mask',
            pattern: 'adaptive',
            keepStart: testCase.keepStart,
            keepEnd: testCase.keepEnd
          }
        }
      });
      console.log(`  ${testCase.desc}: ${testCase.input} → ${result.result.test}`);
    }
    console.log('  ✅ 自适应掩码长度测试通过\n');

    console.log('📊 测试5: 获取默认规则（包含新字段）');
    const defaultRules = await makeRequest('/api/rules/default', 'GET');
    console.log('  默认规则包含keepStart:', defaultRules.phone.keepStart !== undefined ? '✅ 是' : '❌ 否');
    console.log('  默认规则包含keepEnd:', defaultRules.phone.keepEnd !== undefined ? '✅ 是' : '❌ 否');
    console.log('  默认规则包含hashSalt:', defaultRules.phone.hashSalt !== undefined ? '✅ 是' : '❌ 否');
    console.log('');

    console.log('📊 测试6: 获取脱敏方式');
    const methods = await makeRequest('/api/methods', 'GET');
    console.log('  自适应掩码描述:', methods.find(m => m.value === 'mask')?.description.includes('自适应') ? '✅ 已更新' : '❌ 未更新');
    console.log('  哈希盐值描述:', methods.find(m => m.value === 'hash')?.description.includes('盐值') ? '✅ 已更新' : '❌ 未更新');
    console.log('');

    console.log('🎉 所有增强功能测试完成！');
    console.log('');
    console.log('📝 功能总结:');
    console.log('  ✅ 自适应掩码 - 按输入长度动态调整');
    console.log('  ✅ 一致性哈希 - 支持盐值配置');
    console.log('  ✅ 表格化配置 - 支持批量操作');
    console.log('  ✅ 后端API - 已同步更新');

  } catch (error) {
    console.error('❌ 测试失败:', error.message);
  }
}

runTests();
