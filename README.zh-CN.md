<p align="right">
  <a href="./README.md">English</a> · <strong>简体中文</strong>
</p>

# Jimu Codex Team

`jimu-codex-team` 是一个需要显式调用的 Codex Skill，用最小必要的自定义 Agent 小队协调有一定规模的开发、调研、分析、文档、数据和内容任务。

主线程保留尚未解决的产品、编辑、架构、安全、权限和验收决策；五个工作角色分别负责证据探索、边界执行、前端实现、快速局部前端实现和全新上下文复审。可选的 `default` 派发哨兵会在漏传 `agent_type` 时拒绝工作，要求主线程重新选择正确角色。

它是一套调度规则，不是固定流水线，也不替代 Codex 内置的多 Agent 运行时。

## 角色

| Agent 类型 | 模型 | 推理强度 | Profile 默认权限 | 职责 |
|---|---|---:|---|---|
| `Explorer` | `gpt-5.6-luna` | Medium | 只读 | 从网页、文档、数据、代码、日志、API、Schema 和配置中收集证据。 |
| `Executor` | `gpt-5.6-luna` | High | 工作区可写 | 在决策、边界和所有权明确后完成可独立验收的执行任务。 |
| `Frontend` | `gemini-3.8-flash` | High | 工作区可写 | 前端工作的通常且几乎总是默认的 UI 角色，负责新页面、跨组件、响应式或多状态、客户端集成以及存在视觉歧义的工作。 |
| `FrontendFast` | `gemini-3.7-flash` | High | 工作区可写 | 仅作为例外的补充角色，用于极局部、低风险、契约完全固定、有确定性检查且能带来实质速度或成本收益的 UI 工作。 |
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
agent_type = Explorer | Executor | Frontend | FrontendFast | Reviewer
```

模型由显式的 `agent_type` 及其 Profile 选择；不能从 `task_name` 推断，也不能假定每次派发都能单独覆盖模型。`task_name` 只是标签，不能选择 Profile。

前端工作默认且尽可能使用 `Frontend`；无法确定时选择 `Frontend`。`FrontendFast` 是例外的补充选项，不是并列默认、常规替代或失败兜底：只有在设计系统和 API 契约完全固定、修改极局部且低风险、目标文件明确、有确定性检查并能带来实质速度或成本收益时才使用。它不得并发接管其他角色已经拥有的切片。完整的前端切片可以包含页面、组件、样式、交互、客户端状态、路由、固定 API 的消费、资源和聚焦的前端测试，但不包括后端代码、数据库 Schema 或迁移、身份认证或授权、API 契约或端点载荷、生成的契约以及服务端配置。如果需要修改契约，应停止并把具体不匹配返回主线程。

当渲染行为或布局属于范围时，标准视觉证据应覆盖项目定义的桌面和移动端视口，以及范围内所有相关的默认、加载中、空态、错误和交互状态。记录视口、路由、状态和交互；最终视觉与 UX 验收由主线程保留。

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

### 2．安装普通文件版工作 Profile

需要 macOS 或 Linux 上的 Python 3.11+，安装工具只使用标准库。模板保持为唯一真源，活动 Profile 使用普通 TOML 副本。Skill 目录可以保留软链接，但不要把活动 Profile 做成软链接。

```bash
python3 ~/.local/share/jimu-codex-team/scripts/install-agent-profiles.py
python3 ~/.local/share/jimu-codex-team/scripts/install-agent-profiles.py --check
```

默认只安装五个工作角色，内容一致时不改动。自定义文件和未知链接默认报告冲突，检查后显式使用 `--replace` 才会替换。目录、设备、FIFO、Socket，以及软链接形式的 Agent 目标目录都会被拒绝。

仅在尚未配置时，于 `~/.codex/config.toml` 中新增或合并：

```toml
[agents]
enabled = true
max_concurrent_threads_per_session = 3
interrupt_message = true
```

项目级副本可使用 `--agents-dir <项目>/.codex/agents`。

#### 迁移旧版软链接安装

先检查六份 Profile：

```bash
python3 ~/.local/share/jimu-codex-team/scripts/install-agent-profiles.py --check --roles Explorer Executor Frontend FrontendFast Reviewer default
```

将哨兵本身移到唯一备份目录，然后迁移五个工作角色：

```bash
mkdir -p ~/.codex/agents-disabled
if [ -e ~/.codex/agents/default.toml ] || [ -L ~/.codex/agents/default.toml ]; then
  guard_backup=$(mktemp -d ~/.codex/agents-disabled/jimu-guard.XXXXXX)
  mv ~/.codex/agents/default.toml "$guard_backup/default.toml"
