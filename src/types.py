from dataclasses import dataclass
import io
from typing import ClassVar

type ExitCode = int


@dataclass(frozen=True, slots=True)
class Commit:
    sha: str
    COMMIT_DISPLAY_LENGTH: ClassVar[int] = 7

    def __str__(self) -> str:
        return self.sha[: self.COMMIT_DISPLAY_LENGTH]


type PyFile = io.TextIOWrapper
