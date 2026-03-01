from .open_app import OpenAppSkill
from .open_url import OpenUrlSkill
from .run_shell import RunShellSkill


def build_skills(execute: bool = False):
    return {
        "open_app": OpenAppSkill(),
        "open_url": OpenUrlSkill(),
        "run_shell": RunShellSkill(execute=execute),
    }