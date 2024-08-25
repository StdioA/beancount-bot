from datetime import date
from dataclasses import dataclass
from conf.i18n import gettext as _
from typing import List, Union, Any
from beancount.core.inventory import Inventory
import requests
from bean_utils import txs_query
from bean_utils.bean import bean_manager, NoTransactionError
import conf


@dataclass
class BaseMessage:
    content: str


@dataclass
class ErrorMessage:
    content: str
    excption: Exception


@dataclass
class Table:
    title: str
    headers: List[str]
    rows: List[List[str]]


def build_db() -> BaseMessage:
    if not conf.config.embedding.get("enable", True):
        return BaseMessage(content=_("Embedding is not enabled."))
    entries = bean_manager.entries
    tokens = txs_query.build_tx_db(entries)
    return BaseMessage(content=_("Token usage: {tokens}").format(tokens=tokens))


def _translate_rows(rows: List[List[Any]]) -> List[List[str]]:
    parsed_rows = []
    for row in rows:
        row_data = list(row)
        for i, obj in enumerate(row):
            if isinstance(obj, Inventory):
                row_data[i] = obj.to_string(parens=False)
        parsed_rows.append(row_data)
    return parsed_rows


def fetch_expense(start: date, end: date, root_level: int = 2) -> Table:
    if (end - start).days == 1:
        title = _("Expenditures on {start}").format(start=start)
    else:
        # 查询这段时间的账户支出
        title = _("Expenditures between {start} - {end}").format(start=start, end=end)
    headers = [_("Account"), _("Position")]
    query = (f'SELECT ROOT(account, {root_level}) as acc, cost(sum(position)) AS cost '
             f'WHERE date>={start} AND date<{end} AND ROOT(account, 1)="Expenses" GROUP BY acc;')

    __, rows = bean_manager.run_query(query)
    return Table(title=title, headers=headers, rows=_translate_rows(rows))


def fetch_bill(start: date, end: date, root_level: int = 2) -> Table:
    if (end - start).days == 1:
        title = _("Account changes on {start}").format(start=start)
    else:
        # 查询这段时间的账户变动
        title = _("Account changes between {start} - {end}").format(start=start, end=end)
    headers = [_("Account"), _("Position")]
    query = (f'SELECT ROOT(account, {root_level}) as acc, cost(sum(position)) AS cost '
             f'WHERE date>={start} AND date<{end} GROUP BY acc ORDER BY acc;')

    # query = f'SELECT account, cost(sum(position)) AS cost
    # FROM OPEN ON {start} CLOSE ON {end} GROUP BY account ORDER BY account;'
    # 等同于 BALANCES FROM OPEN ON ... CLOSE ON ...
    # 查询结果中 Asset 均为关闭时间时刻的保有量
    __, rows = bean_manager.run_query(query)
    return Table(title=title, headers=headers, rows=_translate_rows(rows))


def clone_txs(message: str) -> Union[BaseMessage, ErrorMessage]:
    try:
        cloned_txs = bean_manager.clone_trx(message)
    except ValueError as e:
        if e == NoTransactionError:
            err_msg = e.args[0]
        else:
            err_msg = "{}: {}".format(e.__class__.__name__, str(e))
        return ErrorMessage(err_msg, e)
    return BaseMessage(content=cloned_txs)


def render_txs(message_str: str) -> Union[List[BaseMessage], ErrorMessage]:
    try:
        trxs = bean_manager.generate_trx(message_str)
    except (ValueError, requests.exceptions.RequestException) as e:
        rendered = "{}: {}".format(e.__class__.__name__, str(e))
        return ErrorMessage(rendered, e)
    return [BaseMessage(tx) for tx in trxs]
