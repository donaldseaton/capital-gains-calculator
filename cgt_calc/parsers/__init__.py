"""Parse input files."""

from __future__ import annotations

import csv
import datetime
from decimal import Decimal
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Final

from cgt_calc.const import DEFAULT_INITIAL_PRICES_FILE
from cgt_calc.exceptions import UnexpectedColumnCountError
from cgt_calc.model import ActionType
from cgt_calc.resources import RESOURCES_PACKAGE

from .mssb import read_mssb_transactions
from .raw import read_raw_transactions
from .schwab import read_schwab_transactions
from .schwab_equity_award_json import read_schwab_equity_award_json_transactions
from .sharesight import read_sharesight_transactions
from .trading212 import read_trading212_transactions

if TYPE_CHECKING:
    from cgt_calc.model import BrokerTransaction

INITIAL_PRICES_COLUMNS_NUM: Final = 3


class InitialPricesEntry:
    """Entry from initial stock prices file."""

    def __init__(self, row: list[str], file: str):
        """Create entry from CSV row."""
        if len(row) != INITIAL_PRICES_COLUMNS_NUM:
            raise UnexpectedColumnCountError(row, INITIAL_PRICES_COLUMNS_NUM, file)
        # date,symbol,price
        self.date = self._parse_date(row[0])
        self.symbol = row[1]
        self.price = Decimal(row[2])

    @staticmethod
    def _parse_date(date_str: str) -> datetime.date:
        """Parse date from string."""
        return datetime.datetime.strptime(date_str, "%b %d, %Y").date()

    def __str__(self) -> str:
        """Return string representation."""
        return f"date: {self.date}, symbol: {self.symbol}, price: {self.price}"


def read_broker_transactions(
    schwab_transactions_file: str | None,
    schwab_awards_transactions_file: str | None,
    schwab_equity_award_json_transactions_file: str | None,
    trading212_transactions_folder: str | None,
    mssb_transactions_folder: str | None,
    sharesight_transactions_folder: str | None,
    raw_transactions_file: str | None,
) -> list[BrokerTransaction]:
    """Read transactions for all brokers."""
    transactions = []
    if schwab_transactions_file is not None:
        transactions += read_schwab_transactions(
            schwab_transactions_file, schwab_awards_transactions_file
        )
    else:
        print("INFO: No schwab file provided")

    if schwab_equity_award_json_transactions_file is not None:
        transactions += read_schwab_equity_award_json_transactions(
            schwab_equity_award_json_transactions_file
        )
    else:
        print("INFO: No schwab Equity Award JSON file provided")

    if trading212_transactions_folder is not None:
        transactions += read_trading212_transactions(trading212_transactions_folder)
    else:
        print("INFO: No trading212 folder provided")

    if mssb_transactions_folder is not None:
        transactions += read_mssb_transactions(mssb_transactions_folder)
    else:
        print("INFO: No mssb folder provided")

    if sharesight_transactions_folder is not None:
        transactions += read_sharesight_transactions(sharesight_transactions_folder)
    else:
        print("INFO: No sharesight file provided")

    if raw_transactions_file is not None:
        transactions += read_raw_transactions(raw_transactions_file)
    else:
        print("INFO: No raw file provided")

    transactions.sort(key=sort_transactions)
    return transactions


def read_initial_prices(
    initial_prices_file: str | None,
) -> dict[datetime.date, dict[str, Decimal]]:
    """Read initial stock prices from CSV file."""
    initial_prices: dict[datetime.date, dict[str, Decimal]] = {}
    if initial_prices_file is None:
        with (
            resources.files(RESOURCES_PACKAGE)
            .joinpath(DEFAULT_INITIAL_PRICES_FILE)
            .open(encoding="utf-8") as csv_file
        ):
            lines = list(csv.reader(csv_file))
    else:
        with Path(initial_prices_file).open(encoding="utf-8") as csv_file:
            lines = list(csv.reader(csv_file))
    lines = lines[1:]
    for row in lines:
        entry = InitialPricesEntry(row, initial_prices_file or "default")
        date_index = entry.date
        if date_index not in initial_prices:
            initial_prices[date_index] = {}
        initial_prices[date_index][entry.symbol] = entry.price
    return initial_prices


def sort_transactions(transaction: BrokerTransaction) -> str:
    """Sorts transactions by date and type.

    (so if shares vest and sell on the same day, the vest is always processed 1st).
    """
    priority = "1"
    if transaction.action == ActionType.SELL:
        priority = "2"
    return transaction.date.strftime("%Y-%m-%d") + priority
