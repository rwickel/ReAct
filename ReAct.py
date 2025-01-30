
import json
from typing import Dict, Any
import copy
from typing import List, Callable, Union
from jsonschema import validate, ValidationError
import inspect
from repl.tools import web_search, get_weather, date,  ask_user, write_code, find_symbol, read_url
from repl.prompts import ACTION_SCHEMA, REFLECTION_SCHEMA, SYSTEM_PROMPTS
from repl.util import process_and_print_streaming_response, function_to_json
from repl.types import Result, Agent
from datetime import datetime
from openai import OpenAI, BadRequestError, RateLimitError, AuthenticationError, Timeout, APIConnectionError
import httpx
import logging
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

logging.basicConfig(
    filename="app.log",  # Log file name
    filemode="a",        # Append mode (use "w" to overwrite)
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO   # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
)

client = OpenAI(base_url='http://localhost:11434/v1/', api_key='ollama', timeout=20.0)

__CTX_VARS_NAME__ = "context_variables"
       
class ReAct:
    def __init__(self, model="phi4:14b", context ="", temperature=0.1, top_p=0.5):             
        self.steps = ["think", "action", "observation", "reflection"]
        self.output_format = []   
        self.context: str = "",    
        self.function_map = None  
        self.model = model
        self.temperature = temperature
        self.max_completion_tokens = 2000
        self.top_p = top_p
        
    def get_chat_completion(self, messages, functions=None, stream=False, response_format=None):
        tools = [function_to_json(f) for f in functions] if functions else []

        messages = [
        msg for msg in messages
        if isinstance(msg, dict) and 
           "role" in msg and "content" in msg and 
           isinstance(msg["content"], str) and msg["content"].strip()
        ]
        
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
            create_params['tools'] = tools  

                    
        return client.chat.completions.create(**create_params)                
            
    
    def format_response(self, content: str, step: str) -> Dict[str, Any]:
        if step == "action":
            try:
                data = json.loads(content)
                validate(instance=data, schema=ACTION_SCHEMA)
                return data
            except (json.JSONDecodeError, ValidationError) as e:
                return {"error": f"Invalid action format: {str(e)}"}

        elif step == "reflection":
            try:
                data = json.loads(content)
                validate(instance=data, schema=REFLECTION_SCHEMA)
                return data
            except (json.JSONDecodeError, ValidationError) as e:
                return {"error": f"Invalid reflection format: {str(e)}"}

        # For think/observation, just return text
        return {"text": content.strip()} 

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
    
    
    def run(self,
        input:str,    
        messages: List, #history        
        tools: List = [],
        max_turns: int = 20,          
        debug: bool = True):
    
        current_step_idx = 0
        finished  = False

        # Create a mapping of function names to functions
        self.function_map = {f.__name__: f for f in tools} 
        
        input_message = [{"role": "user", "content": input}]
        
        history = copy.deepcopy(messages)
        init_len = len(messages)  

        functions = [function_to_json(f) for f in tools]    
        memory=[]
        while not finished and len(memory)  < max_turns:
        
            current_step = self.steps[current_step_idx]   
            
            system_prompt = SYSTEM_PROMPTS[current_step].format(context = self.context , tools=functions, date=datetime.now())      
            
            if memory:
                messages = [{"role": "system", "content": system_prompt}] + input_message + memory[-4:]
            else:
                messages = [{"role": "system", "content": system_prompt}] + history[-4:] + input_message 
            
            if current_step in ["action", "reflection"]:
                response_format = {"type": "json_object","json_schema": ACTION_SCHEMA if current_step == "action" else REFLECTION_SCHEMA} 
            else:
                response_format = None
        
            # Get completion from your preferred LLM API
            try:
                completion = self.get_chat_completion(messages, stream=True, response_format=response_format)
            
            except Exception as e:                
                if hasattr(e, 'message'):                    
                    yield {"error": e.message, "step": "chat"} 

                yield {"response": [] } # Yield only the new messages added to the history
                return
            
            message_content=''

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
                            yield {"content": "No Tool Result.Try again.", "step": "tool"}
                            continue  # Repeat the action step                        

                        if tool_result.finish:
                            finished = True
                            yield {"content": tool_result.value, "step": "observation"}
                            memory.append({
                                "role": "assistant",
                                "content": tool_result.value,
                                "step": "observation"
                            })
                            continue                             
                        
                        yield {"content":  tool_result.value, "step": "tool"}

                    except Exception as e:   
                        memory.append({"role": "tool", "content": e.message})
                        continue     

            current_step_idx = (current_step_idx + 1) % len(self.steps) 
        
        if len(memory) - init_len >= max_turns:
            memory.append({"role": "assistant", "content": "Can't find a solution, try again.", "step": "MaxTurns"}) 
            yield {"content":  "Can't find a solution, try again.", "step": "observation"} 
        
        yield {"response": input_message + self.summarize_history(memory[init_len:]) } # Yield only the new messages added to the history    


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



def run_react_loop(store_history=False):
    agent = ReAct(model="phi4:14b") 
    history = []    
    
    while True:
        print()  # Adds an empty line
        user_input = input("\033[91mUser\033[0m: ")        
        response =  agent.run(user_input, history, tools=[web_search, read_url, ask_user])  
        response = process_and_print_streaming_response(response)   
        
        if store_history:
            # update history 
            history.extend(response)   
        else:
            history = []     

if __name__ == "__main__":
    run_react_loop(True)    
    