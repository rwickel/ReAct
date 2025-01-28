# Third-party imports
from pydantic import BaseModel
from typing import List, Callable, Union, Optional
AgentFunction = Callable[[], Union[str, "Agent", dict]]

class Agent(BaseModel):
    name: str = "Agent"
    model: str = "mistral-nemo:latest"
    instructions: Union[str, Callable[[], str]] = "You are a helpful agent."
    functions: List[AgentFunction] = []
    tool_choice: str = None
    parallel_tool_calls: bool = True


class Agent(BaseModel):
    name: str = "Agent"
    model: str = "mistral-nemo:latest"
    instructions: Union[str, Callable[[], str]] = "You are a helpful agent."
    functions: List[AgentFunction] = []    

class Response(BaseModel):
    messages: List = []
    agent: Optional[Agent] = None
    context_variables: dict = {}


class Result(BaseModel):
    """
    Encapsulates the possible return values for an agent function.

    Attributes:
        value (str): The result value as a string.
        agent (Agent): The agent instance, if applicable.
        context_variables (dict): A dictionary of context variables.
    """
    value: str = ""
    error: bool = False
    finish: bool = False #finish the chat conversation
    repeat: bool = False # action is repeated
    agent: Optional[Agent] = None # assign a new agent
    context_variables: dict = {}