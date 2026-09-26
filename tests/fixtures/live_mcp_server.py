import os
from mcp.server import MCPServer

mcp = MCPServer("KCC Discovery Fixture")
mode=os.environ.get("KCC_FIXTURE_MODE","base")

def lookup_item(query: str) -> str:
    return query
lookup_item.__doc__ = "Search and retrieve an item without mutation." + (" Changed contract." if mode=="changed" else "")
mcp.tool()(lookup_item)

if mode != "removed":
    @mcp.tool()
    def delete_item(item_id: str) -> str:
        """Delete an item permanently."""
        return item_id

if mode == "added":
    @mcp.tool()
    def create_item(name: str) -> str:
        """Create a new item."""
        return name

if __name__ == "__main__":
    mcp.run()
