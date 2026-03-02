from .open_app import OpenAppSkill
from .open_url import OpenUrlSkill
from .run_shell import RunShellSkill


def build_skills(execute: bool = False):
    return {
        "open_app": OpenAppSkill(execute=execute),
        "open_url": OpenUrlSkill(execute=execute),
        "run_shell": RunShellSkill(execute=execute),
    }