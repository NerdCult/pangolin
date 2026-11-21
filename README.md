**UNDER CONSTRUCTION** — Early preview. Things will break. Feedback welcome.

**License:** This software is released under the [PolyForm Noncommercial License 1.0.0](LICENSE). You're free to use it for personal, educational, research, and non-commercial projects.

Want to use it commercially, in a product, or at scale? No problem — just reach out. I'm happy to grant **free short-term evaluation licenses** to companies for testing and prototyping, and long-term licenses can be negotiated.

### Creators & Influencers
If you're a YouTuber, TikToker, blogger, or anyone who makes tech content, feel free to build showcases, reviews, tutorials, or crazy demos with Pangolin. Just point your viewers to the repo. I'll happily provide a free license if you want one for peace of mind.

Email me at gbdenney84@gmail.com to inquire about a license (or open a GitHub issue).

For full legal terms, see the [LICENSE](LICENSE) file. Commercial use or uses outside the license always requires explicit written approval from the copyright holder (Gene B. Denney).

## Introduction
Pangolin is a AI Agent library. Built to be functional out-of-the-box but completely extensible and customisable. Each component implements  Python Protocol class and each edge has an internal data class for normalization. The core object is the AgentRuntime. AgentRuntime manages recieving the user input, context building (chat history, system prompt, skills, and tools), the agent loop (api call, normalization, tool calls). 

## Quick Start: Hello Pangolin

The sample below runs a simple command-line chat interface. 


```python
from pangolin.api_providers.open_ai_provider import openai_agent_runtime
from .cli import cli

URL = 'https://api.openai.com/v1'   # or your preferred endpoint
MODEL = 'gpt-4o-mini'               # or whatever you prefer
KEY = 'your-key-here'

#Create a basic instance of AgentRuntime
# use anthropic_agent_runtime if you want to connect to their api
runtime = openai_agent_runtime(url=URL, model=MODEL, key=KEY)

#Launch the command line interface to interact with the AgentRuntime runtime. output is color-coded green -> user, red -> agent thinking, yellow -> tool calls, blue -> agent reply
cli(runtime)
```

1. Save this as `hello_pangolin_agent.py` (also available in the examples folder)
2. Update the URL, MODEL, and KEY
3. (Optional) Swap `openai_agent_runtime` for `anthropic_agent_runtime` if preferred or use the 1_hello_pangolin_gemini.py from the examples folder.
4. Run it: `python hello_pangolin.py`

When you see the `>>>` prompt, type your message and hit Enter.

**Gemini offers a FREE tier API key** https://aistudio.google.com/docs/api-key if you want to test this library free of charge (and don't run local ya know).

## Tools and Skills

`the 'x'_agent_runtime methods` can accept a system prompt, Memory Manager, Skill Manager, and a Toolbox. Memory Manager defaults to `SimpleMemoryManger`, Skill Manger, and Toolbox default to None. 
- `SimpleMemoryManger` (in-memory with no persistence between sessions).
- `SqliteMemoryManger` uses UUIDs to create and track sessions. Passing in a UUID will load the previous session if it exists. 
- `SimpleSkillManager` loads all skill file in the skill directory (default ./skills).
- `AdvancedSkillManager` provides a skills menu and instructions to load, unload, and create skills (requires AdvancedToolbox)
- `BasicToolbox` hardcoded to only load tools to get current time, browse/read files, search the web, and load/unload skills.  
- `AdvancedToolbox` adds file writing, deletion, tool creation, and skill creation. 
**USE THE ADVANCED TOOLBOX WITH CAUTION — THERE ARE NO HARD BUILT-IN GUARDRAILS.**
- the create_tool and delete_file tools are the dangerous one, if you want to not include them. (delete_file only deletes within the current working directory, but with create_tool that guardrail is readily bypassed)
- Guardrails can be implemented but are not on by default.

To copy the built-in tools and skills run this script (moves them into the current working directory in tools and skills folders or you can set your own target dir, set the same directory when initializing SkillManger and Toolbox):

```
from pangolin import copy_built_in_tools, copy_built_in_skills

copy_built_in_tools()
copy_built_in_skills()
```