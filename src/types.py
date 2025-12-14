from dataclasses import dataclass
import io

type ExitCode = int


@dataclass(frozen=True, slots=True)
class Commit:
    sha: str

    def __str__(self) -> str:
        return self.sha


type PyFile = io.TextIOWrapper
