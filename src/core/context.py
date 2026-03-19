from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..adb_service import AdbService
    from ..vision_service import VisionService
    from ..ai_service import AIService
    from clip_critic import ClipCritic
    from .platform import Platform


@dataclass
class BotContext:
    """Single object passed to every Task.run() call.

    Holds every shared service so tasks never need to import or instantiate
    anything themselves. Adding a new service means updating this one class.
    """

    adb: "AdbService"
    vision: "VisionService"
    ai: "AIService"
    critic: "ClipCritic"
    config: dict
    platform: "Platform"
    scoring_enabled: bool
