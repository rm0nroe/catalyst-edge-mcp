"""SEC fair-access policy is only enforceable through a single shared gate.

Filings, ownership, and funds all hit the same hosts (data.sec.gov and
www.sec.gov/Archives). Two independent gates cannot bound aggregate traffic, so
the 10 rps guideline was previously unenforceable by construction.
"""

from __future__ import annotations

from catalyst_edge_mcp import sec_filings, sec_funds, sec_ownership

# https://www.sec.gov/about/developer-resources — no more than 10 requests/second.
SEC_FAIR_ACCESS_RPS = 10

# One batch of 4 concurrent tickers issues ~28 SEC requests against the service's
# 8s adapter deadline, so anything at or below ~3.5 rps cannot finish in budget
# even at zero network latency. That is what took the scan down.
MIN_RPS_FOR_ONE_BATCH = 4


def test_every_sec_path_shares_one_gate():
    assert sec_ownership.SEC_GATE is sec_filings.SEC_GATE
    assert sec_funds.SEC_GATE is sec_filings.SEC_GATE


def test_shared_gate_respects_sec_fair_access_guideline():
    assert sec_filings.SEC_GATE.requests_per_second <= SEC_FAIR_ACCESS_RPS


def test_shared_gate_can_serve_one_coordinator_batch_in_budget():
    assert sec_filings.SEC_GATE.requests_per_second >= MIN_RPS_FOR_ONE_BATCH
