# coding: utf-8
import time
from conf.i18n import gettext as _
from datetime import timedelta, datetime
import telegram
from telegram import Update
from telegram.ext import (
    Application, filters,
    MessageHandler, CommandHandler, CallbackQueryHandler
)
from fava.util.date import parse_date
from bean_utils.bean import bean_manager
from bots import controller
import conf


OWNER_ID = conf.config.bot.telegram.chat_id


async def start(update, context):
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    uptime = timedelta(seconds=time.monotonic())
    await update.message.reply_text(text=f"Now: {now}\nUptime: {uptime}")


def owner_required(func):
    async def wrapped(update, context):
        chat_id = update.effective_chat.id
        if chat_id != OWNER_ID:
            return
        await func(update, context)

    return wrapped


def _render_tg_table(headers, rows):
    MARGIN = 2
    max_widths = list(map(len, headers))
    for row in rows:
        for i, cell in enumerate(row):
            max_widths[i] = max(len(str(cell)), max_widths[i])
    # Write header
    table = []
    raw_row = []
    for i, header in enumerate(headers):
        raw_row.append(f"{header}{' ' * (max_widths[i] - len(header) + MARGIN)}")
    table.append(raw_row)
    table.append("-" * (sum(max_widths) + MARGIN * (len(max_widths) - 1)))
    # Write rows
    for row in rows:
        raw_row = []
        for i, cell in enumerate(row):
            raw_row.append(f"{cell}{' ' * (max_widths[i] - len(str(cell)) + MARGIN)}")
        table.append(raw_row)

    return "\n".join("".join(row) for row in table)


def _escape_md2(text):
    return text.replace("-", "\\-").replace("*", "\\*")


def _parse_bill_args(args):
    root_level = 2
    if args:
        start, end = parse_date(args[0])
        if len(args) > 1:
            root_level = int(args[1])
    else:
        start = datetime.now().astimezone().date()
        end = start + timedelta(days=1)
    return start, end, root_level


@owner_required
async def bill(update, context):
    start, end, root_level = _parse_bill_args(context.args)
    if start is None and end is None:
        await update.message.reply_text(f"Wrong args: {context.args}")
        return
    resp_table = controller.fetch_bill(start, end, root_level)
    result = _render_tg_table(resp_table.headers, resp_table.rows)
    message = update.message
    if update.message is None:
        message = update.edited_message
    await message.reply_text(_escape_md2(f"{resp_table.title}\n```\n{result}\n```"),
                                    parse_mode="MarkdownV2")


@owner_required
async def expense(update, context):
    start, end, root_level = _parse_bill_args(context.args)
    if start is None and end is None:
        await update.message.reply_text(f"Wrong args: {context.args}")
        return
    resp_table = controller.fetch_expense(start, end, root_level)
    result = _render_tg_table(resp_table.headers, resp_table.rows)
    message = update.message
    if update.message is None:
        message = update.edited_message
    await message.reply_text(_escape_md2(f"{resp_table.title}\n```\n{result}\n```"),
                                    parse_mode="MarkdownV2")


_button_list = [
    telegram.InlineKeyboardButton(_("Submit"), callback_data="submit"),
    telegram.InlineKeyboardButton(_("Cancel"), callback_data="cancel"),
]
_pending_txs_reply_markup = telegram.InlineKeyboardMarkup([_button_list])


@owner_required
async def render(update, context):
    message = update.message
    if update.message is None:
        message = update.edited_message

    resp = controller.render_txs(message.text)
    if isinstance(resp, controller.ErrorMessage):
        await update.message.reply_text(resp.content, reply_to_message_id=message.message_id)
        return

    for tx in resp:
        await update.message.reply_text(tx.content, reply_to_message_id=message.message_id,
                                        reply_markup=_pending_txs_reply_markup)


@owner_required
async def callback(update, context):
    message = update.callback_query.message
    trx = message.text
    choice = update.callback_query.data
    query = update.callback_query
    await query.answer()

    if choice == "submit":
        result_msg = _("Submitted ✅")
        bean_manager.commit_trx(trx)
        conf.logger.info("Commit transaction: %s\n", trx)
    else:
        result_msg = _("Cancelled ❌")
        conf.logger.info("Cancel transaction")

    if result_msg:
        await query.edit_message_text(text=f"{trx}\n\n{result_msg}")


@owner_required
async def build_db(update, context):
    msg = controller.build_db()
    await update.message.reply_text(msg.content)


@owner_required
async def clone_txs(update, context):
    # Fetch ref message
    message = update.message.reply_to_message
    if message is None:
        await update.message.reply_text("Please specify the transaction", reply_to_message_id=message.message_id)
        return
    # Fetch original message
    resp = controller.clone_txs(message.text)
    if isinstance(message, controller.ErrorMessage):
        await update.message.reply_text(resp.content, reply_to_message_id=message.message_id)
    else:
        await update.message.reply_text(resp.content, reply_to_message_id=message.message_id,
                                        reply_markup=_pending_txs_reply_markup)


def run_bot():
    application = Application.builder().token(conf.config.bot.telegram.token).build()

    handlers = [
        CommandHandler('start', start),
        CommandHandler('bill', bill),
        CommandHandler('expense', expense),
        CommandHandler('build', build_db, has_args=False),
        CommandHandler('clone', clone_txs, filters=filters.REPLY, has_args=False),
        MessageHandler(filters.TEXT & (~filters.COMMAND), render),
        CallbackQueryHandler(callback),
    ]
    for handler in handlers:
        application.add_handler(handler)

    conf.logger.info("Beancount bot start")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
