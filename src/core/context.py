from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..adb_service import AdbService
    from ..vision_service import VisionService
    from ..ai_service import AIService
    from clip_critic import ClipCritic
    from .platform import Platform
    from .status_bar import StatusBar
    from profile_db import HarvestService
    from .message_generator import MessageGenerator


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
    clip_enabled: bool   # CLIP profile scoring (like/nope decision)
    chat_enabled: bool   # AI chat replies (Claude API)
    status: "StatusBar | None" = field(default=None)
    harvest: "HarvestService | None" = field(default=None)
    message_generator: "MessageGenerator | None" = field(default=None)
