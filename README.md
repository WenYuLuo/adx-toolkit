# ADX Toolkit

Agent DX 的四个 Codex skills，覆盖开发、独立进程部署、三节点 VM 和 Buildkite 验收。每个 skill 可以单独安装，不依赖其他 toolkit。

| Skill | 使用场景 |
|---|---|
| [adx-dev](adx-dev/SKILL.md) | 源码修改、TDD、Cargo／Go／Python 构建、缓存、发布包与提交 |
| [adx-standalone](adx-standalone/SKILL.md) | 单机进程部署、外部 sandboxd、本地 Docker 两节点公共 SDK E2E |
| [adx-3vm](adx-3vm/SKILL.md) | 三台 Linux VM：控制节点＋两台工作节点，健康检查、部署、网络与验收 |
| [adx-buildkit](adx-buildkit/SKILL.md) | ADX **Buildkite** 三阶段流水线、触发、监控、日志及产物 |

`adx-buildkit` 是约定的 skill 名称，负责 Buildkite CI；Docker BuildKit 只是镜像构建环节涉及的工具。仓库包含四个 skill，没有额外隐式路由 skill。

## 安装

```sh
git clone git@github.com:WenYuLuo/adx-toolkit.git
cd adx-toolkit
python3 scripts/install.py --destination "${CODEX_HOME:-$HOME/.codex}/skills"
```

安装器为四个目录创建软链接，已存在的其他内容会报冲突而不覆盖。保持 checkout 路径稳定，后续 `git pull` 更新内容；新会话中确认技能可用。可通过重复 `--skill` 只安装指定项：

```sh
python3 scripts/install.py --destination "${CODEX_HOME:-$HOME/.codex}/skills" \
  --skill adx-dev --skill adx-buildkit
```

## 调用示例

```text
$adx-dev 基于当前 ADX 分支，用测试驱动补齐节点生命周期功能。
$adx-standalone 使用这份 release 在本机运行真实 SDK 创建、执行和删除验收。
$adx-3vm 使用我指定的三个 VM 部署同一份 ADX 包并验证两个工作节点。
$adx-buildkit 触发当前 ADX 提交的 Buildkite K8s 验收，检查每个用例和清理结果。
```

产品源码默认是 `git@gitcode.com:robbluo/agent-dx.git`，工作路径由调用者指定。每次执行读取目标提交的 `AGENTS.md`、Makefile、配置与驱动；skill 不维护第二套产品构建／部署实现。

## 能力与证据

当前产品实现指针为 ADX 提交 `1a16d794428ef436f6d0da4a793f20e0d82a672c`，记录于 [sources.json](sources.json)。Buildkite #14 验收对应此前的 `0dde79ad57583e998389101a763e4d2d825be63e`；本次多 worktree Cargo 缓存改动仅完成本地合同测试，不能继承该集成验收。版本、分支、镜像、集群与凭证在执行时重新确认。

四个 skill 是操作工作流；创建本仓库不等于运行了一轮新的 ADX 集成测试。尤其 `adx-3vm` 是进程部署与验收契约，尚无 ADX 专用的自动三 VM 驱动或三 VM 通过记录。不得用本地双容器、K8s 两 Pod 或 SDK Socket 测试替代三 VM 证据。

Buildkite helper 使用用户管理的 token 文件或 `BUILDKITE_API_TOKEN` 环境变量。凭证、目标主机清单、kubeconfig、SWR 配置和本次运行输出均保存在仓库外；仓库只含配置结构与示例。

## 校验与维护

```sh
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
```

更新 skill 时同步代码指针、命令与验证边界。新增执行脚本需验证错误处理、重复操作与凭证输出；外部动作是否被授权仍由本次用户请求决定。
