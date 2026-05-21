from typing import Any

from pydantic import BaseModel, ConfigDict


class PromptTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    version: int
    description: str | None = None
    provider: str
    model: str
    input_variables: list[str]
    system_prompt: str
    user_prompt: str
    output_format: str | None = None


class RenderedPrompt(BaseModel):
    id: str
    version: int
    provider: str
    model: str
    system_prompt: str
    user_prompt: str
    output_format: str | None = None
    variables: dict[str, Any]

