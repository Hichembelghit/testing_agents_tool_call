"""Pydantic models for structured agent output."""

from pydantic import BaseModel, Field


class TweetInfo(BaseModel):
    """A single tweet returned by the agent."""

    id: str = Field(description="Unique tweet ID")
    content: str = Field(description="Tweet text content")
    date: str = Field(description="Tweet publication date (ISO format)")
    retweets: int = Field(description="Number of retweets")
    favorites: int = Field(description="Number of favorites/likes")


class AgentResponse(BaseModel):
    """Structured response from the tweet QA agent.

    The agent will always populate these fields when answering.
    The `answer` field contains the conversational response; `count` and
    `tweets` hold the supporting data pulled from the tools.
    """

    answer: str = Field(
        description="A clear conversational answer to the user's question"
    )
    count: int = Field(
        description="Total number of matching tweets found",
    )
    tweets: list[TweetInfo] = Field(
        default_factory=list,
        description="List of matching tweets (may be empty for count-only queries)",
    )
