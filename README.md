# ReAct Agent with OpenAI Integration

This project implements a ReAct (Reasoning and Acting) agent that interacts with an OpenAI-compatible API to perform tasks using a set of predefined tools. The agent follows a cycle of thinking, acting, observing, and reflecting to solve problems or answer questions.

---

## Features

- **ReAct Loop**: The agent cycles through the steps of thinking, acting, observing, and reflecting to iteratively solve problems.
- **Tool Integration**: The agent can use predefined tools such as web search, weather lookup, date retrieval, mathematical calculations, and more. Tools can be easily extended or customized.
- **OpenAI API Integration**: The agent communicates with an OpenAI-compatible API to generate responses and actions, leveraging the power of large language models (LLMs).
- **Streaming Responses**: The agent supports streaming responses for real-time interaction, providing feedback to users as it generates outputs.
- **Error Handling**: The agent handles errors gracefully by logging issues, appending them to the conversation history, and retrying actions if necessary.
- **History Summarization**: The agent summarizes conversation history to retain only relevant messages (e.g., user queries and final assistant observations).
- **Customizable Workflow**: Steps and prompts can be tailored for specific workflows, enabling use cases in various domains like customer support, research, or task automation.

---

## Think-Action-Observation-Reflection Approach

The agent implements the **Think-Action-Observation-Reflection (TAOR)** methodology for decision-making and task execution:

1. **Think**: The agent analyzes the situation, formulates hypotheses, and determines what action to take next.
2. **Action**: Executes the selected action, such as calling a tool or generating a query.
3. **Observation**: Collects and processes the output of the action to update its knowledge.
4. **Reflection**: Evaluates the progress, checks for task completion, and plans the next steps.

This iterative process ensures structured reasoning and adaptability in dynamic environments.

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/react-agent.git
   cd react-agent
