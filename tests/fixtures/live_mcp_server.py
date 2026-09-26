from mcp.server import MCPServer

mcp = MCPServer("KCC Discovery Fixture")

@mcp.tool()
def lookup_item(query: str) -> str:
    """Search and retrieve an item without mutation."""
    return query

@mcp.tool()
def delete_item(item_id: str) -> str:
    """Delete an item permanently."""
    return item_id

if __name__ == "__main__":
    mcp.run()
