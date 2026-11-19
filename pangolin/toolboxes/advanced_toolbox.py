#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import importlib, json, os, sys, logging
from pathlib import Path
from typing import Iterator
from ..messages import ToolCallResult
from ..core.interfaces.toolbox import ToolboxAdvanced, AgentRuntime
from ..core.exceptions import PangolinImportError

LOGGER = logging.getLogger(__name__)

DEFAULT_MAX_RESULTS_LENGTH = 50_000

class AdvancedToolbox(ToolboxAdvanced):
    ''' 
    Implements ToolboxAdvanced which allows it to create new tools if a create_tool tool is present.
    The default tools_dir is the current working directory + /tools when the toolbox initiallizes.
    pangolin.copy_built_in_tools() will copy the built in tools to the current working directory + /tools.
    '''
    def __init__(self, tools_folder: str = f'{os.getcwd()}/tools', max_results_length: int = DEFAULT_MAX_RESULTS_LENGTH):
        '''
        tools_folder: the folder where tool files are kepy
        max_results_length: caps the max result length to help control context size
        '''
        LOGGER.info(f'__init__ {tools_folder} {max_results_length}')
        self.tools_folder: str = tools_folder
        self.max_results_length = max_results_length
        self.registry: dict = {}
        Path(tools_folder).mkdir(parents=True, exist_ok=True)

    # Toolbox advanced is designed to support session aware tools that allow the agent to interact with its own AgentRuntime. This must be set before loading tools as session aware tools can not be loaded
    def set_session(self, session: AgentRuntime):
        LOGGER.info('session set')
        self.session = session

    # iterate over the available tool filess and call _load_tool()
    def load(self):
        LOGGER.info('loading tools')
        for file in Path(self.tools_folder).glob('*.py'):
            if file.stem.startswith('__'):
                continue
            self._load_tool(file)     

        LOGGER.debug(f'tools loaded {len(self.registry)}')       

    # read in the tool's Python file and loads the tool to self.registry
    def _load_tool(self, file: Path):
        LOGGER.debug(f'loading tool {file}')
        spec = importlib.util.spec_from_file_location(file.stem, file)
        if spec is None or spec.loader is None:
            raise PangolinImportError(f'AdvancedToolbox failed to read tool spec {file}')
        try:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[file.stem] = mod
            spec.loader.exec_module(mod)
            schema = getattr(mod, "SCHEMA")

            # session aware files have a special method for creating the actual tool execution function
            if hasattr(mod, "make_session_aware_run"):
                fn = getattr(mod, "make_session_aware_run")(self.session)
            else:
                fn = getattr(mod, "run")
            self.registry[schema["name"]] = (schema, fn)
        except Exception as e:
            LOGGER.error(f'failed to load tool {file} {e}')
            raise PangolinImportError(f'AdvancedToolbox failed to load tool {file} {e}')

    # returns the OpenAI spec tool schemas
    def schemas(self):
        return [{"type": "function", "function": s} for s, _ in self.registry.values()]

    # creates a new tool file and loads it to the registry. can be called from an external application or from a session aware tool
    def create_tool(self, tool_name, code):
        LOGGER.info(f'creating tool {tool_name}')
        LOGGER.debug(code)
        try:
            tool_file_path = f'{self.tools_folder}/{tool_name}.py'
            with open(tool_file_path, 'w') as tool_file:
                tool_file.write(code)
            self._load_tool(Path(tool_file_path))
            return f'tool, {tool_name}, created '
        except Exception as e:
            text = f'tool, {tool_name}, could not be created {e}'
            LOGGER.error(text)
            return text

    # executes a tools function 
    def run_tool(self, name, args) -> str:
        LOGGER.debug(f'running tool {name} {args}')
        entry = self.registry.get(name)
        if not entry:
            return json.dumps({"error": f"unknown tool {name}"})
        try:
            out = json.dumps(entry[1](**args), ensure_ascii=False, default=str)
            # cap to the max result length
            if len(out) > self.max_results_length:
                out = out[:self.max_results_length] + f"... [TRUNCATED: result was {len(out)} chars, limit {self.max_results_length}. Request a smaller piece.]"
            return out
        except Exception as e:
            LOGGER.error(f'run_tool hit and exception {e}')
            return json.dumps({"error": f"{type(e).__name__}: {e}"})

    # handle the tool calls provided from the AgentRuntime and returns the ToolCallResults
    def handle_tool_calls(self, calls) -> Iterator[ToolCallResult]:
        LOGGER.info(f'handling tool calls {len(calls)}')
        for c in calls:
            out = self.run_tool(c.name, c.args)
            yield ToolCallResult(id=c.id, result=out)
