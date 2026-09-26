# tgtg-python(加固版)

[English](README.md) · [项目结构](Structure.md)

[TooGoodToGo](https://toogoodtogo.com) 的非官方 Python 客户端,外加一个监控脚本——收藏
店铺一上 surprise bag 就推送提醒。

本项目 fork 自 [ahivert/tgtg-python](https://github.com/ahivert/tgtg-python)。库的接口
与上游保持一致,区别在于修掉了几个和 DataDome 反爬、令牌刷新相关的 bug,并新增了一个为
长期无人值守运行而设计的监控脚本——目标是连续跑几周而不被风控标记。

Python 3.9+ · GPL-3.0

## 能做什么

- **盯收藏**,有货的瞬间推送到手机
- **自动占单**,免得你摸手机的几秒里包被别人抢走
- **读取**商品、店铺、订单和历史订单

## 不能做什么

- **付款。** 客户端能创建预留订单(`state: RESERVED`),但支付走的是移动端 SDK,没有实现。
  你得在手机 app 里完成付款,而且只有预留生效的那几分钟时间。
- **解 DataDome 验证码。** 一旦 TooGoodToGo 的反爬决定挑战你,所有请求都返回 `403` 和一个
  `geo.captcha-delivery.com` 链接,这个进程里没有任何东西能应答它。唯一的办法是等,以及
  让行为不那么像机器人。
- **跑在 VPN 或云服务器上。** DataDome 把机房和 VPN 网段判定为高风险。请用住宅网络:
  家庭宽带或手机热点。

这个项目对接的是未公开 API。自动化使用很可能违反 TooGoodToGo 的服务条款,账号风险由你
自己承担。

## 安装

```bash
pipx install uv
uv sync --all-extras
```

或者用标准虚拟环境:

```bash
python -m venv .venv
./.venv/bin/pip install -e ".[dev]"
```

## 监控脚本快速上手

```bash
# 1. 登录一次,需要输入 TooGoodToGo 邮件里的 PIN 码
./.venv/bin/python examples/watch_favorites.py --login --email 你的邮箱

# 2. 看看收藏里有什么,以及当前有没有货
./.venv/bin/python examples/watch_favorites.py --list

# 3. 开始盯,有货就推送到你的私密 ntfy topic
./.venv/bin/python examples/watch_favorites.py --notify https://ntfy.sh/一个随机串

# 4. 确认通知能收到之后,再开自动占单
./.venv/bin/python examples/watch_favorites.py --notify https://ntfy.sh/一个随机串 --reserve 1
```

凭据写在 `~/.config/tgtg/credentials.json`,权限 `0600`,**不会落在仓库里**。通知支持
[ntfy](https://ntfy.sh)、Bark 和 Telegram;不加通知参数就只打日志。

> ntfy.sh 的公开 topic 任何人知道名字就能订阅,也能往里发消息。用一长串随机字符,别用
> 能猜到的名字——否则等于把你的店什么时候上货广播给竞争者。

### 命令

| 命令 | 作用 |
| --- | --- |
| `--login --email <邮箱>` | 交互式 PIN 登录,保存凭据 |
| `--list` | 打印所有收藏及当前库存后退出 |
| `--diagnose` | 一次匿名探测:这个网络到底通不通? |
| `--reset-identity` | 清掉存储的设备指纹,保留令牌 |
| `--once` | 只轮询一次就退出 |
| (不带命令) | 持续监控 |

出问题时优先用 `--diagnose`。它用全新身份、不带任何凭据发一个请求,因此能区分
**网络被封** 和 **账号被封**——这个区别单看 `--list` 失败是分不出来的。

### 参数调整

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--interval` | `120` | 轮询间隔(秒) |
| `--jitter` | `30` | 随机 ± 秒数,避免请求过于规律 |
| `--active-hours` | `7-23` | 本地时间窗口;`0-24` 表示不休息;`22-6` 表示跨夜 |
| `--max-polls-per-day` | `600` | 每日硬上限,用完会睡到午夜 |
| `--max-reserves-per-day` | `3` | 自动占单的每日上限 |
| `--store <关键词>` | — | 只盯匹配的店铺,可重复 |

**调低 `--interval` 之前先算一下。** 16 小时窗口按 60 秒轮询是 960 次,会在下午就把
600 次/天的预算用完,然后你在傍晚上货的时段是瞎的。正确做法是缩窗口——请求更少,而且
在关键时段还更快:

```bash
# 5 小时 / 60 秒 = 300 次,只用一半预算,速度翻倍
./.venv/bin/python examples/watch_favorites.py --active-hours 16-21 --interval 60 \
    --notify https://ntfy.sh/你的topic
```

### 长期运行

```bash
caffeinate -i ./.venv/bin/python examples/watch_favorites.py --notify https://ntfy.sh/你的topic
```

`caffeinate -i` 阻止 Mac 空闲休眠,否则轮询会无声无息地停掉。笔记本**合盖仍然会睡**。
`tmux` 或 `nohup` 能让进程在你关闭终端后继续活着,但对休眠没用。

## 直接使用库

```python
from tgtg import TgtgClient

# 首次运行:会提示输入邮件里的 PIN
client = TgtgClient(email="you@example.com")
credentials = client.get_credentials()

# 之后:用存下的凭据构造
client = TgtgClient(**credentials)

for item in client.get_favorites():
    print(item["display_name"], item["items_available"])
```

所有公开方法都会先调 `login()`,它会在需要时自动刷新 access token。逐个接口的响应结构见
[docs/api-reference.md](docs/api-reference.md),各部分如何配合见 [Structure.md](Structure.md)。

## 这个 fork 修了什么

库(`tgtg/`):

- **已登录请求从不发送 DataDome cookie。** 请求一旦自带 `Cookie` 头,`cookielib` 就会
  完全跳过 cookie jar,于是所有用存储凭据构造的请求都静默丢掉了刚刚取到的 cookie。
- **超过一天的令牌永远不刷新。** `timedelta.seconds` 会丢掉整天部分,一个 24 小时前的
  令牌看起来"才过了 1 秒"。
- **`login()` 强制要求 cookie**,可它并不是认证凭据——刚重置过的客户端重新获取一个就行。
- **每次启动都是一台新设备。** user-agent、correlation id 和 DataDome cookie 现在可以跨
  重启复用,不再每个进程现铸一套。
- **user-agent 和指纹自相矛盾。** 客户端一边声称自己是 Android 9 的 Nexus 5,一边告诉
  DataDome 自己是 Android 14 的 Pixel 7 Pro。现在用设备档案让两者保持一致。
- **握手失败不说原因。** 原来一律打印 `Failed to fetch DataDome cookie`,现在会说清是
  HTTP 403、超时,还是响应无法解析。

监控脚本(`examples/watch_favorites.py`)补上了裸轮询循环缺少的克制:熔断器(宁可停止也
不把自己重试进更深的封锁)、单实例锁、每日请求预算、活跃时间窗,以及把密钥挡在仓库之外、
把令牌挡在日志之外的凭据处理。

## 开发

```bash
make test     # pytest,带分支覆盖率
make lint     # ruff check + ruff format --check
```

101 个测试。HTTP 用 [responses](https://github.com/getsentry/responses) 打桩,时间用
[freezegun](https://github.com/spulec/freezegun) 冻结;除非设置了 `TGTG_EMAIL`,没有任何
测试会碰真实 API。

## 致谢

上游库作者 [Anthony Hivert](https://github.com/ahivert)。GPL-3.0 许可,见
[LICENCE](LICENCE)。
