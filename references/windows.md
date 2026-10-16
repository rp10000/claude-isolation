# Windows：独立实施路径

适用 Windows 10/11、PowerShell 5.1+。Windows 原生安装、MSIX、WSL、虚拟机是不同网络边界；不要把 Windows 进程规则套到 WSL 中的 Linux 进程。本发布包没有在所有这些组合上实机验收。

标准部署还要求按 [TUN 与时区流程](tun-timezone.md) 开启规则 TUN，并将系统时区设为 `Singapore Standard Time`。执行前备份、说明系统级影响和核对授权；开启 TUN 不替代下文出站保护。

## 1. 只读盘点和备份

先查目标进程的 ExecutablePath、父子关系、签名；`Get-AuthenticodeSignature` 核对签名状态及发行者。确定 Claude 是独立 EXE、MSIX 还是由共享 Node 启动。查看代理端口所属 PID、v2rayN 当前 core 和实际路由配置。不要输出整份订阅/数据库。

记录 `Get-NetFirewallProfile -PolicyStore ActiveStore` 和 MpsSvc/BFE 状态。防火墙关闭时，说明启用的影响，等使用者授权；本脚本**不会启用**它。入站远程服务和远程管理端口先核对，不做全局重置。

Chrome 备份 `chrome://policy` 的有效值和来源，以及 HKCU/HKLM 下相关键的原值、类型、是否存在。仅备份/修改 `ProxySettings`、`WebRtcIPHandlingUrl`，不要导出并公开整个注册表。若旧单独代理策略、扩展或云策略冲突，先分析优先级。

## 2. 网站：Chrome 强制策略

生成器输出的 `chrome-policy.json` 包含两个复杂策略。在支持本机策略的环境中，用当前官方 ADMX/GPO 或注册表方式部署到 `Software\Policies\Google\Chrome`（非 Recommended）。复杂值用相应 JSON 的 REG_SZ，不能把整个文件写成一个策略值。

由代理在确认无冲突并备份后执行**精确值写入**。示意：

```powershell
$policy = Get-Content -LiteralPath '<output>\chrome-policy.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$key = 'HKCU:\Software\Policies\Google\Chrome'
# 此处必须已经完成备份、冲突审核和应用授权。
New-Item -Path $key -Force | Out-Null
foreach ($name in @('ProxySettings', 'WebRtcIPHandlingUrl')) {
    $json = ConvertTo-Json -InputObject $policy.$name -Depth 15 -Compress
    New-ItemProperty -LiteralPath $key -Name $name -Value $json -PropertyType String -Force | Out-Null
}
```

Chrome 对未受管理设备的部分策略有限制，官方资料对直接注册表部署也有适用条件。**以本机 `chrome://policy` 为准**：两个策略存在、强制级、状态 OK、值和期望一致。若忽略或不支持，停止报告“网站已保护”；用受支持管理方式，或用户同意的独立专用浏览器加进程级隔离。不要为追求生效伪造设备管理、安装未知扩展或接管日常浏览器。

该策略管理这个 Chrome 安装/用户下的网站流量，不会控制任意 Electron WebView、其他浏览器或扩展独立网络栈。WebRTC 禁止非代理 UDP 不等于一定产生美国 UDP 地址；无候选也是可能结果。

## 3. 官方桌面端、CLI：代理 + 出站过滤

先观察实际联网，确认客户端确实连到本地 HTTP/mixed 端口。桌面端是否读系统代理/环境变量随版本变化，不能仅凭变量存在就判断。不要依赖可能被应用拒绝的启动参数，不改应用签名。

Claude Code 仅在**专用启动会话**设置环境变量：

```powershell
$env:HTTPS_PROXY = 'http://127.0.0.1:<verified-port>'
$env:HTTP_PROXY = $env:HTTPS_PROXY
$env:NO_PROXY = 'localhost,127.0.0.1,::1'
# 在该会话启动已核实的官方独立 claude.exe；退出会话即撤销这些变量。
```

不要写全局用户环境变量或覆盖 shell 配置，避免 CC Switch 第三方 API 会话被连带改变。先检查大小写变体、ALL_PROXY 和客户端专用配置是否冲突；同一进程中切模式无法靠防火墙区分。环境变量本身不构成断线保护。Desktop 托管与后台 supervisor 的变量来源例外见 proxy-clients.md；此示例只针对专用前台会话。

专用原生 EXE 可以使用 `scripts/windows-guard.ps1`：

```powershell
# Plan 无写入；每个 helper EXE 需提供完整、实际路径。
.\scripts\windows-guard.ps1 -Mode Plan -Program 'C:\Apps\Claude\claude.exe'
# 用户授权后，在管理员 PowerShell 执行；parent 目录预先存在。
.\scripts\windows-guard.ps1 -Mode Apply -Program 'C:\Apps\Claude\claude.exe' -Receipt 'C:\Private\claude-guard.json'
# 回滚，只移除该 receipt 对应的规则。
.\scripts\windows-guard.ps1 -Mode Rollback -Receipt 'C:\Private\claude-guard.json'
```

脚本阻断指定 EXE 到所有非 loopback 的 IPv4/IPv6 地址；整个 127/8 与 ::1 不在这些阻断规则中，既有策略仍可能拒绝它们。**没有限制为唯一一个本地代理端口**，同机其他转发程序仍是信任边界。若要精确端口隔离，用有相应能力的出站过滤方案并另行验证。它不修改入站，不启用防火墙，不阻断共享 Node、通用浏览器或代理核心。

需要补足的情形：

- MSIX/Store、版本化更新路径：检查实际进程与包身份、有效规则和升级后的路径；不能把旧版本路径的成功沿用到新版本。
- Node/npm CLI：不要封锁整个 `node.exe`；优先专用官方二进制，或独立隔离运行环境。没有合适能力时明确待办。
- WSL、Cowork VM、MCP 子进程：分别盘点；当前 EXE 规则不自动覆盖这些边界。
- 第三方 WFP/安全软件、TUN 接管、受管理策略：可能改变归因或有效规则，必须做故障测试。不能通过关闭其他安全产品来消除冲突。
- 已建立的连接不能用静态规则存在证明已被切断；授权后重建目标连接，记录实际行为。

## 4. 回滚和复核

用 receipt 回滚本 Skill 新建的出站规则。Chrome 每个值按备份恢复原类型/原值；原来不存在的值仅删除本次新增值。不删除整个 Chrome 键，不重置全部防火墙。恢复后重载策略并核对来源；企业管理策略需由相应管理端处理。脚本/注册表修改与用户实际登录验收是不同阶段。

来源（实施时查当前版本）：[Chrome Windows 策略](https://support.google.com/chrome/a/answer/9131254?hl=en)、[复杂策略编码](https://www.chromium.org/administrators/complex-policies-on-windows/)、[Windows 出站规则命令](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule)、[Claude Code 网络配置](https://code.claude.com/docs/en/network-config)。
