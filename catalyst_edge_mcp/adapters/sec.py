"""SEC adapter public module."""

from catalyst_edge_mcp.sec_filings import SecFilingsAdapter
from catalyst_edge_mcp.sec_funds import SecFundAdapter
from catalyst_edge_mcp.sec_ownership import SecInsiderAdapter

__all__ = ["SecFilingsAdapter", "SecFundAdapter", "SecInsiderAdapter"]
