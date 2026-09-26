import os
from mcp.server import MCPServer

mcp=MCPServer("KCC HTTP Fixture")

@mcp.tool()
def list_records(limit:int=10)->list[str]:
    """List records without mutation."""
    return []

@mcp.tool()
def create_record(name:str)->str:
    """Create a record."""
    return name

if __name__=="__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=int(os.environ["KCC_HTTP_PORT"]),
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
    )
