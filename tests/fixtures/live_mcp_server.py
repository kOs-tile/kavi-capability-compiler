import argparse
import os

from mcp.server import MCPServer

mcp = MCPServer("KCC Discovery Fixture")
variant=os.environ.get("KCC_FIXTURE_VARIANT","base")

if variant=="drift":
    @mcp.tool()
    def lookup_item(query: str) -> str:
        """Search and retrieve an item with expanded remote scope."""
        return query

    @mcp.tool()
    def create_item(name: str) -> str:
        """Create a new item."""
        return name
else:
    @mcp.tool()
    def lookup_item(query: str) -> str:
        """Search and retrieve an item without mutation."""
        return query

    @mcp.tool()
    def delete_item(item_id: str) -> str:
        """Delete an item permanently."""
        return item_id

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--http",action="store_true")
    parser.add_argument("--port",type=int,default=8000)
    args=parser.parse_args()
    if args.http:
        mcp.run(transport="streamable-http",host="127.0.0.1",port=args.port)
    else:
        mcp.run()
