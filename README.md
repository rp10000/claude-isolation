# Claude Isolation

为官方 Claude 配置固定代理和断线保护的可分享 Skill。支持 Windows、macOS；默认只处理 Claude，用户要求时可扩展 OpenAI/Gemini 和爱快补充规则。保留独立第三方 API／CC Switch 配置。

**目标：指定线路不可用时，让受保护的客户端请求失败，避免自动直连或切换出口。** 这是联网隐私控制，不承诺防封号、隐藏身份或获得服务的地区使用资格。

## 安装与使用

把 ZIP 中的 `claude-isolation` 文件夹放入 AI 工具的 Skill 目录：

- Codex：`~/.codex/skills/claude-isolation/`（设置了 CODEX_HOME 时用其 skills 子目录）。
- Claude Code：`~/.claude/skills/claude-isolation/`，或项目内 `.claude/skills/claude-isolation/`。
- 其他工具：使用支持 `SKILL.md` 的导入功能；不支持执行本机命令的工具只能辅助生成方案。

重新加载 Skills／开启新会话，使工具发现它。Codex 中可以这样请求：

> 使用 $claude-isolation。先检查我的系统、代理端口、实际节点和 Claude 各客户端联网路径。我要官方网页登录、桌面端和 Claude Code 固定走我指定的节点；节点失效、代理退出都不允许直连。第三方 API 配置不动，国内软件保持原有直连。先说明覆盖范围和回滚，再实施并验证。

Claude Code 可使用 `/claude-isolation`，或直接点名这个 Skill。是否能自动执行取决于工具权限和平台。系统权限、网络过滤扩展、描述文件安装等仍需使用者确认；不会绕过确认。

## 包内能力

| 范围 | 处理方式 | 不能省略的检查 |
|---|---|---|
| Chrome 官方网站 | 精确/子域 PAC，无直连回退；强制策略；按站点限制 WebRTC | 有效策略、版本支持、真实浏览器故障测试 |
| Windows 官方桌面端／独立 CLI | 专用代理设置 + 指定 EXE 出站保护脚本 | 防火墙有效、子进程、MSIX/升级路径、实际连接 |
| macOS 桌面端／CLI | 专用代理 + LuLu 官方规则流程 | 扩展授权、根身份与 helper、旧 allow 冲突 |
| v2rayN 等代理客户端 | 审核正在使用的核心配置，把目标锁到唯一出站 | 不自动换组、不回退直连；中转的下一跳 |
| CC Switch 第三方 API | 保持原设置；单独验证其路径 | 与原生模式共用进程/域名时无法按登录方式分类 |
| 爱快（可选） | 源设备限定的 V4 域名规则计划与应用/撤销流程 | 固件适配、源 IP、非完整 kill switch |

Windows 与 Mac 都有操作参考。生成器提供配置材料，Windows 脚本提供按程序应用和回滚；**没有自动修改所有平台的一键万能安装器**。共享 Node、WSL、Cowork VM、移动端与其他浏览器需要另行核对，未覆盖时会保留待办，不伪报通过。

如果拒绝系统级出站过滤，可以设置浏览器层强制代理，但不能据此保证所有官方桌面端和子进程断线隔绝。TUN、系统代理、HTTPS_PROXY 三者叠加也不能代替故障验证。

## 离线生成与测试

Python 3.10+，无第三方 Python 依赖。实际执行 PAC 用例还需要 Node.js；Windows 测试使用系统 PowerShell。没有 Node 时测试会标 skip，不能当完整通过。

```sh
python scripts/generate.py --config assets/example-config.json --out ./generated-example
python -B -m unittest discover -s tests -v
# 发布 ZIP，输出目录必须存在，ZIP 和校验文件必须尚不存在：
python scripts/make_release.py --out /path/outside-skill/claude-isolation-v1.0.0.zip
```

`generated-example` 必须不存在。例子的 loopback 端口只是示例，真实配置要先发现端口。生成结果没有生效；代理执行流程见 SKILL.md 及 references。不要把自己的生成结果放进公开仓库。

## 验证状态与边界

v1.0.0 的公开生成器经过离线测试：域名边界、PAC 实际执行、策略/描述文件一致性、坏参数拒绝、源范围与防覆盖。Windows 出站脚本经过语法和模拟系统接口测试，**未在每个 Windows 版本、MSIX、WSL 或第三方安全软件组合实机验收**。macOS 与爱快流程来自实机部署经验，但新使用者仍须在自己的机器完成验证。

每次部署独立报告“生成、应用、有效策略、真实路径、节点故障、代理退出”状态。策略存在、一次 HTTP 请求成功、IP 检测网页显示某国家，都不能代替各客户端验收。浏览器 PAC 不覆盖系统 DNS 和所有 UDP；禁用非代理 WebRTC UDP 可能让候选为空，不保证出现某个国家的 UDP 地址。

## 分享与维护

可以把整个源目录提交到自己的 Git 仓库或分发 ZIP。打包脚本只收录明确允许的源文件，输出 SHA256 校验；它不扫描或收集本机配置。提交仓库前仍应检查脱敏，不能只依赖 .gitignore。不要提交真实配置、账号、cookie、密钥、订阅链接、客户规则导出、日志或回滚 receipt。提交问题时附脱敏的 OS/应用版本、覆盖对象和哪一步未通过即可。第三方软件安装器不包含在包里，从官方来源获取并核对版本。

原创代码与文档采用 MIT License；包内 Public Suffix List 保留 MPL-2.0 许可及原始声明，见 THIRD-PARTY-NOTICES.md。独立社区项目，与 Anthropic、OpenAI、v2rayN、Objective-See、爱快无隶属或背书关系。规则是可维护的起点，不是对未来域名和全部网络协议的完整清单。
