# Beancount bot
[![Maintainability](https://api.codeclimate.com/v1/badges/1d9a175911e39f5b576f/maintainability)](https://codeclimate.com/github/StdioA/beancount-bot/maintainability)
[![codecov](https://codecov.io/github/StdioA/beancount-bot/graph/badge.svg?token=PPEO1607AJ)](https://codecov.io/github/StdioA/beancount-bot)
[![ghcr image size](https://ghcr-badge.egpl.dev/stdioa/beancount-bot/size?color=%2344cc11&tag=latest&label=image+size&trim=)](https://github.com/users/stdioa/packages/container/package/beancount-bot)

[English Readme](README.md)

一个可以通过聊天软件快速手动记录简单交易的 beancount bot.

* 前端支持 Telegram 和 Mattermost
* 支持基本账目记录
    * 支持基本文法匹配：`{金额} {流出账户} {流入账户} {payee} {narration} [{#tag1} {#tag2}]`
    * 若当前数据中已存在相同 payee，则流入账户可省略
    * 匹配失败后，可以尝试从向量数据库中进行记录匹配，或通过 RAG 进行信息补全
* 区间内支出统计：`/expense 2024-08`
* 区间内账户变更统计：`/bill 2024-08`
* 提交新记录后，会自动重载账目缓存

## 运行
### 通过 Docker 运行
从 [`config.yaml.example`](config.yaml.example) 复制一份 `config.yaml` 到账本所在目录，并按需更改其中的内容（具体配置含义可参考配置文件中的注释）。

然后下载 [docker/compose.yaml](docker/compose.yaml) 到账本所在目录。如果要运行 Mattermost bot，需要修改 `command` 的值，并配置 `ports` 以暴露端口接收 Webhook.

最后运行 `docker compose up -d` 即可。

### 通过命令行运行
安装基本依赖：`pip install -r requirements/requirements.txt`

若你的设备支持 [sqlite-vec](https://github.com/asg017/sqlite-vec)，则可以额外安装向量数据库组件 `pip install sqlite-vec==0.1.1`，并使用 sqlite 作为数据库；若未安装 `sqlite-vec`，则 bot 会使用 json 来存储向量数据，并使用 numpy 进行向量计算。

如果要使用 Telegram 作为前端，则安装 `python-telegram-bot`: `pip install python-telegram-bot==21.4`;  
如果要使用 Mattermost 作为前端，则安装 `mmpy-bot`: `pip install mmpy-bot==2.1.4`.

最后运行 bot: `python main.py telegram -c config.yaml` 或 `python main.py mattermost -c config.yaml`

## 使用
若使用 Telegram 作为前端，可以预先在 [BotFather](https://telegram.me/BotFather) 处配置 bot 命令列表：

```
start - ping
bill - 查询账户变动
expense - 查询支出
clone - 复制交易
build - 重建向量数据库
```

后续操作都以 Telegram 为前端举例，若使用 Mattermost 作为前端，则使用时的不同会单独注明。

### 基本记账
基本文法：`{金额} {流出账户} [{流入账户}] {payee} {narration} [{#tag1} {#tag2} ...]`，流出和流入账户支持部分匹配。  
若当前数据中已存在相同 payee，则流入账户可省略（`{金额} {流出账户} {payee} {narration}`）；  
若以上匹配规则均失败，则会尝试根据现有信息从向量数据库中匹配一条最接近的数据，并更新它的金额和日期。依靠这种方法可以支持 `{金额} {payee}` 或 `{金额} {narration}` 等格式的记账。

输入后，bot 会补全交易信息并输出，用户可以选择提交或撤销这次更改。

<img src="example/basic_record.png" alt="基本记账示例" width="500" height="350">

### 其他命令
* `/build`: 重建向量数据库
* `/expense {range} {level}`：统计某时间段内的账户支出情况，支持按账户层级组合
    * Mattermost 命令格式参照命令行格式，为 `expense [-l {level}] [{range}]`
    * level 默认为 2，range 默认为昨天
* `/bill {range} {level}`：统计某时间段内的账户变更，支持按账户层级组合
    * Mattermost 为 `bill [-l {level}] [{range}]`
    * 参数默认设置同上
* `/clone`：在已有的交易信息上回复该命令，则可以生成一条新交易，交易日期为当日
    * 由于 Mattermost 对消息引用的支持不够好完善，因此暂时不支持复制，后续可以考虑通过 reaction 等方式达成

## Roadmap
- [x] 使用向量数据库匹配时，支持输出多条备选（以弥补准确率的缺陷）
- [x] 再记一笔
- [ ] 撤回交易
- [x] Docker 支持
- [x] 单元测试
- [ ] 基于 Web 的 Chat UI
- [x] RAG（通过 LLM 进行更精确的元素替换，比如自动将“午饭”改成“晚饭”，或自动更改变更账户等）
- [ ] 支持增量构建向量数据库（如果用 OpenAI 的 `text-embedding-3-large`，目前构建 1000 条交易组成的数据库大概只需要 ￥0.01，而且目前提供 embedding 的供应商大多不对 embedding 功能收费，所以优先级不高）


## Reference
[开始使用 Beancount - Telegram bot](https://blog.stdioa.com/2020/09/using-beancount/#telegram-bot)
