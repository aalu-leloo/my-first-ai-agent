import os
import json
import subprocess
import requests
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Optional

load_dotenv()

client = OpenAI(
    api_key="AQ.Ab8RN6LebJy08nn6QKwjag8g0pAD2-oKtfkhHb5HKRX-G2l8yA",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)


def run_command(cmd: str):
    result=os.system(cmd)
    return result#this is a toll via which i can run any command on my system
    
   


def get_weather(city: str):
    try:
        r = requests.get(f"https://wttr.in/{city.lower()}?format=%C+%t", timeout=10)
    except requests.RequestException:
        return "something went wrong"
    if r.status_code == 200:
        return f"the weather in {city} is {r.text.strip()}"
    return "something went wrong"


available_tools = {
    "get_weather": get_weather,
    "run_command": run_command,
}

system_query = """
You are an expert AI assistant that resolves user queries using chain of thought.
You work in PLAN, TOOL and OUTPUT steps.
First PLAN what needs to be done. The PLAN can have multiple steps.
You can call a tool from the available tools if required.
After a TOOL step, wait for an OBSERVE message, which is the tool's output.
Once enough planning is done, give the final OUTPUT.

RULES:
- Reply with exactly one valid JSON object per turn, nothing else.
- Run only one step at a time.
- Sequence: PLAN (one or more times), optionally TOOL, then OUTPUT.
- The user's system is Windows, so use Windows (cmd) commands only.

OUTPUT JSON FORMAT:
{"step": "PLAN" | "TOOL" | "OUTPUT", "content": "string", "tool": "string", "input": "string"}

AVAILABLE TOOLS:
- get_weather: takes a city name as a string and returns the current weather of that city.
- run_command: takes a Windows command as a string, runs it on the user's system and returns the output.

EXAMPLE:
User: What is the weather of Delhi?
{"step": "PLAN", "content": "The user wants the weather of Delhi."}
{"step": "PLAN", "content": "I have a get_weather tool for this."}
{"step": "TOOL", "tool": "get_weather", "input": "delhi"}
(you will then receive) {"step": "OBSERVE", "tool": "get_weather", "output": "Cloudy +20C"}
{"step": "PLAN", "content": "I got the weather of Delhi."}
{"step": "OUTPUT", "content": "The current weather in Delhi is cloudy at 20 degrees Celsius."}
"""


class MyOutputFormat(BaseModel):
    step: str = Field(..., description="the id of step. example: PLAN, OUTPUT, TOOL")
    content: Optional[str] = Field(None, description="the optional string content")
    tool: Optional[str] = Field(None, description="the id of tool to call")
    input: Optional[str] = Field(None, description="the input params for the tool")


message_history = [{"role": "system", "content": system_query}]

while True:
    user_query = input("> ")
    message_history.append({"role": "user", "content": user_query})

    while True:
        try:
            response = client.chat.completions.parse(
                model="gemini-flash-lite-latest",
                response_format=MyOutputFormat,
                messages=message_history,
            )
        except Exception as e:
            print("API error:", e)
            break

        raw_result = response.choices[0].message.content
        parsed_result = response.choices[0].message.parsed

        if parsed_result is None:
            print("Could not parse model response:", raw_result)
            break

        message_history.append({"role": "assistant", "content": raw_result})
        step = parsed_result.step.upper()

        if step == "PLAN":
            print(parsed_result.content)
            # the next request must not end on an assistant turn
            message_history.append(
                {"role": "user", "content": "Continue with the next step."}
            )
            continue

        if step == "TOOL":
            tool_name = parsed_result.tool
            tool_input = parsed_result.input
            print(f">> {tool_name}({tool_input})")

            if tool_name in available_tools:
                tool_response = available_tools[tool_name](tool_input)
            else:
                tool_response = f"unknown tool: {tool_name}"
            print(f">>> {tool_response}")

            message_history.append({
                "role": "user",
                "content": json.dumps({
                    "step": "OBSERVE",
                    "tool": tool_name,
                    "input": tool_input,
                    "output": tool_response,
                }),
            })
            continue

        if step == "OUTPUT":
            print(parsed_result.content)
            break

        print("Unexpected response:", raw_result)
        break