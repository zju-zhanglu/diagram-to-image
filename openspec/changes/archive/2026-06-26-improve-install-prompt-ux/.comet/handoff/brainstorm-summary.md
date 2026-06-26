# Brainstorm Summary

- Change: improve-install-prompt-ux
- Date: 2026-06-26

## 确认的技术方案

**方案 B：顶层检测 + 独立函数分发**

- 顶层 try/catch 加载 `@inquirer/prompts`，设置 `inquirerAvailable` 标志位
- 新函数 `promptForAgentsInquirer()` 用 `checkbox` 实现 agent 多选（默认全选，required）
- 新函数 `promptForScopeInquirer()` 用 `select` 实现 scope 单选（default: global）
- 原函数重命名为 `promptForAgentsLegacy()` / `promptForScopeLegacy()`（readline 文本输入）
- 包装函数 `promptForAgents()` / `promptForScope()` 按 `inquirerAvailable` 分发给 inquirer 或 legacy
- 新增依赖 `@inquirer/prompts: ^8.4.3`（与 Comet 一致）

## 关键取舍与风险

- 2 个 legacy 函数保留且导出，供测试覆盖 readline 路径
- 默认全选 agent（`checked: true`），与当前行为一致
- 风险：新依赖不可用时通过 try/catch fallback 完全消除影响

## 测试策略

- 现有 `npm test` 覆盖 legacy 路径（函数签名不变）
- 手动测试 TTY 环境 checkbox/select 交互
- 手动测试 CLI 参数跳过交互（`--agent`、`--scope`、`--all`）
- 手动测试非 TTY 静默安装

## Spec Patch

无
