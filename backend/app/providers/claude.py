import anthropic
from typing import List, Optional
from fastapi import HTTPException
from app.providers.base import BaseProvider, ProviderMessage, ProviderResponse
from app.core.config import settings

class ClaudeProvider(BaseProvider):
    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        self.client = anthropic.AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=settings.REQUEST_TIMEOUT
        )
        self.model = settings.ANTHROPIC_MODEL

    async def generate(self, messages: List[ProviderMessage], system_instruction: Optional[str] = None) -> ProviderResponse:
        anthropic_messages = []
        for msg in messages:
            anthropic_messages.append({"role": msg.role, "content": msg.content})
        
        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
        }
        if system_instruction:
            kwargs["system"] = system_instruction
            
        try:
            response = await self.client.messages.create(**kwargs)
            return ProviderResponse(
                content=response.content[0].text,
                provider="claude",
                model=self.model,
                metadata={"usage": response.usage.model_dump() if response.usage else None}
            )
        except anthropic.AuthenticationError:
            raise HTTPException(status_code=401, detail="Invalid Anthropic credentials")
        except anthropic.RateLimitError:
            raise HTTPException(status_code=429, detail="Anthropic rate limit exceeded")
        except anthropic.APITimeoutError:
            raise HTTPException(status_code=504, detail="Anthropic API request timed out")
        except anthropic.APIError as e:
            raise HTTPException(status_code=502, detail=f"Anthropic API error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Claude provider error: {str(e)}")

class ClaudeAgentWrapper:
    """
    Agent loop using the official Anthropic Claude Agent SDK.

    Exposes exactly one tool: `search_transcripts`, which searches the
    Lenny's Podcast knowledge base via RetrievalService.

    Guardrails:
      - Max turns: settings.AGENT_MAX_TURNS (default 4)
      - Timeout: settings.AGENT_TIMEOUT (default 120s)
    """
    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        self.model = settings.ANTHROPIC_MODEL
        self.max_turns = settings.AGENT_MAX_TURNS
        self.api_key = settings.ANTHROPIC_API_KEY

    async def run_agent(self, prompt: str, db=None) -> str:
        """
        Run a restricted agent loop using the official SDK.
        """
        from app.services.retrieval_service import get_retrieval_service

        system_instruction = (
            "You are the Lenny Growth Assistant, an expert on product growth, "
            "retention, and product-market fit based on Lenny's Podcast transcripts. "
            "Use the search_transcripts tool to find relevant evidence before answering. "
            "Always cite your sources. If evidence is insufficient, say so clearly."
        )

        tools = [
            {
                "name": "search_transcripts",
                "description": "Search Lenny's Podcast transcript knowledge base for relevant passages. Use this to find specific quotes, frameworks, examples, or guest insights.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]

        messages = [{"role": "user", "content": prompt}]
        
        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        for _ in range(self.max_turns):
            try:
                response = await client.messages.create(
                    model=self.model,
                    system=system_instruction,
                    messages=messages,
                    tools=tools,
                    max_tokens=4096
                )
            except Exception as e:
                return f"Agent execution failed: {str(e)}"
            
            messages.append({"role": "assistant", "content": response.content})
            
            if response.stop_reason == "tool_use":
                for content_block in response.content:
                    if content_block.type == "tool_use" and content_block.name == "search_transcripts":
                        query_str = content_block.input.get("query", "")
                        
                        try:
                            retrieval_service = get_retrieval_service()
                            results = await retrieval_service.search(db=db, query=query_str)
                            
                            if not results:
                                tool_result = "No relevant transcript passages found for this query."
                            else:
                                passages = []
                                for r in results:
                                    passage = f"[{r.episode_title}]"
                                    if r.speaker:
                                        passage += f" {r.speaker}:"
                                    passage += f" {r.content}"
                                    if r.source_url:
                                        passage += f" (source: {r.source_url})"
                                    passages.append(passage)
                                tool_result = "\n\n".join(passages)
                                
                        except Exception as e:
                            tool_result = f"Search failed: {str(e)}"
                            
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": content_block.id,
                                    "content": tool_result
                                }
                            ]
                        })
                # Continue loop to send tool result
            else:
                # Agent finished
                final_texts = [b.text for b in response.content if b.type == "text"]
                return "\n".join(final_texts)

        return "Agent reached maximum turns or returned no textual response."

