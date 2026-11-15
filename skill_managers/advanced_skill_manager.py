#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import json, os, logging
from pathlib import Path
from ..core.interfaces import SkillManagerSkillMaker

LOGGER = logging.getLogger(__name__)

SKILL_SUFFIXES = ('.md', '.json')

def skill_name_of(skill_name: str) -> str:
    """Normalize a skill name: drop any directory part and a known suffix."""
    name = Path(skill_name).name
    for suffix in SKILL_SUFFIXES:
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name

def parse_skill(path: Path) -> tuple[str, str]:
    """Return (description, text) for a .md (front matter) or .json skill."""
    raw = path.read_text(encoding='utf-8').strip()
    if path.suffix == '.json':
        data = json.loads(raw)
        return data['description'], data['text']

    description, body = '', raw
    parts = raw.split('---', 2)
    if raw.startswith('---') and len(parts) == 3:
        _, header, body = parts
        for line in header.strip().splitlines():
            key, _, value = line.partition(':')
            if key.strip() == 'description':
                description = value.strip()
    return description, body.strip()

class AdvancedSkillManager(SkillManagerSkillMaker):
    '''
    Implements all the Skill Manager options. 
    skills() returns a menu of available skill names and descriptions and how to use tools to load and unload skills as well as create new skills.

    '''
    def __init__(self, skill_folder: str = f'{os.getcwd()}/skills', menu_preamble: str | None = None):
        '''
        skill_folder: the folder path where skill markdown files can be found.
        menu_preamble: if None, one is set internally to a default explaination of the skills menau provided and how to load, unload, and create skills (requires ToolboxAdvanced implementation).
        skill menu is created on reload_skills from file names and the description header in the file.
        available skills are tracked in one set and appended after the skills menu.
        loaded skills are tracked in another set set and the full skill is appended after available skills
        '''
        LOGGER.info(f'__init__ {skill_folder} {menu_preamble}')
        self.skills_folder = Path(skill_folder)
        self.menu_preamble: str = menu_preamble or 'Provided below are the available skills in this environment. To have one loaded into the context use the load_skill tool providing the name of the skill to load. Use unload_skill if a skill is no longer needed. Use create_skill to create a new skill; these can track user preferences, notes about a long running project of the user, or guides for performing tasks that may need to be repeated. '
        self.available: dict[str, Path] = {}  # name -> file
        self.menu: str = ''
        self.loaded_skills: dict[str, str] = {}
        Path(skill_folder).mkdir(parents=True, exist_ok=True)
        self.reload_skills()

    # clear current skill meny and available skills,, read and parse the skills markdown files
    def reload_skills(self):
        self.available = {}
        lines = []
        self.menu = ''
        
        for path in self.skills_folder.iterdir():
            if path.suffix in SKILL_SUFFIXES:
                self.available[path.stem] = path
        for name, path in self.available.items():
            lines.append(f'{name} = {parse_skill(path)[0]}')
        self.menu = '\n'.join(lines)

        LOGGER.info('skills loaded')

    # provide the skill menu preamble + menu + loaded skills
    def skills(self) -> str:
        loaded = ''.join(f'\n {name}: {text}' for name, text in self.loaded_skills.items())
        return f'{self.menu_preamble}\n available skills:\n{self.menu}\n loaded skills:{loaded}'

    # resolve skill name in case the model is inconsistent with using a file extension
    def _resolve(self, skill_name: str) -> str:
        name = skill_name_of(skill_name)
        if name not in self.available:
            raise KeyError(f'unknown skill: {skill_name}')
        return name

    # load a skill's full text to be sent to the LLM. can be called by external application or context aware tool
    def load_skill(self, skill_name: str):
        LOGGER.info(f'skill loading {skill_name}')
        name = self._resolve(skill_name)
        self.loaded_skills[name] = parse_skill(self.available[name])[1]
        LOGGER.debug(f'skill loaded {skill_name}')

    # unload a skill's full text to stop senging to the LLM. can be called by external application or context aware tool
    def unload_skill(self, skill_name: str):
        LOGGER.info(f'skill unloading {skill_name}')
        self.loaded_skills.pop(self._resolve(skill_name))
        LOGGER.debug(f'skill unloaded {skill_name}')

    # create a skill markdown file and trigger a skill reload. can be called by external application or context aware tool
    def create_skill(self, skill_name: str, description: str, text: str):
        LOGGER.info(f'creating skill {skill_name}')
        LOGGER.debug(f'{description} {text}')
        name = skill_name_of(skill_name)
        if not name:
            raise ValueError('skill_name must not be empty')
        # the description lives on one front matter line
        description = ' '.join(description.split())
        (self.skills_folder / f'{name}.md').write_text(
            f'---\ndescription: {description}\n---\n{text}\n', encoding='utf-8')
        LOGGER.debug(f'skill created {skill_name}')
        self.reload_skills()
