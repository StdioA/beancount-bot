import contextlib
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from conf.i18n import gettext as _
import shlex
import subprocess
from beancount import loader
from beancount.parser import parser
from beanquery.query import run_query
from beancount.core import data as d
from beancount.core.number import MISSING
from beancount.parser.printer import EntryPrinter
from typing import List
from bean_utils.vec_query import query_txs
from bean_utils.rag import complete_rag
import conf


NoTransactionError = ValueError("No transaction found")


class BeanManager:
    def __init__(self, fname=None) -> None:
        self.fname = fname or conf.config.beancount.filename
        self.currency = conf.config.beancount.currency
        self._load()
        self._printer = EntryPrinter(dcontext=self._options.get("dcontext"))

    def _load(self):
        """
        Load the beancount file and initialize the internal state.

        This function loads the beancount file specified by `self.fname` and
        initializes the internal state. The internal state includes the entries
        (transactions and metadata), options, accounts, modification times of
        included files, and account files.

        This function does not return anything. It updates the following instance
        variables:
        - `_entries`: a list of parsed entries.
        - `_options`: a dictionary of options.
        - `_accounts`: a set of accounts.
        - `mtimes`: a dictionary mapping filenames to modification times.
        - `account_files`: a set of filenames.
        """
        self._entries, errors, self._options = loader.load_file(self.fname)
        self._accounts = set()
        self.mtimes = {}
        self.account_files = set()
        for ent in self._entries:
            if isinstance(ent, d.Open):
                self._accounts.add(ent.account)
                self.account_files.add(ent.meta["filename"])
            elif isinstance(ent, d.Close):
                self._accounts.remove(ent.account)
                self.account_files.add(ent.meta["filename"])

        # Fill mtime
        for f in self._options["include"]:
            self.mtimes[f] = Path(f).stat().st_mtime

    def _auto_reload(self, accounts_only=False):
        """
        Check and reload if any of the files have been modified.

        Args:
            accounts_only (bool): If True, only check the files that contains account
                transactions. Defaults to False.
        """
        files_to_check = self.mtimes.keys()
        if accounts_only:
            files_to_check = self.account_files
        for fname in files_to_check:
            if self.mtimes[fname] != Path(fname).stat().st_mtime:
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
        """
        Find an account that contains the given string.

        Args:
            account_str (str): A substring to search for in the account string.

        Returns:
            str or None: The account that contains the given substring, or None
                if no such account is found.
        """
        for account in self.accounts:
            if account_str in account:
                return account
        return None

    def find_account_by_payee(self, payee):
        """
        Find the account with the same payee.

        Args:
            payee (str): The payee to search for.

        Returns:
            str or None: The account with the same payee, or None if not found. If the
                transaction has multiple postings with missing units, the first one is
                returned. If no expense account is found, the first expense account in
                the transaction is returned.
        """
        target = None
        for trx in reversed(self._entries):
            if not isinstance(trx, d.Transaction):
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
        """
        A procedural interface to the `beancount.query` module.
        """
        return run_query(self.entries, self.options, q)

    def modify_args_via_vec(self, args) -> List[List[str]]:
        """
        Given a list of arguments, modify the arguments to match the transactions in the vector
        database.

        Args:
            args (List[str]): The arguments to modify.

        Returns:
            List[List[str]]: A list of modified arguments.

        This function queries the vector database to find transactions that match the given
        arguments. It then rebuilds the narrations for each matching transaction and returns a
        list of modified arguments. If no matching transactions are found, an empty list is
        returned.
        """
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
        """
        The core function of transaction generation.

        Args:
            args (List[str]): A list of strings representing the transaction arguments.
                The format is: {amount} {from_account} {to_account} {payee} {narration} [#{tag1} #{tag2} ...].
                The to_account and narration are optional.

        Returns:
            str: The transaction string in the beancount format.

        Raises:
            ValueError: If from_account or to_account is not found.
        """
        amount, from_acc, to_acc, *extra = args

        amount = Decimal(amount)
        from_account = self.find_account(from_acc)
        to_account = self.find_account(to_acc)
        payee = None

        # from_account id requied
        if from_account is None:
            err_msg = _("Account {acc} not found").format(acc=from_acc)
            raise ValueError(err_msg)
        # Try to find the payee if to_account is not found
        if to_account is None:
            payee = to_acc
            to_account = self.find_account_by_payee(payee)
            if to_account is None:
                err_msg = _("Account {acc} not found").format(acc=to_acc)
                raise ValueError(err_msg)

        if payee is None:
            payee, *extra = extra
        desc, tags = "", []
        for arg in extra:
            if arg.startswith(("#", "^")):
                tags.append(arg[1:])
            elif not desc:
                desc = arg

        trx = d.Transaction(
            date=datetime.now().astimezone().date(),
            flag="*",
            payee=payee,
            narration=desc,
            meta={"lineno": 1},
            postings=[
                d.Posting(
                    account=from_account,
                    units=d.Amount(-amount, self.currency),
                    meta={"lineno": 1},
                    cost=None,
                    price=None,
                    flag=None,
                ),
                d.Posting(
                    account=to_account,
                    units=MISSING,
                    meta={"lineno": 1},
                    cost=None,
                    price=None,
                    flag=None,
                ),
            ],
            tags=frozenset(tags),
            links=frozenset(),
        )
        return "\n" + self._printer(trx)


    def generate_trx(self, line) -> List[str]:
        """
        The entry procedure for transaction generation.

        If the line cannot be directly converted into a transaction,
        the function will attempt to match it from a vector database
        or a RAG model. If all attempts fail, a ValueError will be raised.

        Args:
            line (str): The line to generate a transaction from.

        Returns:
            List[str]: A list of transactions generated from the line.

        Raises:
            ValueError: If all attempts to generate a transaction fail.
        """
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
                for new_args in self.modify_args_via_vec(args):
                    with contextlib.suppress(ValueError):
                        candidate_txs.append(self.build_trx(new_args))
                if candidate_txs:
                    return candidate_txs
                # If no match, raise original error,
                # however it may not be happen if vecdb is built.
            raise e

    def clone_trx(self, text, amount=None) -> str:
        """
        Clone a transaction from text.

        Args:
            text (str): Text contains one transaction.

        Returns:
            str: A transaction with today's date.
        """
        entries, _, _ = parser.parse_string(text)
        try:
            txs = next(e for e in entries if isinstance(e, d.Transaction))
        except StopIteration as e:
            raise NoTransactionError from e

        if amount is not None:
            for i, posting in enumerate(txs.postings):
                if posting.units is not MISSING:
                    txs.postings[i] = d.Posting(
                        account=posting.account,
                        units=d.Amount(Decimal(-amount), posting.units.currency),
                        meta=posting.meta,
                        cost=posting.cost,
                        price=posting.price,
                        flag=posting.flag,
                    )
                    break

        txs = d.Transaction(
            date=datetime.now().astimezone().date(),
            flag=txs.flag,
            payee=txs.payee,
            narration=txs.narration,
            meta=txs.meta,
            postings=txs.postings,
            tags=txs.tags,
            links=txs.links,
        )
        return self._printer(txs)

    def commit_trx(self, data):
        """
        Commit a transaction to beancount file, and format.

        Args:
            data (str): The transaction data in beancount format.

        Raises:
            SubprocessError: If the bean-format command fails to execute.
        """
        fname = self.fname

        # Check the end of file to determine proper spacing
        try:
            with open(fname, 'rb') as f:
                # Seek to end and check last few bytes
                f.seek(-10, 2)  # Go to 10 bytes from end
                end_content = f.read().decode('utf-8', errors='ignore')

                # Count existing trailing newlines
                newline_count = 0
                for char in reversed(end_content):
                    if char == '\n':
                        newline_count += 1
                    else:
                        break
        except (IOError, OSError):
            # If file doesn't exist or can't be read, treat as new file
            newline_count = 0

        # Calculate needed spacing: ensure exactly one blank line before, then one after
        prefix = "\n" if newline_count == 0 else ""

        with open(fname, 'a') as f:
            f.write(prefix + data.lstrip("\n") + "\n")
        subprocess.run(["bean-format", "-o", shlex.quote(str(fname)), shlex.quote(str(fname))],   # noqa: S607,S603
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
