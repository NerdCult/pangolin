#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import logging
from pathlib import Path
from ..core.interfaces import SkillManager

LOGGER = logging.getLogger(__name__)

class SimpleSkillManager(SkillManager):
    '''
    Implements all the Skill Manger options. 
    skills() the concatonation of the skills found.

    '''
    def __init__(self, skill_folder: str | Path = Path.cwd().joinpath('skills')):
        '''
        skill_folder: the folder path for where skill markdown files are kept
        '''
        LOGGER.info(f'__init__ {skill_folder}')
        self.skills_folder = skill_folder if isinstance(skill_folder, Path) else Path(skill_folder)
        self.skills_all = ''
        self.skills_folder.mkdir(parents=True, exist_ok=True)
        self.reload_skills()

    # load the available skills
    def reload_skills(self):
        self.skills_all = ''
        
        for path in sorted(self.skills_folder.iterdir()):
            if path.is_file() and path.suffix == '.md':
                LOGGER.debug(f'loading skill: {path.stem}')
                self.skills_all = f'{self.skills_all} \n\n{path.stem}:\n{path.read_text(encoding='utf-8')}'

        LOGGER.info('skills loaded')

    # provide the concatonation of the found skills
    def skills(self) -> str:
        return self.skills_all
