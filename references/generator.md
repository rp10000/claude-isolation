# 离线生成器

需要 Python 3.10+；不联网、无第三方 Python 依赖、不读取任何账号，不修改系统。公共后缀校验使用包内官方 Public Suffix List 快照（含私有托管后缀），来源与许可见 THIRD-PARTY-NOTICES.md。

1. 复制 `assets/example-config.json` 到私有工作目录。
2. 探测正在使用的本地 **HTTP 或 mixed** 代理端口后填写 `proxy_port`。不支持只提供 SOCKS 的端口。默认例子不代表本机端口。
3. `providers` 默认为 `claude`。用户要求时才加 `openai`、`gemini`；域名清单是起点，登录链路变化需观察补充。
4. `extra_domains` 填裸域名，不填 URL、端口、通配符或公共后缀。每项同时匹配自身和子域。脚本对自定义输入拒绝公共后缀和几个明确的共享供应商根域；这不代表其他输入已获得服务归属认证。内置供应商清单允许特定服务自己的内容托管根域（如 claudeusercontent.com），这是明确维护的例外，不开放给任意自定义后缀。人工确认每个自定义域名及其子域范围，不能把不相关站点或整个共享 CDN 加入。
5. `unprotected=direct`：其他网站直连；`proxy-then-direct`：其他网站先走同一本地代理，失败可直连。后者的直连回退**不适用于保护域名**。这会覆盖 Chrome 原有代理策略，先核对现有行为；不合适时由代理自身承担普通网站分流，审阅后调整。
6. `router_sources` 默认空，不输出路由规则。需要路由补充时只填用户确认的单个内网 IPv4；不要扫描全网或推断全局保护。

```sh
python scripts/generate.py --config /path/to/private-config.json --out /path/to/new-output
```

输出：PAC、Chrome 策略 JSON、可移除的 macOS 用户描述文件、域名表、`setup-requirements.json`（规则 TUN 与新加坡系统/浏览器时区的待执行要求）、状态和哈希清单；有源 IP 时另有爱快 V4 请求**计划**。输出目录必须不存在，父目录必须存在，不覆盖旧备份。生成失败的目录需人工检查后处理，不能当完成结果。

JSON 是策略数据，不是 Chrome 界面可直接导入的设置文件。macOS 走描述文件；Windows 按平台参考部署。不要把 JSON 复制进 Preferences，或用推荐级策略冒充强制级策略。`chrome://policy` 是有效性检查入口。

PAC 的本地域名和私有 IPv4/Tailscale 地址保留直连；受保护域名先匹配。IPv6 本地特例仅含 `::1`，不要把其他 IPv6 自动加为旁路。完整 IPv6、DNS、QUIC 需要平台和实测补足。

脚本不安装软件、不配置节点、不生成凭据、不自动把本地端口绑定某个远端出口，也不会开启 TUN 或修改时区。`setup-requirements.json` 中 required=true 是部署目标，verified=false 保留待验证状态；代理需按 tun-timezone.md 在获得设置授权后实施。不得声称生成即隔离成功。
