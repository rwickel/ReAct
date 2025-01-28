
from datetime import datetime
import pytz
import json
import io
import contextlib
from repl.util import pretty_print_messages, function_to_json
from ddg import Duckduckgo
from repl.types import Result, Agent

def get_weather(location, time="now"):
    """Get the current weather in a given location. Location MUST be a city."""    
    return json.dumps({"location": location, "temperature": "65", "time": time})

def date(timezone='UTC'):
    """
    Get the current date and time. If a timezone is specified,
    return the time in that timezone.

    Parameters:
    - timezone (str): The timezone for which to get the current time (e.g., 'America/New_York').

    Returns:
    - str: Formatted current date and time.
    """
    if timezone:
        # Get the current time in the specified timezone
        tz = pytz.timezone(timezone)
        current_datetime = datetime.now(tz)
    else:
        # Get the current date and time in the local timezone
        current_datetime = datetime.now()

    return current_datetime.strftime("%B %d, %Y Time: %H:%M:%S")

def web_search(query: str) -> str:
    """
    Performs a web search for the given query using DuckDuckGo and retrieves a list of search results.

    Args:
        query (str): The search query.

    Returns:
        str: A custom string representation of the search results or an error message.
    """
    try:
        result = Result()        
                
        ddg_api = Duckduckgo()
        # Perform the search using DuckDuckGo
        web_results = ddg_api.search(query)

        # Check if the search was successful
        if not web_results.get('success', False):
            return "Error: Search was not successful."

        # Extract the search results from the 'data' field
        result_list = web_results.get('data', [])

        # Convert the list of results to a custom string format
        output = []
        for res in result_list:
            output.append(f"Title: {res.get('title', 'N/A')}")
            output.append(f"URL: {res.get('url', 'N/A')}")
            output.append(f"Description: {res.get('description', 'N/A')}")
            output.append("-" * 40)
        
        result.value ="\n".join(output) 

    except Exception as e:
        # Return a custom error message
        result.value =  f"An error occurred: {str(e)}"
        result.error = True

    finally:
        return result    
    
    # Define actual functions with type hints and docstrings
def count_letters(word: str, letter: str) -> int:
    """Count occurrences of a letter in a word.
    
    Args:
        word: The text to analyze (required)
        letter: The character to count (required)
    """
    return word.count(letter)

def calculate_expression(expression: str) -> float:
    """Evaluate mathematical expressions.
    
    Args:
        expression: The arithmetic expression to calculate (required)
    """
    return eval(expression)  # In practice, use a safe evaluator

def ask_user(query: str):
    """
    Prompts the user with a query and returns their input.

    Args:
        query (str): The question or prompt to display to the user.

    Returns:
        str: The user's input as a string.
    """  
    result = Result()
    result.value = query
    result.finish = True # Finish the conversation
    return result


def write_code(code: str):
    """
    Writes code to a temporal file which can replace existing code and returns the file path.

    Args:
        code (str): The code to write to the file.

    Returns:
        str: The file path where the code was written.
    """
    file_path = "code_temp.py"
    with open(file_path, "w") as file:
        file.write(code)
    return file_path
