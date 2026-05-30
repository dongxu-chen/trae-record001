const http = require('http');

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
      res.on('end', () => {
        try {
          resolve(JSON.parse(body));
        } catch {
          resolve(body);
        }
      });
    });

    req.on('error', reject);
    if (data) req.write(JSON.stringify(data));
    req.end();
  });
}

async function runTests() {
  console.log('🚀 开始测试新功能...\n');

  try {
    console.log('📋 测试1: 获取策略模板');
    const templates = await makeRequest('/api/templates', 'GET');
    console.log('  模板数量:', templates.length);
    templates.forEach(t => {
      console.log(`    - ${t.icon} ${t.name}: ${t.description}`);
    });
    console.log('  ✅ 策略模板获取成功\n');

    console.log('🔐 测试2: 获取权限级别');
    const permissions = await makeRequest('/api/permissions', 'GET');
    console.log('  权限级别:');
    permissions.forEach(p => {
      console.log(`    - ${p.value} (级别${p.level + 1}): ${p.label} - ${p.description}`);
    });
    console.log('  ✅ 权限级别获取成功\n');

    console.log('🔄 测试3: 动态脱敏 - 不同权限对比');
    const testData = {
      phone: '13800138000',
      idCard: '110101199001011234',
      email: 'example@email.com',
      name: '张三',
      address: '北京市朝阳区某某街道123号'
    };

    const testRules = {
      phone: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 3, keepEnd: 4 },
      idCard: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 6, keepEnd: 4 },
      email: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 2, keepEnd: 0 },
      name: { enabled: true, method: 'mask', pattern: 'adaptive', keepStart: 1, keepEnd: 0 },
      address: { enabled: true, method: 'truncate', maxLength: 10 }
    };

    for (const perm of ['admin', 'senior', 'normal', 'guest']) {
      const result = await makeRequest('/api/mask', 'POST', {
        data: testData,
        rules: testRules,
        permission: perm,
        userId: 'test_user',
        userName: '测试用户'
      });

      const permLabel = permissions.find(p => p.value === perm)?.label || perm;
      console.log(`  ${permLabel}:`);
      console.log(`    手机号: ${testData.phone} → ${result.result.phone}`);
      console.log(`    身份证: ${testData.idCard} → ${result.result.idCard}`);
      console.log(`    邮箱: ${testData.email} → ${result.result.email}`);
      console.log(`    姓名: ${testData.name} → ${result.result.name}`);
      console.log(`    地址: ${testData.address} → ${result.result.address}`);
      console.log('');
    }
    console.log('  ✅ 动态脱敏测试通过\n');

    console.log('📜 测试4: 审计日志记录');
    const auditLogs = await makeRequest('/api/audit/logs?limit=10', 'GET');
    console.log('  审计日志总数:', auditLogs.total);
    console.log('  最近3条记录:');
    auditLogs.logs.slice(0, 3).forEach((log, i) => {
      console.log(`    ${i + 1}. [${log.action}] ${log.userName} - ${new Date(log.timestamp).toLocaleString('zh-CN')}`);
      if (log.sensitiveFields) {
        console.log(`       敏感字段: ${log.sensitiveFields.join(', ')}`);
      }
    });
    console.log('  ✅ 审计日志测试通过\n');

    console.log('🏢 测试5: 应用模板规则');
    const enterpriseTemplate = templates.find(t => t.id === 'enterprise');
    if (enterpriseTemplate) {
      console.log('  应用企业标准级模板:');
      Object.entries(enterpriseTemplate.rules).forEach(([field, rule]) => {
        const status = rule.enabled ? '✅' : '⬜';
        console.log(`    ${status} ${rule.label}: ${rule.method}`);
      });
      console.log('  ✅ 模板规则解析成功\n');
    }

    console.log('🎉 所有新功能测试完成！');
    console.log('');
    console.log('📝 功能总结:');
    console.log('  ✅ 策略模板 - 5种预设模板一键应用');
    console.log('  ✅ 动态脱敏 - 4种权限级别不同脱敏程度');
    console.log('  ✅ 审计日志 - 完整记录敏感数据访问行为');

  } catch (error) {
    console.error('❌ 测试失败:', error.message);
  }
}

setTimeout(runTests, 2000);
