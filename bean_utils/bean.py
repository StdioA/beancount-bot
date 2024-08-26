import contextlib
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from conf.i18n import gettext as _
import re
import shlex
import subprocess
from beancount import loader
from beancount.parser import parser
from beancount.query import query
from beancount.core.data import Open, Transaction
from beancount.core.number import MISSING
from typing import List
from bean_utils.vec_query import query_txs
from bean_utils.rag import complete_rag
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
            self.mtimes[f] = Path(f).stat().st_mtime

    def _auto_reload(self, accounts_only=False):
        # Check and reload
        for f, mtime in self.mtimes.items():
            if accounts_only and ("accounts" not in f):
                continue
            if mtime != Path(f).stat().st_mtime:
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

    def find_account_by_payee(self, payee):
        # Find the account with the same payee
        target = None
        for trx in reversed(self._entries):
            if not isinstance(trx, Transaction):
                continue
            if trx.payee == payee:
                target = trx
                break
        else:
            return None
        expense_account = None
        # Find the posting with missing units
        # If not found, return the first expense account
        for posting in target.postings:
            if posting.units is MISSING or posting.meta.get("__automatic__"):
                return posting.account
            if posting.account.startswith("Expenses:") and expense_account is None:
                expense_account = posting.account
        return expense_account

    def run_query(self, q):
        return query.run_query(self.entries, self.options, q)

    def match_new_args(self, args) -> List[List[str]]:
        # Query from vector db
        matched_txs = query_txs(" ".join(args[1:]))
        candidate_args = []
        for tx in matched_txs:
            # Rebuild narrations
            sentence = parse_args(tx["sentence"])
            # The tx may contains more than one accounts, so we need to distinguish them by prefix
            tags = [seg for seg in sentence[4:] if seg.startswith("#")]
            #           price     both accounts  payee & narration  tags
            new_args = [args[0]] + sentence[2:4] + sentence[:2] + tags
            candidate_args.append(new_args)
        return candidate_args

    def build_trx(self, args):
        amount, from_acc, to_acc, *extra = args

        amount = Decimal(amount)
        from_account = self.find_account(from_acc)
        to_account = self.find_account(to_acc)
        payee = None

        if from_account is None:
            err_msg = _("Account {acc} not found").format(acc=from_acc)
            raise ValueError(err_msg)
        if to_account is None:
            payee = to_acc
            to_account = self.find_account_by_payee(payee)
            if to_account is None:
                err_msg = _("Account {acc} not found").format(acc=to_acc)
                raise ValueError(err_msg)

        if payee is None:
            payee, *extra = extra
        kwargs = {
            "date": datetime.now().astimezone().date(),
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
            if arg.startswith(("#", "^")):
                tags.append(arg)
            elif not kwargs["desc"]:
                kwargs["desc"] = arg
        if tags:
            kwargs["tags"] = " " + " ".join(tags)

        return transaction_tmpl.format(**kwargs)

    def generate_trx(self, line) -> List[str]:
        args = parse_args(line)
        try:
            return [self.build_trx(args)]
        except ValueError as e:
            vec_enabled = conf.config.embedding.get("enable", True)
            rag_enabled = conf.config.rag.get("enable", False)
            if rag_enabled:
                today = str(datetime.now().astimezone().date())
                accounts = map(self.find_account, args[1:])
                accounts = list(filter(bool, accounts))
                completion = complete_rag(args, today, accounts)
                return [self.clone_trx(completion)]
            if vec_enabled:
                # Query from vector db
                candidate_txs = []
                for new_args in self.match_new_args(args):
                    with contextlib.suppress(ValueError):
                        candidate_txs.append(self.build_trx(new_args))
                if candidate_txs:
                    return candidate_txs
                # If no match, raise original error,
                # however it may not be happen if vecdb is built.
            raise e

    def clone_trx(self, text) -> str:
        entries, _, _ = parser.parse_string(text)
        try:
            txs = next(e for e in entries if isinstance(e, Transaction))
        except StopIteration as e:
            raise NoTransactionError from e

        # Parse transaction from given string
        lines = [txs.meta["lineno"]] + [p.meta["lineno"] for p in txs.postings]
        segments = text.split("\n")[min(lines)-1:max(lines)]
        # Modify date
        today = str(datetime.now().astimezone().date())
        segments[0] = TXS_DATE_RE.sub(rf"{today}\1", segments[0])
        return "\n".join(segments)

    def commit_trx(self, data):
        fname = self.fname
        with open(fname, 'a') as f:
            f.write("\n" + data + "\n")
        subprocess.run(["bean-format", "-o", shlex.quote(fname), shlex.quote(fname)],   # noqa: S607,S603
                       shell=False)


ArgsError = ValueError("Quote not closed")


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
        raise ArgsError
    return args


bean_manager = None


def init_bean_manager(fname=None):
    global bean_manager
    bean_manager = BeanManager(fname)
    return bean_manager
