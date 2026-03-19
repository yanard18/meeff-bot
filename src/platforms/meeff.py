from ..core.platform import Platform
from ..vision_service import VisionService


class MeeffPlatform(Platform):
    """Meeff-specific UI adapter.

    Wraps VisionService so that task code never imports vision details
    directly — making it trivial to swap this out for InstagramPlatform
    without touching any task.
    """

    def __init__(self, vision: VisionService) -> None:
        self._vision = vision

    @property
    def app_package(self) -> str:
        return "com.noyesrun.meeff.kr"

    def detect_state(self) -> str:
        return self._vision.determine_app_state()
