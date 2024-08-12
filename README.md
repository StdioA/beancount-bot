# Beancount bot
一个可以通过聊天软件快速手动记录简单交易的 beancount bot.

* 前端支持 Telegram 和 Mattermost
* 支持基本账目记录
    * 支持基本文法匹配：`{金额} {流出账户} {流入账户} {payee} {narration}`
    * 若当前数据中已存在相同 payee，则流入账户可省略
    * 匹配失败后，可以尝试从向量数据库中进行匹配
* 区间内支出统计：`/expense 2024-08`
* 区间内账户变更统计：`/bill 2024-08`

_Why is this document written in Chinese? Because the currently defined grammar rules are not as friendly to languages that contain spaces (such as English and French)._

## 安装
`pip install -r requirements.txt`

若你的设备支持 [sqlite-vec](https://github.com/asg017/sqlite-vec)，则额外安装向量数据库组件 `pip install sqlite-vec`，否则 bot 会使用 json 来存储数据库，并使用 numpy 进行向量计算。

如果要使用 Telegram 作为前端，则安装 `python-telegram-bot`: `pip install python-telegram-bot==21.4`;
如果要使用 Mattermost 作为前端，则安装 `mmpy-bot`: `pip install mmpy-bot==2.1.4`.

## 使用
从 `config.yaml.example` 复制一份 `config.yaml`，并按需更改其中的内容。  
然后运行 bot: `python main.py telegram -c config.yaml` 或 `python main.py mattermost -c config.yaml`

后续操作都以 telegram 为例子，若使用 mattermost 作为前端，则在输入命令时需要去掉命令前的斜杠。

### 基本记账
基本文法：`{金额} {流出账户} {流入账户} {payee} {narration}`，流出和流入账户支持部分匹配。  
若当前数据中已存在相同 payee，则流入账户可省略；若匹配失败，则会尝试从向量数据库中匹配一条最接近的数据。

![基本记账示例](example/basic_record.png)

### 其他命令
* `/build`: 构建向量数据库
* `/expense {range} {level}`：获取时间段内的账户支出情况，支持按账户层级组合
    * Mattermost 命令格式参照命令行格式，为 `expense [-l {level}] [{range}]`
    * level 默认为 2，range 默认为昨天
* `/bill {range} {level}`：统计区间内账户变更，支持按账户层级组合
    * Mattermost 为 `bill [-l {level}] [{range}]`
    * 参数默认设置同上

## Reference
[开始使用 Beancount - Telegram bot](https://blog.stdioa.com/2020/09/using-beancount/#telegram-bot)
