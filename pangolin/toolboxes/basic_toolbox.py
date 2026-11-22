#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import importlib, json, sys, logging
from pathlib import Path
from typing import Iterator
from ..core.interfaces.toolbox import Toolbox
from ..core.exceptions import PangolinImportError
from ..messages.tool_call_result import ToolCallResult

LOGGER = logging.getLogger(__name__)

DEFAULT_TOOLS_DIR = Path(__file__).resolve().parent.joinpath('tools')
DEFAULT_MAX_RESULTS_LENGTH = 50_000

#hard coded list based on the built-in Pangolin tools
BASIC_TOOL_SET = ['browse_files',
                  'fetch_page',
                  'web_search',
                  'read_file',
                  'get_utc_time']

class BasicToolbox(Toolbox):
    '''
    BasicToolbox is the "safe" toolbox. only loading a safe set of tools provided in the pangolin library.
    '''

    def __init__(self, max_results_length: int = DEFAULT_MAX_RESULTS_LENGTH):
        '''
        max_results_length: caps the tool result size to help control context size
        tool_list: list of tools to load, the default is a list based on the built-in tools and enable web searching, file browsing/reading. 
        '''
        LOGGER.info(f'__init__ {max_results_length}')
        self.max_results_length = max_results_length
        self.registry: dict = {}
        self.tool_set = BASIC_TOOL_SET

    # load tool_set
    def load(self):
        LOGGER.info('loading tools')
        for tool in self.tool_set:
            file = DEFAULT_TOOLS_DIR.joinpath(f'{tool}.py')
            self._load_tool(file)

        LOGGER.debug(f'tools loaded {len(self.registry)}')            

    # read and load the individual tool python file
    def _load_tool(self, file: Path):
        LOGGER.debug(f'loading tool {file}')
        spec = importlib.util.spec_from_file_location(file.stem, file)
        if spec is None or spec.loader is None:
            raise PangolinImportError(f'BasicToolbox failed to read tool spec {file}')
        try:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[file.stem] = mod
            spec.loader.exec_module(mod)
            schema = getattr(mod, "SCHEMA")
            
            if hasattr(mod, "make_session_aware_run"):
                return
            else:
                fn = getattr(mod, "run")
            self.registry[schema["name"]] = (schema, fn)
        except Exception as e:
            raise PangolinImportError(f'BasicToolbox failed to load tool {file} {e}')

    # returns the OpenAI formatted tools schems
    def schemas(self) -> list[dict]:
        return [{"type": "function", "function": s} for s, _ in self.registry.values()]

    # execute a tool's method
    def run_tool(self, name, args) -> str:
        LOGGER.debug(f'running tool {name} {args}')
        entry = self.registry.get(name)
        if not entry:
            return json.dumps({"error": f"unknown tool {name}"})
        try:
            out = json.dumps(entry[1](**args), ensure_ascii=False, default=str)
            if len(out) > self.max_results_length:
                out = out[:self.max_results_length] + f"... [TRUNCATED: result was {len(out)} chars, limit {self.max_results_length}. Request a smaller piece.]"
            return out
        except Exception as e:
            LOGGER.error(f'run_tool() returned exception {e}')
            return json.dumps({"error": f"{type(e).__name__}: {e}"})

    # handle the list[ToolCall] provided by AgentRuntime and return the ToolCallResults
    def handle_tool_calls(self, calls) -> Iterator[ToolCallResult]:
        LOGGER.info(f'handling tool calls {len(calls)}')
        for c in calls:
            out = self.run_tool(c.name, c.args)
            yield ToolCallResult(id=c.id, result=out)
