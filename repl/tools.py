
from datetime import datetime
import pytz
import json
import io
import contextlib
from ddg import Duckduckgo
from repl.types import Result, Agent
from serpapi import GoogleSearch
import requests
from bs4 import BeautifulSoup


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


def read_url(url: str) -> Result:
    """
    Fetches and extracts text content from a given webpage URL.

    Args:
        url (str): The webpage URL.

    Returns:
        Result: An object containing the extracted text or an error message.
    """
    result = Result()  # Initialize the result object

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)

        # Parse HTML content
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove unnecessary elements (scripts, styles, etc.)
        for element in soup(["script", "style", "meta", "noscript"]):
            element.extract()

        # Extract readable text
        text = soup.get_text(separator="\n", strip=True)

        # Limit output size (prevent excessively large content)
        result.value = text[:5000]  # First 5000 characters
        result.error = False

    except requests.exceptions.RequestException as e:
        result.value = f"Error fetching website: {e}"
        result.error = True

    return result


def google(query: str) -> str:
    """
    Performs a web search for the given query using SerpApi and retrieves a list of search results.

    Args:
        query (str): The search query.

    Returns:
        str: A custom string representation of the search results or an error message.
    """
    try:
        result = Result() 
        result.value = "Error: Search engine provides no results."  
        result.error = True   
        
        # Set up SerpApi parameters
        params = {
            "q": query,
            "engine": "google",
            "api_key": "YOUR_SERPAPI_KEY"  # Replace with your actual API key
        }
        
        search = GoogleSearch(params)
        web_results = search.get_dict()
        
        if "error" in web_results:
            return f"Error: {web_results['error']}"
        
        result_list = web_results.get("organic_results", [])
        
        if not result_list:
            return result["value"]
        
        output = []
        for res in result_list:
            title = res.get("title", "N/A")
            url = res.get("link", "N/A")
            description = res.get("snippet", "N/A")
            output.append(f"- **[{title}]({url})**  \n  **Description:** {description}\n")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"An error occurred: {str(e)}"



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
        result.value = "Error: Search engine provides no results."  
        result.error = True     
                
        ddg_api = Duckduckgo()
        # Perform the search using DuckDuckGo
        web_results = ddg_api.search(query)

        # Check if the search was successful
        if not web_results.get('success', False):            
            return result            

        # Extract the search results from the 'data' field
        result_list = web_results.get('data', [])

        if not result_list:
            result.repeat = True
            return result

        # Convert the list of results to a custom string format
        output = []
        for res in result_list:
            title = res.get('title', 'N/A')
            url = res.get('url', 'N/A')
            description = res.get('description', 'N/A')

            output.append(f"- **[{title}]({url})**  \n  **Description:** {description}\n")

        result.value =  "\n".join(output)
        result.error = False
        return result

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



def find_symbol(symbol_name: str) -> list:
    """
    Searches for a symbol (e.g., variable, function) across multiple files and returns its occurrences with start and end line information.
    
    Args:
        symbol_name (str): The name of the symbol to search for (e.g., variable, function name).

    Returns:
        list: A list of dictionaries with the file path (`file`), kind of symbol (`kind`), position (`range`), and the symbol's content.
        
    Example:
        [
            {"file": "src\\brake_system.c", "kind": "Function", "range": [{"line": 21, "character": 0}, {"line": 55, "character": 1}], "detail": "function definition", "content": "void BrakeSystem_Update(SensorData sensor_data) {...}"},
            {"file": "include\\brake_system.h", "kind": "Function", "range": [{"line": 46, "character": 0}, {"line": 46, "character": 48}], "detail": "function declaration", "content": "void BrakeSystem_Init(BrakeConfig config); void BrakeSystem_Update(SensorData sensor_data);"},
            {"file": "src\\main.c", "kind": "Reference", "range": [{"line": 22, "character": 4}, {"line": 22, "character": 22}], "detail": "function call", "content": "BrakeSystem_Update(sensor_data);"},
            {"file": "src\\brake_system.c", "kind": "Reference", "range": [{"line": 21, "character": 5}, {"line": 21, "character": 23}], "detail": "function reference", "content": "BrakeSystem_Update(sensor_data);"},
            {"file": "include\\brake_system.h", "kind": "Reference", "range": [{"line": 46, "character": 5}, {"line": 46, "character": 23}], "detail": "function reference", "content": "BrakeSystem_Update(sensor_data);"}
        ]
    """
    
    # Example symbol data with function occurrences
    symbol_data = [
        {
            "file": "src\\brake_system.c",
            "kind": "Function",
            "range": [{"line": 21, "character": 0}, {"line": 55, "character": 1}],
            "detail": "function definition",
            "content": "void BrakeSystem_Update(SensorData sensor_data) {\n    // Compute CRC for the sensor data\n    sensor_data.crc = CRC_Compute((uint8_t*)&sensor_data, sizeof(SensorData) - sizeof(sensor_data.crc));\n    brake_status.sensor_data = sensor_data;\n    ...}"
        },
        {
            "file": "include\\brake_system.h",
            "kind": "Function",
            "range": [{"line": 46, "character": 0}, {"line": 46, "character": 48}],
            "detail": "function declaration",
            "content": "void BrakeSystem_Init(BrakeConfig config);\nvoid BrakeSystem_Update(SensorData sensor_data);"
        },
        {
            "file": "src\\main.c",
            "kind": "Reference",
            "range": [{"line": 22, "character": 4}, {"line": 22, "character": 22}],
            "detail": "function call",
            "content": "BrakeSystem_Update(sensor_data);"
        },
        {
            "file": "src\\brake_system.c",
            "kind": "Reference",
            "range": [{"line": 21, "character": 5}, {"line": 21, "character": 23}],
            "detail": "function reference",
            "content": "BrakeSystem_Update(sensor_data);"
        },
        {
            "file": "include\\brake_system.h",
            "kind": "Reference",
            "range": [{"line": 46, "character": 5}, {"line": 46, "character": 23}],
            "detail": "function reference",
            "content": "BrakeSystem_Update(sensor_data);"
        }
    ]
    
    return symbol_data





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
