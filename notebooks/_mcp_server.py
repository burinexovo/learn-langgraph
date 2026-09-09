"""A minimal local MCP server shared by 12_mcp_tools.ipynb and 14_capstone_it_ticket_agent.ipynb.

Runs entirely over stdio as a subprocess -- no network access, no API key.
This is what a "real" MCP server looks like from the provider side; the
notebooks connect to it as a client, same as they would for any third-party
MCP server.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("demo-tools")


@mcp.tool()
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"{city}: sunny, 28C"


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@mcp.tool()
def check_service_status(service: str) -> str:
    """Check whether an internal service is healthy."""
    if service == "billing-api":
        return "billing-api: DEGRADED - high latency on /invoices, restart recommended"
    return f"{service}: OK"


@mcp.tool()
def lookup_runbook(topic: str) -> str:
    """Look up an internal runbook entry for a known issue."""
    runbooks = {
        "billing-api-latency": "Runbook: restart billing-api pod, then verify /health returns 200.",
    }
    return runbooks.get(topic, f"No runbook found for '{topic}'.")


if __name__ == "__main__":
    mcp.run(transport="stdio")
