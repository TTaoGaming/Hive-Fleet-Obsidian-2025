from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_anthropic import ChatAnthropic

# Dummy LLM for demo (replace with your API key for real use)
# llm = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0, api_key="your_api_key_here")
# For now, use a mock function to simulate without API
def mock_llm(messages: list[BaseMessage]) -> str:
    last_msg = messages[-1].content
    if "plan" in last_msg.lower():
        return "Plan: Break task into steps 1-3."
    elif "execute" in last_msg.lower():
        return "Executed step 1. Complete? Yes."
    return "Task done."

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    step_count: int

def planner_node(state: State) -> State:
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a planner. Create a simple plan for the task."),
        MessagesPlaceholder(variable_name="messages"),
    ])
    # chain = prompt | llm  # Real LLM
    response = mock_llm(state["messages"])
    return {"messages": [HumanMessage(content=response)], "step_count": state.get("step_count", 0)}

def executor_node(state: State) -> State:
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an executor. Simulate executing the plan."),
        MessagesPlaceholder(variable_name="messages"),
    ])
    # chain = prompt | llm
    step = state.get("step_count", 0) + 1
    response = f"Executed step {step}. Complete? Yes." if step >= 2 else f"Executed step {step}. Not complete yet."
    return {"messages": [HumanMessage(content=response)], "step_count": step}

def should_continue(state: State) -> str:
    last_msg = state["messages"][-1].content
    if "Complete? Yes" in last_msg:
        return END
    return "executor"

# Build graph
workflow = StateGraph(State)
workflow.add_node("planner", planner_node)
workflow.add_node("executor", executor_node)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "executor")
workflow.add_conditional_edges("executor", should_continue, {"executor": "executor", END: END})

graph = workflow.compile()

# Run example
if __name__ == "__main__":
    initial_state = {"messages": [HumanMessage(content="Plan and execute a simple task: Write a hello world script.")], "step_count": 0}
    for s in graph.stream(initial_state):
        print(s)