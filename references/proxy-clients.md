# 代理核心、CLI 模式与第三方 API

## v2rayN 与其他代理客户端

1. 读取当前运行实例、核心类型/版本和实际加载的配置路径。v2rayN GUI、Xray、sing-box、mihomo 是不同层；只看 GUI 选中行不足以确认某次连接。
2. 找到 HTTP/mixed 监听地址和端口，确认仅本机可用、不冲突。检查系统代理、TUN、浏览器策略是否叠加、绕行或形成代理环路。不要把代理端口开放给 LAN 来省事。
3. 保护域名规则应在通用直连/GeoIP/默认规则之前，指向用户指定的唯一出站。不同核心的域名字段/匹配语义不同，按当前官方 schema 编辑；不把 Clash 语法粘贴到 Xray 配置。优先使用客户端持久化的路由/自定义配置入口，不只改下次启动会被覆盖的生成文件。
4. 目标不能指向自动选择、故障转移、负载均衡组或含 DIRECT 的备用链。节点名字可能是任意别名，核对实际 endpoint/传输及中转下一跳；不输出凭据。节点失效应得到连接错误。
5. 备份改动的持久配置字段，保留国内及用户原有其他流量路线。重新加载核心可能中断连接，先评估管理通道；不随意关闭 TUN、全局代理或改整个默认出口。
6. 保护域名的 DNS 选择、UDP/QUIC、IPv6 另行检查。改 DNS/MTU/TUN 栈前先拿测量证据；此 Skill 的目标是隔离，不是顺带全局“加速优化”。

不直接分发全量 v2rayN 数据库、节点配置或订阅；它们包含用户凭据。发布包只提供域名和策略材料，代理对使用者现有配置做最小修改。

## Claude Code 的实际运行上下文

命令行前台、Desktop 内 Code 会话、后台 supervisor、WSL、SSH 远端各自核对。前台 shell 的变量可能到不了已运行的后台进程。当前官方文档说明：代理变量在启动时读取；大小写变量有优先级；部分 Desktop 托管会话只读取 managed settings 和用户设置中的变量；后台 supervisor 可能继承另一个 shell 的环境。

先读本机版本的当前官方文档，再选适用配置源。只在专用官方会话设置代理时，要报告“后台/其他启动入口待验证”。若需覆盖后台进程，先确认不会影响第三方 API 使用，再选择受支持的专用设置/运行环境；不要直接把代理写入所有用户会话的 settings.json。停止 supervisor 可能终止其他工作，必须评估并征得中断授权。

CLI 只设置 HTTP(S) 代理；不把 SOCKS-only 地址当 HTTP。核对 `/status`（若版本支持）和进程真实连接，不公开 debug 日志里的认证信息。不要复制用户 settings 文件进发布包。

## API 与 OAuth

第三方 relay 用独立域名且走直连时，可让网络规则保持该域名原有路径。官方原生 API 常与 OAuth 服务使用同一个供应商域名集；域名防护不会识别认证方式。独立进程的出站封锁同样不识别 token 类型。

用户要求“第三方 API 直连，官方 OAuth 固定代理”时，必须证明它们在域名/客户端/运行上下文上可区分。共用 EXE 或 Node 时，不能一边用进程封锁、一边承诺其 API 自由直连。选择专用官方客户端或用户批准的独立环境；缺少条件则保留待办。

## 无系统过滤时

Chrome 已验证生效的强制 PAC 可以在其受保护网站请求上不提供直连回退。桌面端、外部 helper、任意子进程和其他浏览器不能据此获得同样保证。用户不接受防火墙/网络过滤时，明确给出可实现的范围，不用轮询守护、反复杀进程、hosts 黑洞或全局永久离线来冒充网络 kill switch。

官方来源：[Claude Code 网络配置](https://code.claude.com/docs/en/network-config)、[v2rayN](https://github.com/2dust/v2rayN)、[Xray 路由](https://xtls.github.io/config/routing.html)、[sing-box 路由](https://sing-box.sagernet.org/configuration/route/)、[mihomo 路由规则](https://wiki.metacubex.one/config/rules/)。链接用于实施前核对当前版本，本包不锁定第三方软件版本。
