**UNDER CONSTRUCTION** — Early preview. Things will break. Feedback welcome.

**License:** This software is released under the [PolyForm Noncommercial License 1.0.0](LICENSE). You're free to use it for personal, educational, research, and non-commercial projects.

Want to use it commercially, in a product, or at scale? No problem — just reach out. I'm happy to grant **free short-term evaluation licenses** to companies for testing and prototyping, and long-term licenses can be negotiated.

### Creators & Influencers
If you're a YouTuber, TikToker, blogger, or anyone who makes tech content, feel free to build showcases, reviews, tutorials, or crazy demos with Pangolin. Just point your viewers to the repo. I'll happily provide a free license if you want one for peace of mind.

Email me at gbdenney84@gmail.com to inquire about a license (or open a GitHub issue).

For full legal terms, see the [LICENSE](LICENSE) file. Commercial use or uses outside the license always requires explicit written approval from the copyright holder (Gene B. Denney).

## Introduction
Pangolin is a AI Agent library developed with Python >= 3.14. Built to be functional out-of-the-box but completely extensible and customisable. Each component implements a Python Protocol and each edge has an internal data class for normalization. The core object is the PangolinRuntime. PangolinRuntime is an orchestrator and agent loop manager, moving from one step to the next as each component finishes is responsibility. The component based design with Protocol contracts and data normalization types, means any one component (skills, memory, tools, api) can be implemented by a developer without having to touch the rest of the life cycle.

## Quick Start: Hello Pangolin

Until I get it pushed up for pip install you can git clone > cd ./pangolin > python -m pip install -e . and it will be treated like an installed package.

The sample below runs a simple command-line chat interface. 
**Pangolin was intentionally kept dependency light, so you will need to install openai, anthropic, and/or google-genai as you plan to use them.**

```python
from pangolin.api_providers.open_ai_provider import openai_agent_runtime
from pangolin import cli
# from cli import cli # use the cli.py from the examples folder for color coded output and async examples. (requires colorama and pynput)

#Create a basic instance of AgentRuntime
# use anthropic_agent_runtime if you want to connect to their api
session = openai_agent_runtime(
    url='https://api.openai.com/v1',   
    model='gpt-4o-mini',              
    key='your-key-here')

#Launch the command line interface to interact with the AgentRuntime runtime. See the examples to add persistent memory, skills, tools, and guardrails
cli(session)
```

1. Save this as `hello_pangolin_agent.py` (also available in the examples folder)
2. Update the URL, MODEL, and KEY
3. (Optional) Swap `openai_agent_runtime` for `anthropic_agent_runtime` if preferred or use the `1_hello_pangolin_gemini.py` from the examples folder.
4. Run it: `python hello_pangolin.py`

When you see the `USER>` prompt, type your message and hit Enter. the cli from examples will show `>>>` in green.

**Gemini offers a FREE tier API key** https://aistudio.google.com/docs/api-key if you want to test this library free of charge (and don't run local ya know).

## Tools and Skills

`the 'x'_agent_runtime methods` can accept a system prompt, Memory Manager, Skill Manager, and a Toolbox. Memory Manager defaults to `SimpleMemoryManger`, Skill Manger, and Toolbox default to None. 
- `SimpleMemoryManger` (in-memory with no persistence between sessions).
- `SqliteMemoryManger` uses UUIDs to create and track sessions. Passing in a UUID will load the previous session if it exists. 
- `SimpleSkillManager` loads all skill file in the skill directory (default ./skills).
- `AdvancedSkillManager` provides a skills menu and instructions to load, unload, and create skills (requires PangolinToolbox)
- `BasicToolbox` hardcoded to only load tools to get current time, browse/read files, search the web, and load/unload skills.  
- `PangolinToolbox` adds file writing, deletion, tool creation, and skill creation. 
**USE DefaultGuardrail WITH PangolinToolbox UNTIL YOU ARE READY TO SET YOUR OWN GUARDRAILS. PangolinToolbox CAN CREATE IT'S OWN TOOLS AND ACCESS 'SESSION AWARE TOOLS' THAT HAVE ACCESS TO THE AGENT RUNTIME.**
- `DefaultGuardrails` a minimal implementation of the guardrail Protocol. I blocks create_tool and delete_file tool calls. **strongly recommend using this till you are comfortable with your agent.**

## Built-in resources

The built-in tools provide web and file search capabilities, load/unload/create skills capabilites (when paired with AdvancedSkillManager), and the ability to delete files and create tools (tool creation requires a ToolboxAdvanced instance) 
The built-in skills are focused on how to use or develop with this library
To copy the built-in tools and skills run this script (moves them into the current working directory in tools and skills folders or you can set your own target dir, set the same directory when initializing your SkillManager and Toolbox):

```
from pangolin import copy_built_in_tools, copy_built_in_skills

copy_built_in_tools()
copy_built_in_skills()
```