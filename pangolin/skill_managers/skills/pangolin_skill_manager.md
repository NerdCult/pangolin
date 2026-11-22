---
description: Load when writing a new SkillManager. Covers skills, reload_skills, and the optional Dynamic and SkillMaker methods. Not for using Simple or Advanced, and not for writing a tool.
---
# SkillManager

The runtime calls `skills()` once per turn and concatenates the string onto the system prompt. It never calls `load_skill`, `unload_skill`, `create_skill`, or `reload_skills`. Those are for tools or the host app.

Reference: `SimpleSkillManager` (base protocol), `AdvancedSkillManager` (SkillMaker). Built-in skill files are demos. Do not treat them as the format spec if they disagree with the parser below.

## Base protocol

```python
def skills(self) -> str: ...
def reload_skills(self) -> None: ...
```

`skills()` returns text, not a list, not a dict. Empty string is legal and means no skills.

`reload_skills` must be safe to call mid-session. AdvancedSkillManager re-reads the folder and re-resolves already loaded names. The runtime will not call it for you after `create_skill`. Your `create_skill` must.

## Tiers

Implement only the tier you need. Extra methods the runtime does not call are fine. Missing methods on a tier you claim are not.

| Protocol | Adds | Who calls it |
|---|---|---|
| SkillManager | `skills`, `reload_skills` | Runtime calls `skills`. |
| SkillManagerDynamic | `load_skill(name)`, `unload_skill(name)` | A tool or the host. Needs ToolboxAdvanced so the tool can be session-aware. |
| SkillManagerSkillMaker | `create_skill(skill_name, description, text)` | Same. |

`skills()` on a Dynamic manager should be a menu: name, description, and which tool loads or unloads. Loaded bodies go after the menu. If `skills()` dumps every body, you have written SimpleSkillManager and the load tools do nothing useful.

## File shape AdvancedSkillManager actually parses

Folder of `.md` only. Name is the file stem. Suffixes are stripped if the model passes `name.md`.

Markdown:

```markdown
---
description: one line, no newlines
---
body sent to the model when loaded
```

`create_skill` writes `name.md` with that front matter, then calls `reload_skills`. Empty name is a `ValueError`. Description is flattened to one line.

SimpleSkillManager does not parse front matter. It concatenates the raw file. A Simple-compatible manager can be that dumb. A Dynamic manager cannot, because the menu needs a description that is not the whole body.

## Session-aware tool contract

The toolbox skill owns the tool file. From this side, the tool receives the runtime and calls:

```python
session.skill_manager.load_skill(skill_name)
session.skill_manager.unload_skill(skill_name)
session.skill_manager.create_skill(skill_name, description, text)
```

Raise `KeyError` on an unknown name. The tool turns that into a string the model can read. Do not swallow it.

`load_skill` stores the body. `unload_skill` drops it. Neither should need a restart. `skills()` must reflect the change on the next turn, which it will, because the runtime calls it every turn.

The built-in skills can be copied to a new directory using the code below. Default copies to the current working directory/skills/ or you can pass in a target directory. Built-in skills are primarily focused on Pangolin development and use.

```python
from pangolin.utils import copy_built_in_skills

copy_built_in_skills()
```
## Skeleton

```python
from pangolin.core.interfaces import SkillManager

class StaticSkills(SkillManager):
    def __init__(self, text: str):
        self.text = text

    def skills(self) -> str:
        return self.text

    def reload_skills(self) -> None:
        return None
```

## Do not

Do not inject skills by writing a system ChatRecord into the memory manager. The runtime overwrites that idea every turn. Do not expect `load_skill` to run because the menu says so. A tool has to call it. Do not implement Toolbox here.
