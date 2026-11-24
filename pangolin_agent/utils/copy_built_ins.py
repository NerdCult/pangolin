#Copyright (c) 2026 Gene B. Denney. All Rights Reserved.

import shutil, os
from pathlib import Path

def copy_built_in_tools(target_dir: str = f'{os.getcwd()}/tools'):
    ''' helper function to copy the basic built-in tools to the folder where you manage your own tools. browse_files, read_file, fetch_page, web_search (ddgs- Duck Duck Go library) and web_search_playwright, create_skill, load_skill, unload_skill, get_utc_time. '''
    src_path = Path(F'{os.path.dirname(__file__)}/../toolboxes/tools')
    dst_path = Path(target_dir)
    dst_path.mkdir(parents=True, exist_ok=True)
    
    for file in src_path.iterdir():
        if file.is_file() and not file.stem.startswith('__'):
            print(f'copying {file.name}')
            shutil.copy2(file, dst_path)
        
    print ('some tools require extra dependencies, use pip install pangolin-agent[tools]')

def copy_built_in_power_tools(target_dir: str = f'{os.getcwd()}/tools'):
    ''' helper function to copy the built-in POWER tools to the folder where you manage your own tools. VERIFY ALL TOOL FILES BEFORE ALLOWING AND AGENT TO EXECUTE THEM. SOME ARE QUITE POWERFUL. create_tool, delete_file, write_file, run_sh '''
    src_path = Path(F'{os.path.dirname(__file__)}/../toolboxes/power_tools')
    dst_path = Path(target_dir)
    dst_path.mkdir(parents=True, exist_ok=True)
    
    for file in src_path.iterdir():
        if file.is_file() and not file.stem.startswith('__'):
            print(f'copying {file.name}')
            shutil.copy2(file, dst_path)

    print ('use power tools with caution')

def copy_built_in_skills(target_dir: str = f'{os.getcwd()}/skills'):
    ''' helper function to copy the built-in skills to the folder where you manage your own skills. Built-in skills are mostly for Pangolin development or demo'''
    src_path = Path(F'{os.path.dirname(__file__)}/../skill_managers/skills')
    dst_path = Path(target_dir)
    dst_path.mkdir(parents=True, exist_ok=True)
    
    for file in src_path.iterdir():
        if file.is_file() and not file.stem.startswith('__'):
            print(f'copying {file.name}')
            shutil.copy2(file, dst_path)