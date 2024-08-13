# coding: utf-8
import telegram
import logging
from datetime import date, timedelta
from telegram import Update
from telegram.ext import (
    Application, filters,
    MessageHandler, CommandHandler, CallbackQueryHandler
)
from beancount.core.inventory import Inventory
from fava.util.date import parse_date
from bean_utils.bean import bean_manager
from bean_utils import txs_query
import conf


OWNER_ID = conf.config.bot.telegram.chat_id


async def start(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="哦")


def owner_required(func):
    async def wrapped(update, context):
        chat_id = update.effective_chat.id
        if chat_id != OWNER_ID:
            return
        await func(update, context)

    return wrapped


def render_table(header, rows):
    data = [[header]]
    for row in rows:
        row_data = list(row)
        for i, obj in enumerate(row):
            if isinstance(obj, Inventory):
                row_data[i] = obj.to_string()
        data.append(row_data)

    return "\n".join(["    ".join(row) for row in data])


@owner_required
async def bill(update, context):
    args = context.args
    root_level = 2
    if args:
        start, end = parse_date(args[0])
        if len(args) > 1:
            root_level = int(args[1])
    else:
        start = date.today()
        end = start + timedelta(days=1)

    if start is None and end is None:
        await update.message.reply_text(f"Wrong args: {args}")

    if (end - start).days == 1:
        header = f"Expenses on {start}"
    else:
        # 查询这段时间的账户变动
        header = f"Expenses between {start} - {end}"
    query = (f'SELECT ROOT(account, {root_level}) as acc, cost(sum(position)) AS cost '
             f'WHERE date>={start} AND date<{end} GROUP BY acc ORDER BY acc;')

    # query = f'SELECT account, cost(sum(position)) AS cost
    # FROM OPEN ON {start} CLOSE ON {end} GROUP BY account ORDER BY account;'
    # 等同于 BALANCES FROM OPEN ON ... CLOSE ON ...
    # 查询结果中 Asset 均为关闭时间时刻的保有量

    _, rows = bean_manager.run_query(query)
    result = render_table(header, rows)
    await update.message.reply_text(str(result))


@owner_required
async def expense(update, context):
    args = context.args
    root_level = 2
    if args:
        start, end = parse_date(args[0])
        if len(args) > 1:
            root_level = int(args[1])
    else:
        start = date.today()
        end = start + timedelta(days=1)

    if start is None and end is None:
        await update.message.reply_text(f"Wrong args: {args}")

    if (end - start).days == 1:
        header = f"Cost on {start}"
    else:
        # 查询这段时间的账户支出
        header = f"Transaction between {start} - {end}"
    query = (f'SELECT ROOT(account, {root_level}) as acc, cost(sum(position)) AS cost '
             f'WHERE date>={start} AND date<{end} AND ROOT(account, 1)="Expenses" GROUP BY acc;')

    _, rows = bean_manager.run_query(query)
    result = render_table(header, rows)
    await update.message.reply_text(str(result))


@owner_required
async def trx_render(update, context):
    button_list = [
        telegram.InlineKeyboardButton("提交", callback_data="提交"),
        telegram.InlineKeyboardButton("取消", callback_data="取消"),
    ]
    reply_markup = telegram.InlineKeyboardMarkup([button_list])

    try:
        message = update.message
        if update.message is None:
            message = update.edited_message
        trxs = bean_manager.generate_trx(message.text)
    except Exception as e:
        rendered = "{}: {}".format(e.__class__.__name__, str(e))
        await update.message.reply_text(rendered, reply_to_message_id=message.message_id)
    else:
        for tx in trxs:
            await update.message.reply_text(tx, reply_to_message_id=message.message_id, reply_markup=reply_markup)


@owner_required
async def callback(update, context):
    message = update.callback_query.message
    trx = message.text
    choice = update.callback_query.data
    query = update.callback_query
    await query.answer()

    if choice == "提交":
        result_msg = "已提交 ✅"
        bean_manager.commit_trx(trx)
        logging.info("Commit transaction\n", trx)
    else:
        result_msg = "已取消 ❌"
        logging.info("Cancel transaction")

    if result_msg:
        await query.edit_message_text(text=f"{trx}\n\n{result_msg}")


@owner_required
async def build_db(update, context):
    entries = bean_manager.entries
    tokens = txs_query.build_tx_db(entries)
    await update.message.reply_text(f"Token usage: {tokens}")


def run_bot():
    application = Application.builder().token(conf.config.bot.telegram.token).build()

    handlers = [
        CommandHandler('start', start),
        CommandHandler('bill', bill, has_args=True),
        CommandHandler('expense', expense, has_args=True),
        CommandHandler('build', build_db, has_args=False),
        MessageHandler(filters.TEXT & (~filters.COMMAND), trx_render),
        CallbackQueryHandler(callback),
    ]
    for handler in handlers:
        application.add_handler(handler)

    print("Bot start")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    import conf
    conf.load_config("config.yaml")
    run_bot()
