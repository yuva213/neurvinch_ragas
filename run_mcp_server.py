#!/usr/bin/env python
"""Runner script for the Neurvinch MCP Server.

Sets up correct python path and runs the FastMCP server.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from neurvinch.mcp_server import mcp

if __name__ == "__main__":
    mcp.run()
