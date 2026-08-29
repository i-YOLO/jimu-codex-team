<p align="right">
  <a href="./README.md">English</a> · <strong>简体中文</strong>
</p>

# Jimu Codex Team

`jimu-codex-team` 是一个需要显式调用的 Codex Skill，用最小必要的自定义 Agent 小队协调有一定规模的开发、调研、分析、文档、数据和内容任务。

主线程保留尚未解决的产品、编辑、架构、安全、权限和验收决策；三个工作 Agent 分别负责证据探索、边界执行和全新上下文复审。可选的 `default` 派发哨兵会在漏传 `agent_type` 时拒绝工作，要求主线程重新选择正确角色。

它是一套调度规则，不是固定流水线，也不替代 Codex 内置的多 Agent 运行时。

## 角色

| Agent 类型 | 模型 | 推理强度 | Profile 默认权限 | 职责 |
|---|---|---:|---|---|
| `Explorer` | `gpt-5.6-luna` | Medium | 只读 | 从网页、文档、数据、代码、日志、API、Schema 和配置中收集证据。 |
| `Executor` | `gpt-5.6-luna` | High | 工作区可写 | 在决策、边界和所有权明确后完成可独立验收的执行任务。 |
| `Reviewer` | `gpt-5.6-terra` | Medium | 只读 | 使用全新上下文检查一个明确的未解决风险，不修改产物。 |
| `default` | `gpt-5.6-terra` | Low | 只读 | 拦截漏传或误传角色的派发。 |

父任务的实时权限可能覆盖 Profile 的沙箱默认值。只读角色既是配置边界，也是行为边界；真正需要隔离时，应从运行记录确认有效权限。

## 适合做什么

- 并行梳理大型代码库的不同模块；
- 同时调查代码、日志、配置与测试；
- 将互不重叠的模块交给不同 Executor 实现；
- 从代码质量、性能、复用或回归风险角度复审稳定改动；
- 分头查找多组一手资料；
- 审计文档、数据、报告或知识库；
- 按明确所有权和验收标准协调内容、媒体或其他产物制作。

简单查询、一行修改、紧耦合单文件工作、尚未确定的产品决策，以及多人共享同一个浏览器或账号的交互工作，应留在主线程。

每个子 Agent 都会独立消耗 Token 和工具时间。只有并行、上下文隔离、低成本边界执行或独立判断的收益大于派发和验收成本时，才值得组队。

## 调度契约

所有工作派发必须显式选择：

```text
agent_type = Explorer | Executor | Reviewer
```

`task_name` 只是标签，不能选择 Profile。

每个派发包必须包含：

```text
Outcome:
Benefit:
Sources:
Scope:
Checks:
Stop when:
Return:
```

Reviewer 还必须包含 `Unresolved risk`、`Evidence`、`Checks already passed` 和 `Do not repeat`。

Skill 默认给子 Agent 全新上下文；同一可变目标只允许一个写入者；子 Agent 不再生成后代；主线程检查真实来源、文件、Diff 和验证结果后才接受工作。没有可复用结果时，瞬时失败最多重试一次。

## 安装

### 1．安装 Skill

直接安装：

```bash
npx skills add i-YOLO/jimu-codex-team
```

这一步只安装 Skill 指令。自定义 Agent Profile 属于另一套 Codex 配置，需要单独安装。

推荐保留一个可维护的源码目录：

```bash
git clone https://github.com/i-YOLO/jimu-codex-team.git ~/.local/share/jimu-codex-team
npx skills add ~/.local/share/jimu-codex-team
```

### 2．安装三个工作 Profile

```bash
mkdir -p ~/.codex/agents
ln -s ~/.local/share/jimu-codex-team/assets/agent-profiles/Explorer.toml ~/.codex/agents/Explorer.toml
ln -s ~/.local/share/jimu-codex-team/assets/agent-profiles/Executor.toml ~/.codex/agents/Executor.toml
ln -s ~/.local/share/jimu-codex-team/assets/agent-profiles/Reviewer.toml ~/.codex/agents/Reviewer.toml
```

在 `~/.codex/config.toml` 中新增或合并：

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 3
interrupt_message = true
```

重启 Codex 或新建任务。确认模型可见的 `spawn_agent` Schema 能通过 `agent_type` 选择 `Explorer`、`Executor`、`Reviewer`，然后分别执行一次无副作用探针。

### 3．启用可选派发哨兵

只有三个工作角色都通过运行时验证后，才启用：

```bash
ln -s ~/.local/share/jimu-codex-team/assets/agent-profiles/default.toml ~/.codex/agents/default.toml
```

再次重启 Codex。受控漏参派发必须返回：

```text
DISPATCH BLOCKED: the delegated task was not executed because agent_type was omitted or set to default. Respawn with agent_type=Explorer, Executor, or Reviewer.
```

个人级 `default` 会覆盖 Codex 内置的默认回退 Agent，影响所有遗漏角色的个人 Codex 派发。如果运行时没有 `agent_type`，不要启用哨兵。

只关闭哨兵、不移除三个工作角色：

```bash
mkdir -p ~/.codex/agents-disabled
mv ~/.codex/agents/default.toml ~/.codex/agents-disabled/default.toml
```

更完整的验证与定制边界见[Agent Profile 安装说明](./references/agent-setup.md)。

## 使用

```text
$jimu-codex-team 调查这个项目为什么构建失败，分别检查代码、依赖和配置，确认原因后修复并验证。
```

```text
$jimu-codex-team 审查这个分支，分别检查代码质量、性能、复用和测试缺口，最后输出一份按严重度排序的报告。
```

```text
$jimu-codex-team 检查这个知识库的重复、断链、过期索引和敏感内容，保持写入范围互不重叠，并验证每项修复。
```

你不需要自己逐个选择角色。主线程会选择最小够用的小队；面对简单任务时，它也可以正确地不启动任何子 Agent。

## 本地运行报告

诊断脚本只读取本地保留的 Codex trace，输出角色、模型、推理强度、有效沙箱、状态、耗时和 Token，不输出提示词或工具内容，也不联网：

```bash
python3 scripts/inspect-team-runs.py --task-id current --by-session
python3 scripts/inspect-team-runs.py --task-id current --by-session --json
```

本地 trace 可能不包含临时或不可用会话；出现完成标记不代表产物一定正确。

## 测试

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

测试覆盖 Profile 解析与角色边界、显式调用策略、派发契约、任务归属、运行时元数据、终止状态和 Token 计算。

## 仓库结构

```text
jimu-codex-team/
├── SKILL.md
├── agents/openai.yaml
├── assets/agent-profiles/
├── references/
├── scripts/inspect-team-runs.py
└── tests/
```

## 许可证

[MIT](./LICENSE)
