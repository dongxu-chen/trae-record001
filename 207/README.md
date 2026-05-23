# 代码片段管理工具

一个基于 Vue3 + Vuex + Monaco Editor 的在线代码片段管理工具。

## 功能特性

- ✅ 创建、编辑、删除代码片段
- ✅ 支持 15 种编程语言语法高亮
- ✅ 标签云展示和多选标签筛选
- ✅ 搜索筛选功能（标题、代码、标签）
- ✅ 暗色/亮色主题切换
- ✅ 自动保存到 localStorage
- ✅ 导出为 JSON 文件
- ✅ 键盘快捷键支持
- ✅ 编辑器加载状态提示
- ✅ 修复 Monaco Editor CDN/加载配置

## 支持的语言

JavaScript、TypeScript、Python、Java、C#、C++、Go、Rust、HTML、CSS、JSON、SQL、Bash、Ruby、PHP

## 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl + N` | 新建代码片段 |
| `Ctrl + S` | 保存当前片段 |

## 安装与运行

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 项目结构

```
src/
├── components/
│   ├── MonacoEditor.vue    # Monaco Editor 封装组件（含加载状态）
│   ├── SnippetList.vue     # 代码片段列表组件
│   ├── SnippetEditor.vue   # 代码编辑器组件
│   └── SearchFilter.vue    # 搜索和标签云筛选组件
├── constants/
│   └── languages.js        # 支持的语言配置
├── store/
│   └── index.js            # Vuex 状态管理（多选标签）
├── App.vue                 # 主应用组件（含快捷键）
├── main.js                 # 应用入口
└── style.css               # 全局样式（Monaco主题适配）
```

## 使用说明

1. **创建片段**: 点击左侧"新建"按钮或按 `Ctrl + N`
2. **编辑代码**: 在右侧编辑器中编写代码，支持实时语法高亮
3. **添加标签**: 在标签输入框中输入标签名称，按回车添加
4. **标签筛选**: 点击标签云中的标签进行多选筛选
5. **搜索筛选**: 使用顶部搜索框按标题、代码或标签搜索
6. **切换主题**: 点击右上角按钮切换暗色/亮色主题
7. **保存片段**: 自动保存或按 `Ctrl + S` 手动保存
8. **导出数据**: 点击"导出JSON"按钮将所有片段导出为文件
