import click
from datetime import datetime, timedelta
from mmpy_bot import Bot, Settings
from mmpy_bot import Plugin, listen_to, listen_webhook
from mmpy_bot.plugins.base import PluginManager
from mmpy_bot.driver import Driver
from mmpy_bot import Message, WebHookEvent
from fava.util.date import parse_date
from beancount.core.inventory import Inventory
from bean_utils.bean import bean_manager
from bots import controller
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

    def gen_action(self, id_, name, trx):
        return {
            "id": id_,
            "name": name,
            "integration": {
                "url": self.gen_hook(id_),
                "context": {
                    "trx": trx,
                    "choice": name,
                }
            }
        }

    @listen_to(r"^-?[\d.]+ ", direct_only=True, allowed_users=[OWNER_NAME])
    async def render(self, message: Message):
        resp = controller.render_txs(message.text)
        if isinstance(resp, controller.ErrorMessage):
            self.driver.reply_to(message, "", props={
                "attachments": [
                    {
                        "text": resp.content,
                        "color": "#ffc107"
                    }
                ]
            })
            return
        for tx in resp:
            tx_content = tx.content
            self.driver.reply_to(message, f"`{tx_content}`", props={
                "attachments": [
                    {
                        "actions": [
                            self.gen_action("submit", "提交", tx_content),
                            self.gen_action("cancel", "取消", tx_content),
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
            start = datetime.now().astimezone().date()
            end = start + timedelta(days=1)
        if start is None and end is None:
            self.driver.reply_to(message, f"Wrong args: {date}")

        resp_table = controller.fetch_bill(start, end, level)
        result = render_table(resp_table.headers, resp_table.rows)
        self.driver.reply_to(message, f"**{resp_table.title}**\n\n{result}")

    @listen_to("expense", direct_only=True, allowed_users=[OWNER_NAME])
    @click.command(help="查询支出")
    @click.option("-l", "--level", default=2, type=int)
    @click.argument("args", nargs=-1, type=str)
    def expense(self, message: Message, level: int, args: str):
        if args:
            start, end = parse_date(args[0])
        else:
            start = datetime.now().astimezone().date()
            end = start + timedelta(days=1)

        if start is None and end is None:
            self.driver.reply_to(message, f"Wrong args: {args}")
            return

        resp_table = controller.fetch_expense(start, end, level)
        result = render_table(resp_table.headers, resp_table.rows)
        self.driver.reply_to(message, f"**{resp_table.title}**\n\n{result}")

    @listen_to("build", direct_only=True, allowed_users=[OWNER_NAME])
    def build_db(self, message: Message):
        msg = controller.build_db()
        self.driver.reply_to(message, msg.content)


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
