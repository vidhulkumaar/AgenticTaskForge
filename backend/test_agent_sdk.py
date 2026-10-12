import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, tool, create_sdk_mcp_server

@tool("search_transcripts", "Search Lenny's Podcast transcript knowledge base.", {"query": str})
async def search_transcripts_tool(args):
    return {"content": [{"type": "text", "text": f"Found results for {args['query']}"}]}

async def main():
    server = create_sdk_mcp_server("lenny_db", tools=[search_transcripts_tool])
    options = ClaudeAgentOptions(
        model="claude-3-5-sonnet-20241022",
        mcp_servers={"lenny": server},
        allowed_tools=["search_transcripts"],
        system_prompt="You are a helpful assistant.",
        max_turns=4
    )
    
    try:
        async for msg in query(prompt="hello", options=options):
            print(type(msg))
    except Exception as e:
        print(f"Error: {type(e)} - {e}")

if __name__ == "__main__":
    asyncio.run(main())
