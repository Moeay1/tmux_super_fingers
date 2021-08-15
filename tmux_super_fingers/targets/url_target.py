from dataclasses import dataclass
from .target import Target
from .os_openable import OsOpenable
from tmux_super_fingers.actions import os_open_action

# @dataclass doesn't play well with @abstractmethod, hence workaraound.
# Copied from: https://github.com/python/mypy/issues/5374#issuecomment-650656381


@dataclass
class _UrlTarget(Target):
    url: str

    @property
    def file_or_url(self) -> str:
        return self.url


class UrlTarget(_UrlTarget, OsOpenable):
    def perform_primary_action(self) -> None:
        os_open_action.OsOpenAction(self).perform()
