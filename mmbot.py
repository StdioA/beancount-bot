import click
import datetime
from datetime import timedelta
from mmpy_bot import Bot, Settings
from mmpy_bot import Plugin, listen_to, listen_webhook
from mmpy_bot.plugins.base import PluginManager
from mmpy_bot.driver import Driver
from mmpy_bot import Message, WebHookEvent
from fava.util.date import parse_date
from beancount.core.inventory import Inventory
from beancount.core.data import Transaction
from bean import bean_manager
import txs_query
import conf


OWNER_NAME = conf.config.bot.mattermost.owner_user


def render_table(header, rows):
    data = [header]
    for row in rows:
        row_data = list(row)
        for i, obj in enumerate(row):
            if isinstance(obj, Inventory):
                row_data[i] = obj.to_string()
        data.append(row_data)

    column = 1
    if rows:
        column = max(column, max(len(r) for r in rows))
    else:
        data.append([""])
    header_line = "|" + "|".join(data[0]) + "|"
    table_line = "|" + "-|" * column
    data_lines = ["|".join(["", *r, ""]) for r in data[1:]]

    return "\n".join([header_line, table_line, *data_lines])


class BeanBotPlugin(Plugin):
    def initialize(self, driver: Driver, plugin_manager: PluginManager, settings: Settings):
        super().initialize(driver, plugin_manager, settings)
        self.webhook_host_url = settings.WEBHOOK_HOST_URL
        self.webhook_host_port = settings.WEBHOOK_HOST_PORT
        return self

    def gen_hook(self, action):
        return f"{self.webhook_host_url}:{self.webhook_host_port}/hooks/{action}"

    def gen_action(self, id, name, trx):
        return {
            "id": id,
            "name": name,
            "integration": {
                "url": self.gen_hook(id),
                "context": {
                    "trx": trx,
                    "choice": name,
                }
            }
        }

    @listen_to(r"^-?[\d.]+ ", direct_only=True, allowed_users=[OWNER_NAME])
    async def render(self, message: Message):
        try:
            trx = bean_manager.generate_trx(message.text)
        except Exception as e:
            rendered = "{}: {}".format(e.__class__.__name__, str(e))
            self.driver.reply_to(message, "", props={
                "attachments": [
                    {
                        "text": rendered,
                        "color": "#ffc107"
                    }
                ]
            })
            return
        self.driver.reply_to(message, f"`{trx}`", props={
            "attachments": [
                {
                    "actions": [
                        self.gen_action("submit", "提交", trx),
                        self.gen_action("cancel", "取消", trx),
                    ]
                }
            ]
        })

    @listen_webhook("^(submit|cancel)$")
    async def submit_listener(self, event: WebHookEvent):
        post_id = event.body["post_id"]
        trx = event.body["context"]["trx"]
        webhook_id = event.webhook_id

        if webhook_id == "submit":
            reaction = "white_check_mark"
            bean_manager.commit_trx(trx.strip())
        else:
            reaction = "wastebasket"

        self.driver.respond_to_web(event, {
            "update": {
                "message": f"`{trx}`",
                "props": {}
            },
        })
        self.driver.react_to(Message({
            "data": {"post": {"id": post_id}},
        }), reaction)

    # 需要改 listen_to 实现中对 reg 的替换代码，以支持单独命令输入
    @listen_to("bill", direct_only=True, allowed_users=[OWNER_NAME])
    @click.command(help="查询账户变动")
    @click.option("-l", "--level", default=2, type=int)
    @click.argument("date", nargs=-1, type=str)
    def bill(self, message: Message, level: int, date: str):
        if date:
            start, end = parse_date(date[0])
        else:
            start = datetime.date.today()
            end = start + timedelta(days=1)
        if start is None and end is None:
            self.driver.reply_to(message, f"Wrong args: {date}")

        if (end - start).days == 1:
            title = f"Expenses on {start}"
        else:
            # 查询这段时间的账户变动
            title = f"Expenses between {start} - {end}"
        query = (f'SELECT ROOT(account, {level}) as acc, cost(sum(position)) AS cost '
                 f'WHERE date>={start} AND date<{end} GROUP BY acc ORDER BY acc;')

        # query = f'SELECT account, cost(sum(position)) AS cost
        # FROM OPEN ON {start} CLOSE ON {end} GROUP BY account ORDER BY account;'
        # 等同于 BALANCES FROM OPEN ON ... CLOSE ON ...
        # 查询结果中 Asset 均为关闭时间时刻的保有量

        _, rows = bean_manager.run_query(query)
        result = render_table(["Account", "Position"], rows)
        self.driver.reply_to(message, f"**{title}**\n\n{result}")

    @listen_to("expense", direct_only=True, allowed_users=[OWNER_NAME])
    @click.command(help="查询支出")
    @click.option("-l", "--level", default=2, type=int)
    @click.argument("args", nargs=-1, type=str)
    def expense(self, message: Message, level: int, args: str):
        if args:
            start, end = parse_date(args[0])
        else:
            start = datetime.date.today()
            end = start + timedelta(days=1)

        if start is None and end is None:
            self.driver.reply_to(message, f"Wrong args: {args}")
            return

        if (end - start).days == 1:
            title = f"Cost on {start}"
        else:
            # 查询这段时间的账户支出
            title = f"Transaction between {start} - {end}"
        query = (f'SELECT ROOT(account, {level}) as acc, cost(sum(position)) AS cost '
                 f'WHERE date>={start} AND date<{end} AND ROOT(account, 1)="Expenses" GROUP BY acc;')

        _, rows = bean_manager.run_query(query)
        result = render_table(["Account", "Position"], rows)
        self.driver.reply_to(message, f"**{title}**\n\n{result}")

    @listen_to("build", direct_only=True, allowed_users=[OWNER_NAME])
    def build_db(self, message: Message):
        entries = bean_manager.entries
        amount = conf.config.embedding.transaction_amount
        # Build latest transactions
        entries = [e for e in entries if isinstance(e, Transaction)][-amount:]
        tokens = txs_query.build_tx_db(entries)
        self.driver.reply_to(message, f"Token usage: {tokens}")


def run_bot():
    mm_conf = conf.config.bot.mattermost
    bot = Bot(
        settings=Settings(
            MATTERMOST_URL=mm_conf.server_url,
            MATTERMOST_PORT=mm_conf.server_port,
            BOT_TOKEN=mm_conf.bot_token,
            BOT_TEAM=mm_conf.bot_team,
            SSL_VERIFY=mm_conf.ssl_verify,

            WEBHOOK_HOST_ENABLED=True,
            WEBHOOK_HOST_PORT=mm_conf.webhook_host_port,
            WEBHOOK_HOST_URL=mm_conf.webhook_host_url,
        ),  # Either specify your settings here or as environment variables.
        plugins=[BeanBotPlugin()],  # Add your own plugins here.
    )
    bot.run()


if __name__ == "__main__":
    import conf
    conf.load_config("config.yaml")
    run_bot(conf.config)
