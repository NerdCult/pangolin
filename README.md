**UNDER CONSTRUCTION** — Early preview. Things will break. Feedback welcome.

**License:** This software is released under the [PolyForm Noncommercial License 1.0.0](LICENSE). You're free to use it for personal, educational, research, and non-commercial projects.

Want to use it commercially, in a product, or at scale? No problem — just reach out. I'm happy to grant **free short-term evaluation licenses** to companies for testing and prototyping, and long-term licenses can be negotiated.

### Creators & Influencers
If you're a YouTuber, TikToker, blogger, or anyone who makes tech content, feel free to build showcases, reviews, tutorials, or crazy demos with Pangolin. Just point your viewers to the repo. I'll happily provide a free license if you want one for peace of mind.

Email me at gbdenney84@gmail.com to inquire about a license (or open a GitHub issue).

For full legal terms, see the [LICENSE](LICENSE) file. Commercial use or uses outside the license always requires explicit written approval from the copyright holder (Gene B. Denney).

## Introduction
Pangolin is a AI Agent library developed with Python >= 3.14. Built to be simple and functional out-of-the-box but completely extensible and customisable. Each component implements a Python Protocol and each edge has an internal data class for normalization. The core object is the PangolinRuntime. PangolinRuntime is an orchestrator and agent loop manager, moving from one step to the next as each component finishes its responsibility. The component based design with Protocol contracts and data normalization types, means any one component (skills, memory, tools, api, guardrails) can be implemented by a developer without having to touch the rest of the life cycle.

## Quick Start: Hello Pangolin

Install with `pip install pangolin-agent`

The sample below runs a simple command-line chat interface. 
**Pangolin was intentionally kept dependency light, so you will need to install openai, anthropic, and/or google-genai as you plan to use them.**

```python
from pangolin_agent.api_providers.open_ai_provider import openai_agent_runtime
from pangolin_agent import cli
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

1. Save this as `hello_pangolin.py` (also available in the examples folder as 1_hello_pangolin_agent.py)
2. Update the URL, MODEL, and KEY
3. (Optional) Swap `openai_agent_runtime` for `anthropic_agent_runtime` if preferred or use the `1_hello_pangolin_gemini.py` from the examples folder.
4. Run it: `python hello_pangolin.py`

When you see the `USER>` prompt, type your message and hit Enter. The cli from examples will show `>>>` in green.

**Gemini offers a FREE tier API key** https://aistudio.google.com/docs/api-key if you want to test this library free of charge (and don't run local ya know).

## Runtime Options: Memory, Tools, Skills

`the 'x'_agent_runtime methods` can accept a system_prompt, memory_manager, skill_manager, toolbox, guardrail, max_tokens, and max_rounds. memory_manager defaults to `SimpleMemoryManager`, skill_manager, toolbox, and guardrail default to None. max_tokens defaults to 32,000 and max_rounds defaults to 10. 
- `SimpleMemoryManager` (in-memory with no persistence between sessions).
- `SqliteMemoryManager` uses UUIDs to create and track sessions. Passing in a UUID will load the previous session if it exists. 
- `SimpleSkillManager` loads all skill file in the skill directory (default ./skills). Use the copy_built_in_skills helper shown below to copy the built in skills.
- `AdvancedSkillManager` provides a skills menu and instructions to load, unload, and create skills (requires PangolinToolbox)
- `BasicToolbox` hardcoded to only load tools to get current time, browse/read files, and search the web. Reads from the library tools folder and does not support a custom folders directory. 
- `PangolinToolbox` reads the tools files from a specified folder (default='./tools'). supports `session aware tools` that can access the agent runtime to support tool/skill creation, skill loading and unloading, updating name/description of a chat session, etc. use the copy_built_in_tools helper (example below) to get the core tool set. use copy_built_in_power_tools to get the tools that are more capable create_tool, delete_file/write_file, run_sh, etc. **review and understand power tools before deciding to allow your agent to run them**
- `DefaultGuardrail` a minimal implementation of the guardrail Protocol. By default, it blocks run_sh, create_tool, write_file, and delete_file tool calls, or you can pass your own list[str] of blocked tools. **If you pull the power tools, I recommend using this or your own Guardrail implementation till you are comfortable with your agent.**
- `max_tokens` limit the size of the current full context before sending to the API.
- `max_rounds` limit the number of rounds the agent loop can make per single user input.

## Built-in resources

- The built-in tools provide web and file search capabilities, and update chat name and description, load/unload/create skills capabilites (when paired with supporting Skill Manager and Toolbox). **built in tools have depenencies that are not required when installing the Pangolin library. Optionally use copy_built_in_power_tools to get tools that can create new tools, run sh, write/delete files. Power tools should be used with caution and/or a Guardrail implementation.**
- The built-in skills are focused on how to use or develop with this library.
- To copy the built-in tools and skills run this script (moves them into the current working directory in tools and skills folders or you can set your own target dir, set the same directory when initializing your AdvancedSkillManager and PangolinToolbox):

```python
from pangolin_agent import copy_built_in_tools, copy_built_in_skills

copy_built_in_tools() 
copy_built_in_skills()
```


## The meta development experience

Pangolin ships with built-in skill files explaining how to develop with it. use the two copy_built_in_x functions above, and start your session with AdvancedSkillManager and PangolinToolbox, and your agent can help you understand how to develop with pangolin_agent. 