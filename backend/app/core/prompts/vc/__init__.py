"""System prompts for the VC startup-evaluation pipeline.

Each agent role has its prompt in a dedicated module. They are re-exported here
so node functions can import them from a single location.
"""

from app.core.prompts.vc.chief import CHIEF_SYSTEM_PROMPT
from app.core.prompts.vc.founder import FOUNDER_SYSTEM_PROMPT
from app.core.prompts.vc.market import MARKET_SYSTEM_PROMPT
from app.core.prompts.vc.product import PRODUCT_SYSTEM_PROMPT
from app.core.prompts.vc.scout import SCOUT_SYSTEM_PROMPT

__all__ = [
    "SCOUT_SYSTEM_PROMPT",
    "MARKET_SYSTEM_PROMPT",
    "PRODUCT_SYSTEM_PROMPT",
    "FOUNDER_SYSTEM_PROMPT",
    "CHIEF_SYSTEM_PROMPT",
]
