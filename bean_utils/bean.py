import os
import re
from datetime import date
from decimal import Decimal
from beancount import loader
from beancount.parser import parser
from beancount.query import query
from beancount.core.data import Open, Transaction
from typing import List
from .txs_query import query_txs
import conf


NoTransactionError = ValueError("No transaction found")
transaction_tmpl = """
{date} * "{payee}" "{desc}"{tags}
  {from_account}\t\t\t{amount:.2f} {currency}
  {to_account}"""


TXS_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}(.*)")


class BeanManager:
    def __init__(self, fname=None) -> None:
        self.fname = fname or conf.config.beancount.filename
        self.currency = conf.config.beancount.currency
        self._load()

    def _load(self):
        self._entries, errors, self._options = loader.load_file(self.fname)
        self._accounts = []
        self.mtimes = {}
        for ent in self._entries:
            if isinstance(ent, Open):
                self._accounts.append(ent.account)

        # Fill mtime
        for f in self._options["include"]:
            self.mtimes[f] = os.stat(f).st_mtime

    def _auto_reload(self, accounts_only=False):
        # Check and reload
        for f, mtime in self.mtimes.items():
            if accounts_only and ("accounts" not in f):
                continue
            if mtime != os.stat(f).st_mtime:
                self._load()
                return

    @property
    def entries(self):
        self._auto_reload()
        return self._entries

    @property
    def options(self):
        self._auto_reload()
        return self._options

    @property
    def accounts(self):
        self._auto_reload(accounts_only=True)
        return self._accounts

    def find_account(self, account_str):
        for account in self.accounts:
            if account_str in account:
                return account
        return None

    def find_account_by_payee(self, payee, kind="Expenses"):
        target = None
        for trx in reversed(self._entries):
            if not isinstance(trx, Transaction):
                continue
            if trx.payee == payee:
                target = trx
                break
        else:
            return None
        for posting in target.postings:
            if posting.account.startswith(kind):
                return posting.account
        return None

    def run_query(self, q):
        return query.run_query(self.entries, self.options, q)

    def match_new_args(self, args) -> List[List[str]]:
        # Query from vector db
        matched_txs = query_txs(" ".join(args[1:]))
        candidate_args = []
        for tx in matched_txs:
            # Rebuild narrations
            sentence = parse_args(tx["sentence"])
            new_args = [args[0]] + sentence[2:4] + sentence[:2]
            candidate_args.append(new_args)
        return candidate_args

    def build_txs(self, args):
        amount, from_acc, to_acc, *extra = args

        amount = Decimal(amount)
        from_account = self.find_account(from_acc)
        to_account = self.find_account(to_acc)
        payee = None

        if from_account is None:
            raise ValueError(f"Account {from_acc} not found")
        if to_account is None:
            payee = to_acc
            to_account = self.find_account_by_payee(payee)
            if to_account is None:
                raise ValueError(f"Account {to_acc} not found")

        if payee is None:
            payee, *extra = extra
        kwargs = {
            "date": date.today(),
            "payee": payee,
            "from_account": from_account,
            "to_account": to_account,
            "amount": -amount,
            "desc": "",
            "tags": "",
            "currency": self.currency,
        }

        tags = []
        for arg in extra:
            if arg.startswith("#") or arg.startswith("^"):
                tags.append(arg)
            elif not kwargs["desc"]:
                kwargs["desc"] = arg
        if tags:
            kwargs["tags"] = " " + " ".join(tags)

        return transaction_tmpl.format(**kwargs)

    def generate_trx(self, line) -> List[str]:
        args = parse_args(line)
        try:
            return [self.build_txs(args)]
        except ValueError:
            candidate_args = self.match_new_args(args)
            candidate_txs = []
            for args in candidate_args:
                try:
                    candidate_txs.append(self.build_txs(args))
                except ValueError:
                    pass
            return candidate_txs

    def clone_trx(self, text) -> str:
        entries, _, _ = parser.parse_string(text)
        try:
            txs = next(e for e in entries if isinstance(e, Transaction))
        except StopIteration:
            raise NoTransactionError

        # Parse transaction from given string
        lines = [txs.meta["lineno"]] + [p.meta["lineno"] for p in txs.postings]
        segments = text.split("\n")[min(lines)-1:max(lines)]
        # Modify date
        today = str(date.today())
        segments[0] = TXS_DATE_RE.sub(rf"{today}\1", segments[0])
        return "\n".join(segments)

    def commit_trx(self, data):
        fname = self.fname
        with open(fname, 'a') as f:
            f.write("\n" + data + "\n")
        os.system(f"bean-format -o {fname} {fname} &")


def parse_args(line):
    args = []
    quotes = {
        '"': '"',
        "'": "'",
        "“": "”",
        "”": "“",
    }

    buffer = []
    end_quote = ""
    for segment in line.split(" "):
        if not segment:
            if buffer:
                buffer.append(segment)
            continue

        if buffer:
            if segment[-1] == end_quote:
                # Quote ends
                buffer.append(segment[:-1])
                args.append(" ".join(buffer))
                buffer = []
            else:
                buffer.append(segment)
        elif segment[0] in quotes:
            end_quote = quotes[segment[0]]
            if segment[-1] == end_quote:
                # Single segment with quotes
                args.append(segment[1:-1])
            else:
                # Quote starts
                buffer.append(segment[1:])
        else:
            args.append(segment)
    if buffer:
        raise ValueError("Quote not closed")
    return args


if __name__ == "__main__":
    # Tricky initialize
    conf.load_config("config.yaml")


bean_manager = BeanManager()


if __name__ == "__main__":
    print(bean_manager.generate_trx("12.8 微信 饮料 咖啡"))
    print(bean_manager.generate_trx('12.8 微信 饮料 咖啡 "拿铁 AA"'))
    print(bean_manager.generate_trx("12.8 南京银行 微信 转账"))
    print(bean_manager.generate_trx("12.8 南京银行 微信 ”转账“ '转账1 转账2'"))