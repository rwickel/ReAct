from openai import OpenAI
from typing import Dict, Any
from typing import  List, Dict, Optional, Union, Any
import inspect

class LLM:
    def __init__(
        self,
        model: str = "phi4:14b",
        temperature: float = 0.1,
        top_p: float = 0.5,
        max_completion_tokens: int = 1000,
        client = OpenAI(base_url='http://localhost:11434/v1/', api_key='ollama', timeout=20.0),
    ):
        """
        Initialize the LLM class.

        Args:
            model (str): The model to use for completions. Default is "phi4:14b".
            temperature (float): Sampling temperature. Default is 0.1.
            top_p (float): Nucleus sampling parameter. Default is 0.5.
            max_completion_tokens (int): Maximum number of tokens to generate. Default is 1000.
            client (Optional[object]): The client object to interact with the API. Default is None.
        """
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_completion_tokens = max_completion_tokens
        self.client = client

    def get_chat_completion(
        self,
        messages: List[Dict[str, str]],
        functions: Optional[List[object]] = None,
        stream: bool = False,
        response_format: Optional[Dict[str, str]] = None,
    ) -> Union[Dict, object]:
        """
        Get a chat completion from the model.

        Args:
            messages (List[Dict[str, str]]): List of message dictionaries with "role" and "content".
            functions (Optional[List[object]]): List of functions to include in the request. Default is None.
            stream (bool): Whether to stream the response. Default is False.
            response_format (Optional[Dict[str, str]]): Format of the response. Default is None.

        Returns:
            Union[Dict, object]: The completion response from the model.
        """
        if not self.client:
            raise ValueError("Client is not initialized. Please provide a client object.")

        # Convert functions to JSON if provided
        tools = [self.function_to_json(f) for f in functions] if functions else []

        # Filter valid messages
        messages = [
            msg for msg in messages
            if isinstance(msg, dict)
            and "role" in msg
            and "content" in msg
            and isinstance(msg["content"], str)
            and msg["content"].strip()
        ]

        # Prepare parameters for the API call
        create_params = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": messages,
            "max_tokens": self.max_completion_tokens,
            "top_p": self.top_p,
            "stream": stream,
        }

        if response_format:
            create_params["response_format"] = response_format

        if tools:
            create_params["tools"] = tools

        # Make the API call
        return self.client.chat.completions.create(**create_params)
    
    def function_to_json(self, func) -> dict:
        """
        Converts a Python function into a JSON-serializable dictionary
        that describes the function's signature, including its name,
        description, and parameters.

        Args:
            func: The function to be converted.

        Returns:
            A dictionary representing the function's signature in JSON format.
        """
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
            type(None): "null",
        }

        try:
            signature = inspect.signature(func)
        except ValueError as e:
            raise ValueError(
                f"Failed to get signature for function {func.__name__}: {str(e)}"
            )

        parameters = {}
        for param in signature.parameters.values():
            try:
                param_type = type_map.get(param.annotation, "string")
            except KeyError as e:
                raise KeyError(
                    f"Unknown type annotation {param.annotation} for parameter {param.name}: {str(e)}"
                )
            parameters[param.name] = {"type": param_type}

        required = [
            param.name
            for param in signature.parameters.values()
            if param.default == inspect._empty
        ]

        return {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": func.__doc__ or "",
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required,
                },
            },
        }