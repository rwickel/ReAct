
import json
from typing import  List, Dict, Optional, Union, Any
import copy
from typing import List, Callable, Union
from jsonschema import validate, ValidationError
import inspect
from repl.tools import web_search, get_weather, date,  ask_user, write_code, find_symbol, read_url
from repl.prompts import ACTION_SCHEMA, REFLECTION_SCHEMA, SYSTEM_PROMPTS, PLANNER_SCHEMA, REQUIREMENTS_SCHEMA , STEP_CONFIG
from repl.util import process_and_print_streaming_response, function_to_string
from datetime import datetime
from openai import OpenAI
from repl.types import Result, Agent
import logging
from requests.exceptions import RequestException, Timeout, ConnectionError
from repl.llm import LLM


logging.basicConfig(
    filename="app.log",  # Log file name
    filemode="a",        # Append mode (use "w" to overwrite)
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO   # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
)

__CTX_VARS_NAME__ = "context_variables"

class Requirements:
    def __init__(self, **kwargs):
        self.requirements = kwargs

    def add_requirement(self, item):
        self.requirements.append(item)       

class ReAct:
    def __init__(self, llm=LLM(), context="" , step_config=STEP_CONFIG):
        """
        Initializes the ReAct agent with configurable steps, system prompts, and response schemas.

        Args:
            model (str): The LLM model to use.
            context (str): Additional context for the agent.
            temperature (float): Sampling temperature for responses.
            top_p (float): Nucleus sampling parameter.
            step_config (dict): Dictionary defining steps, each with a system prompt and schema.
        """
        self.steps = list(step_config.keys()) if step_config else ["think", "action", "observation", "reflection"]
        self.step_config = step_config or {}
        self.context = context    
        self.function_map = None  
        self.llm = llm

    def format_response(self, content: str, step: str) -> Dict[str, Any]:
        """
        Formats the response based on the step and its corresponding schema.
        
        Args:
            content (str): The raw response content from the model.
            step (str): The current step (e.g., "action", "reflection").

        Returns:
            Dict[str, Any]: A formatted response, including parsed JSON if applicable.
        """
        if step not in self.step_config:
            return {"error": f"Unknown step: {step}", "text": content.strip()}

        # Get schema for the step (if any)
        schema = self.step_config[step].get("schema")

        if schema:
            try:
                # Parse and validate JSON response
                data = json.loads(content)
                validate(instance=data, schema=schema)
                return data
            except json.JSONDecodeError:
                return {"error": f"Invalid JSON format for step: {step}", "raw_content": content}
            except ValidationError as e:
                return {"error": f"Schema validation failed for step: {step}", "details": str(e)}

        # If no schema is provided, return plain text
        return {"text": content.strip()}   

    def get_step_prompt_and_schema(self, step):
        """Fetches the system prompt and schema for a given step."""
        config = self.step_config.get(step, {})
        return config.get("prompt", ""), config.get("schema", None)

    
    def handle_tool_calls(self, action: Dict[str, Any]):
        """
        Executes an action by looking up the corresponding function in the function map.

        Args:
            action (Dict[str, Any]): A dictionary containing the action type and parameters.

        Returns:
            Dict[str, str]: A dictionary with "error" and "result" keys.
        """           
        try:
            result = Result()
            func = self.function_map.get(action["action"])
            if not func:
                result.value = f"Error: Unknown action {action['action']}"
                result.repeat = True 
                result.error = True
                return result
                       
            return func(**action["parameters"])
        
        except Exception as e:           
            result.error = True
            result.value = f"Error executing action: {str(e)}"
            result.repeat = True            
    
    def handle_function_result(self, result) -> Result:
        match result:
            case Result(value=value, error=error, finish=finish, repeat=repeat, agent=agent, context_variables=context_variables):
                return Result(
                        value=value,
                        error=error,
                        finish=finish,
                        repeat=repeat,
                        agent=agent,
                        context_variables=context_variables,
                    )

            case Agent() as agent:
                return Result(
                    value=json.dumps({"assistant": agent.name}),
                    agent=agent,
                )
            case _:
                try:
                    return Result(value=str(result))
                except Exception as e:
                    error_message = f"Failed to cast response to string: {result}. Make sure agent functions return a string or Result object. Error: {str(e)}"                    
                    raise TypeError(error_message)

    def summarize_history(self, history):
        """
        Summarizes the history to include only relevant messages.
        Includes:
            - All messages with role='user'
            - Messages with role='assistant' where step='observation'
        """
        # Filter history based on the criteria
        # Find the last observation message
        last_observation = next(
            (message for message in reversed(history) if message["role"] == "assistant" and message.get("step") == "observation"),
            None
        )
        return [last_observation]

    def execute(self, input_str, messages, tools=[], max_turns=20, debug=True):
        current_step_idx = 0
        finished = False

        # Create a function map for available tools
        self.function_map = {f.__name__: f for f in tools} 
        
        input_message = [{"role": "user", "content": input_str}]
        history = copy.deepcopy(messages)
        memory = []
        
        while not finished and len(memory) < max_turns:
            current_step = self.steps[current_step_idx]
            system_prompt, response_schema = self.get_step_prompt_and_schema(current_step)
            
            # Format the system prompt   
            if "{tools}" in system_prompt: 
                functions = [function_to_string(f) for f in tools]   
                system_prompt = system_prompt.format( tools=functions)  

            response_format = {"type": "json_object", "json_schema": response_schema} if response_schema else None

            # Construct messages
            messages = [{"role": "system", "content": system_prompt}] + history + input_message + memory

            try:
                completion = self.llm.get_chat_completion(messages, stream=True, response_format=response_format)
            except Exception as e:
                yield {"error": str(e), "step": "chat"}
                return
            
            message_content = ""
            for chunk in completion:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield {"content": delta.content, "step": current_step}
                    message_content += delta.content

            memory.append({"role": "assistant", "content": message_content, "step": current_step})

            # Process the response
            response = self.format_response(message_content, current_step)

            match current_step:
                case "reflection":
                    if response.get("done", False):
                        finished = True
                        continue
                case "action":
                    try:
                        result = self.handle_tool_calls(response)
                        tool_result = self.handle_function_result(result)
                        
                        memory.append({
                            "role": "tool",
                            "content": tool_result.value,
                            "step": current_step
                        })
                        
                        if tool_result.repeat:
                            yield {"content": "No Tool Result. Try again.", "step": "tool"}
                            continue

                        if tool_result.finish:
                            finished = True
                            yield {"content": tool_result.value, "step": "observation"}
                            memory.append({
                                "role": "assistant",
                                "content": tool_result.value,
                                "step": "observation"
                            })
                            continue

                        yield {"content": tool_result.value, "step": "tool"}

                    except Exception as e:
                        memory.append({"role": "tool", "content": str(e)})
                        continue

            current_step_idx = (current_step_idx + 1) % len(self.steps)

        yield {"response": input_message + self.summarize_history(memory)}


def run_react_loop(store_history=False):
    agent = ReAct(context="AI assistant for engineering tasks") 
    history = []    
    
    while True:
        print()  # Adds an empty line
        user_input = input("\033[91mUser\033[0m: ")     
         
        response =  agent.execute(user_input , history, tools=[ web_search, write_code, ask_user])  
        response = process_and_print_streaming_response(response)   
        
        if store_history:
            # update history 
            history.extend(response)   
        else:
            history = []     

if __name__ == "__main__":
    run_react_loop(True)    
    