# 标准部署：规则 TUN 与新加坡时区

v1.1.0 起，标准部署包含 **TUN 开启并生效**、**整个系统时区设为新加坡**。这是本 Skill 的默认方案，不代表所有 Claude 客户端的技术要求。实施前说明系统级影响；用户未授权、权限不足、当前客户端不支持或影响唯一远程管理路径时，暂停对应修改并标记未完成。不要悄悄省略，也不强行覆盖用户后来的明确限制。

## 变更前

在私有 receipt 记录：原 TUN 状态、运行实例/core/版本、相关持久配置和路由/DNS状态、原系统时区 ID、自动设置时区开关。不要记录订阅凭据或全量网络私密配置。时区变更会改变本地时间显示，可能影响按本地时间安排的任务、日历和日志阅读，先说明这个影响。

系统时区不会改变公网出口 IP、物理位置或服务地区资格。新加坡和某些其他时区同为 UTC+8，不能用偏移量相同代替正确的时区 ID。保留真实 UTC 时间、原有 NTP/自动校时设置、系统地区与语言；不改硬件时钟、不改日期、不伪造浏览器指纹。

## 开启 TUN：Windows 与 macOS

1. 在当前正在使用的代理实例中操作。v2rayN 或其他客户端的菜单、服务和 core 选择随版本不同，先核对本机能力及官方说明。优先其受支持的 TUN 开关/持久设置；不要只改下次启动会被覆盖的生成配置，也不要另外拉起一个争用配置的实例。
2. 保持规则分流：保护域名优先走指定唯一节点；无自动换节点/直连回退。已明确的国内站、独立第三方 API、LAN、Tailscale 和管理通道按原约定直连或旁路。TUN 开启不等于全局所有流量走国外；浏览器 PAC 的 DIRECT 也不保证系统 TUN 会直连，要核对核心的对应路由。
3. 所需管理员、驱动、服务或网络权限使用平台正规授权；只授予本机当前版本所需的权限，不绕过系统安全确认、不关闭防火墙或 LuLu。创建虚拟网卡/重载路由可能中断网络，先确认有恢复通道和中断授权。客户端不支持时，不私自换代理软件。
4. 核对 core 的实际 TUN 入站已启用、虚拟接口存在、目标 IP 的有效系统路由和核心命中符合预期。Windows 可只读使用 `Get-NetAdapter` / `Get-NetRoute`；macOS 可用 `ifconfig`、`route -n get <authorized-test-ip>`。这些结果要结合实际进程/core 流量，接口名字或 GUI 开关亮起本身不足以证明覆盖。
5. 复测国内站、API、LAN/管理通道，检查 DNS、IPv6、UDP/QUIC、代理环路和冲突 VPN。保留原有 MTU、栈等无关参数，发现故障后基于证据单独处理，不顺带全局调参。TUN 下的进程归因可能变化，重新验证现有出站过滤。

**TUN 不能代替 kill switch。** 代理退出后系统路由可能回到物理网络，已有网站强制策略和进程出站保护仍需保留。必须独立做节点失效与代理软件退出测试；TUN 关了以后保护还能否拦住请求属于故障验收，不是省略正常状态 TUN 要求的理由。

## Windows：Singapore Standard Time

先记录 `(Get-TimeZone).Id`，并在“设置 → 时间和语言 → 日期和时间”记录“自动设置时区”的原状态。为固定新加坡时区，只关闭“自动设置时区”（如果已开启且用户授权），不要关闭“自动设置时间”。不批量修改定位服务或系统服务注册表。

确认本机可用此 ID、备份与授权完成后执行：

```powershell
Get-TimeZone -ListAvailable | Where-Object Id -eq 'Singapore Standard Time'
Set-TimeZone -Id 'Singapore Standard Time' -ErrorAction Stop
$zone = Get-TimeZone
if ($zone.Id -ne 'Singapore Standard Time' -or $zone.BaseUtcOffset.TotalHours -ne 8) {
    throw 'Singapore system time zone not effective'
}
```

不要用翻译后的 DisplayName 定位，也不要把 China Standard Time 当成同一 ID。权限不足或组织策略控制时报告待办，不尝试提权绕过。回滚时用 `Set-TimeZone -Id '<receipt-original-id>'` 恢复原 ID，再把自动时区开关恢复到原状态，复核实际值。

## macOS：Asia/Singapore

系统设置 → 通用 → 日期与时间。记录原时区和“使用当前位置自动设置时区”的状态；为固定时区，在授权后关闭该**时区**自动项，选择新加坡作为时区/最近城市。保留自动日期时间和网络时间设置。系统密码或 Touch ID 由用户确认。

经管理员授权，也可先核对本机 `systemsetup` 支持及可用列表，再操作：

```sh
sudo /usr/sbin/systemsetup -gettimezone
sudo /usr/sbin/systemsetup -listtimezones
# 原值已记入私有 receipt，自动时区项已按上文处理后：
sudo /usr/sbin/systemsetup -settimezone Asia/Singapore
sudo /usr/sbin/systemsetup -gettimezone
```

读回应为 Asia/Singapore。不要只看命令退出码；使用系统设置再核对实际状态。回滚用 `systemsetup -settimezone <receipt-original-zone>` 或系统设置恢复原值，再恢复原自动时区开关，不直接改 timed 内部数据库。

## 验证与恢复

在实际使用的浏览器本地控制台读取 `Intl.DateTimeFormat().resolvedOptions().timeZone`；标准部署预期为 `Asia/Singapore`。若仍是旧时区，先检查应用缓存、TZ 环境或已存在的仿真设置；需要重开应用时先让用户保存工作，不强杀、不重启电脑。不要为让结果“对上”另加指纹伪装。

交付分别报告：TUN 已请求／已开启／有效路径已观察；系统时区 ID；浏览器时区；原生客户端故障验收。输出 JSON 的 required 字段只是目标，不是已完成证据。

撤销配置时先停止受保护目标的新请求，保留管理通道和阻断规则，再恢复原 TUN/路由/DNS和时区/自动时区状态。确认原网络行为恢复后，按原有 receipt 撤销本次新增的守护规则/浏览器策略。中途失败保留保护并报告，不重置全部网络、不关闭系统过滤、不退出远程登录。

官方来源：[Windows Set-TimeZone](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/set-timezone)、[Apple 日期与时间设置](https://support.apple.com/guide/mac-help/set-the-date-and-time-automatically-mchlp2996/mac)、[Apple systemsetup](https://support.apple.com/en-is/guide/remote-desktop/apd95406b8d/mac)、[v2rayN 官方文档入口](https://github.com/2dust/v2rayN/wiki)、[sing-box TUN](https://sing-box.sagernet.org/configuration/inbound/tun/)。实施时按本机版本核对，不照搬其他核心的配置字段。
