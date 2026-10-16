# macOS：Chrome + 进程出站保护

标准部署还要求按 [TUN 与时区流程](tun-timezone.md) 开启规则 TUN，并将系统时区设为 `Asia/Singapore`。执行前备份、说明系统级影响和核对授权；开启 TUN 不替代 LuLu 或网站保护。

## 备份与前置检查

记录 Chrome 有效策略、已装描述文件标识、代理监听 PID、实际选择的唯一节点。仅看相关字段，不读取认证和完整订阅。已有 MDM/企业策略冲突时先停止应用。

LuLu 使用官方发行版；首次系统扩展、网络过滤授权由用户确认。检查活动 profile、过滤启用状态、allow list、自动允许规则和实际匹配日志。关闭 LuLu 或切换到另一 profile 会使原保护失效。

## Chrome 网站层

运行生成器，审阅 PAC 与描述文件。用系统设置安装 `chrome.mobileconfig`：通用 → 设备管理；名称为 Claude Isolation - Chrome。需要用户本机密码/Touch ID 时交给用户。此文件是可移除的用户级 Chrome 策略，不包含证书、账号或设备管理注册。

核对 `chrome://policy` 中 ProxySettings、WebRtcIPHandlingUrl 强制级、状态 OK。代理不可用时，保护域名只能失败，不得返回 DIRECT。普通网站行为以生成配置的 `unprotected` 为准。描述文件安装成功不等于代理出口验证成功。

## 官方桌面端与 CLI

核对实际 bundle/EXE 路径、`codesign -dv --verbose=4` 的标识与签名、子进程路径；不要硬编码某位用户的签名键或家目录。正常启动客户端并观察真实连接，不向官方应用注入被拒绝的调试/代理参数。

在官方 LuLu GUI 建立仅目标客户端的规则：

- 主应用身份的外部出站拒绝，允许所需 loopback 代理连接。
- 应用 bundle 内 helper/子进程的出站同样限制。
- 单独启动的 Claude Code、MCP、虚拟机进程不自动归属于桌面 bundle；另行处理，不能封锁系统共享 Node/Python。

目录 `/Applications/Claude.app/*` 不涵盖 bundle 根身份 `/Applications/Claude.app`。需要同时核对根身份和目录/实际 helper 的规则。已有 app-specific 精确 allow、基线自动 allow 或 allow list 可能覆盖预期限制；检查冲突，不能只追加一条 wildcard block 后宣布完成。

LuLu 4.5.1 的导出/导入是官方 JSON；**内部 rules.plist 是归档，不是可导入 JSON**。不要直接改内部归档、与 daemon 争写或绕过签名校验/XPC。自动化导入前，必须读取当前版本官方 schema，使用全量导出作备份，保留无关项，审核目标相关旧规则的替换；schema 不明就用 GUI，不猜字段。全量导入会替换规则集；仅用户规则导入仍可能留下其他类型的冲突规则。

全局允许 DNS、localhost、installed apps、被动模式及 allow list 会影响结果。若 loopback 全局允许，报告为“允许本机转发”，不能声称只有一个端口可用。修改全局项可能影响无关应用，应先说明并获得授权。LuLu 官方也说明有些流量不经过其 Network Extension；必须保留这个覆盖边界。

CLI 的 HTTPS_PROXY/HTTP_PROXY 仅放进专用启动会话，保留第三方 API 会话；用 `lsof -nP -i`、限定 app 的 LuLu 日志确认实际联网。浏览器打开的 OAuth 登录页面需要独立的网站策略，CLI 变量不覆盖浏览器。

## 回滚

移除本 Skill 的描述文件，恢复先前相关 Chrome 策略；不删除 MDM 或无关 profile。LuLu 在同一活动 profile 中用改动前全量导出恢复，或逐条恢复目标规则。全量导入可能覆盖期间新增的其他规则，恢复前先导出当前状态并审核差异。恢复专用启动会话/代理的原配置后再观察有效状态。

来源：[Apple 描述文件](https://support.apple.com/guide/mac-help/mh35561/mac)、[Chrome Mac 管理](https://www.chromium.org/administrators/mac-quick-start/)、[LuLu 官方使用与限制](https://objective-see.org/products/lulu.html)、[LuLu 4.5.1 规则实现](https://github.com/objective-see/LuLu/blob/v4.5.1/LuLu/Extension/Rules.m)。实现来源用于核对版本，不把第三方代码复制进发布包。