fi
python3 ~/.local/share/jimu-codex-team/scripts/install-agent-profiles.py --migrate-links
python3 ~/.local/share/jimu-codex-team/scripts/install-agent-profiles.py --check
```

`--migrate-links` 只接受指向当前源码目录对应模板的链接。来自其他目录的旧链接必须先检查，再明确授权 `--replace`。不要直接向现有软链接复制，否则可能改写模板，却没有消除软链接。

已在 Desktop `0.151.0-alpha.7.1` 复现：Profile 软链接导致 `os error 62`，对外只显示 `agent type is currently not available`，但此前 CLI `0.145.0` 探针可以通过。这是已观察到的兼容问题，不代表所有 Codex 版本都拒绝软链接。

### 3．先验证 Desktop，再启用哨兵

在原本受影响的 Desktop 任务中验证五个工作角色，记录实际运行的二进制路径和版本；不能用 PATH 中另一版本的 `codex` 测试替代。需要重新加载时再协调重启或恢复任务，不中断其他工作。

从真实子 Agent trace 核对角色、模型、推理强度、完成状态、工具调用和有效权限；仅看到角色名，或子 Agent 自报角色，都不足以通过验收。

五个角色全部通过后：

```bash
python3 ~/.local/share/jimu-codex-team/scripts/install-agent-profiles.py --roles default
python3 ~/.local/share/jimu-codex-team/scripts/install-agent-profiles.py --check --roles Explorer Executor Frontend FrontendFast Reviewer default
```

执行一次明确授权、子 Agent 不调用工具的漏参探针，必须返回：

```text
DISPATCH BLOCKED: the delegated task was not executed because agent_type was omitted or set to default. Respawn with agent_type=Explorer, Executor, Frontend, FrontendFast, or Reviewer.
```

随后再确认显式 `Explorer` 可以工作。受控安装自检是正常派发必须指定角色这一规则的唯一例外。

个人级哨兵会覆盖所有个人任务的默认回退。若派发仍失败，应保持禁用。单独关闭时，按上方步骤将它移入唯一备份目录；检查通过后使用安装工具恢复，不重新装回已知不兼容的旧链接。

### 4．后续更新与恢复

更新模板不会自动改变运行副本。先运行 `--check`、检查差异，再按需使用 `--replace` 显式同步。原件备份到活动目录之外的 `agents-backups/jimu-codex-team/` 时间戳目录，软链接按链接本身保留。写入使用暂存文件、绑定目录的操作和失败回滚，不改动其他 Profile。

安装工具不修改 `config.toml`、不启动 Agent、不联网。文件安装与运行时验收是两件事。完整冲突处理和验证方法见[Agent Profile 安装说明](./references/agent-setup.md)。

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

测试覆盖真实文件安装、软链接迁移、O_NOFOLLOW、幂等、冲突保护、备份回滚与目录替换竞争，以及角色契约、显式调用、trace 归属和 Token 计算。

## 仓库结构

```text
jimu-codex-team/
├── SKILL.md
├── agents/openai.yaml
├── assets/agent-profiles/
├── references/
├── scripts/                  # Profile installer and trace report
└── tests/
```

## 许可证

[MIT](./LICENSE)
