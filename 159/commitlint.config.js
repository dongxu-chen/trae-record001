/**
 * Git Commit Message 规范配置文件
 * 
 * Husky钩子执行顺序:
 * 1. pre-commit          - 提交前执行代码检查和未暂存文件提醒
 * 2. prepare-commit-msg  - 准备提交消息时触发
 * 3. commit-msg          - 校验提交消息格式（本工具处理）
 */

module.exports = {
  /**
   * 允许的提交类型枚举
   * 可以根据项目需求自定义添加或删除
   */
  types: [
    'feat',      // 新功能
    'fix',       // 修复bug
    'docs',      // 文档更新
    'style',     // 代码格式调整（不影响代码运行）
    'refactor',  // 代码重构（既不是新增功能，也不是修复bug）
    'perf',      // 性能优化
    'test',      // 测试相关
    'build',     // 构建系统、外部依赖变更
    'ci',        // CI/CD 配置修改
    'chore',     // 其他修改（比如构建流程或辅助工具）
    'revert'     // 回滚提交
  ],

  /**
   * 各类型对应的emoji
   * 用于交互式提交和CHANGELOG生成
   */
  typeEmojis: {
    feat: '✨',
    fix: '🐛',
    docs: '📝',
    style: '💄',
    refactor: '♻️',
    perf: '⚡',
    test: '✅',
    build: '📦',
    ci: '🤖',
    chore: '🔧',
    revert: '⏪'
  },

  /**
   * 提交消息长度限制
   */
  maxLength: 100,
  minLength: 10,

  /**
   * 格式校验正则表达式
   * 格式: <type>(<scope>): <subject>
   */
  pattern: /^(\w+)(\(.+\))?: .{1,}$/,

  /**
   * 各类型的中文描述说明
   */
  typeDescriptions: {
    feat: '新功能',
    fix: '修复bug',
    docs: '文档更新',
    style: '代码格式调整',
    refactor: '代码重构',
    perf: '性能优化',
    test: '测试相关',
    build: '构建系统',
    ci: '持续集成',
    chore: '其他修改',
    revert: '回滚提交'
  }
};
