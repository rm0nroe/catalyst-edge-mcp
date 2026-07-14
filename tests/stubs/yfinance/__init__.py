"""Offline yfinance contract-test stub."""

from types import SimpleNamespace


class Ticker:
    def __init__(self, ticker):
        self.ticker = ticker
        self.options = ("2026-07-17",)

    def option_chain(self, expiration):
        assert expiration == self.options[0]
        return SimpleNamespace(
            calls=[{"volume": 200, "openInterest": 500}],
            puts=[{"volume": 50, "openInterest": 300}],
        )
