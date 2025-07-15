import os
from typing import Final

MAX_ITER: Final[int] = int(os.getenv("IKOMA_MAX_ITER", 25))
MAX_MINS: Final[int] = int(os.getenv("IKOMA_MAX_MINS", 10))
