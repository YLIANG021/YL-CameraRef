"""UI panels."""

from .panel_camera_tools import IMAGE_SWITCHER_PT_CameraTools
from .panel_main import IMAGE_SWITCHER_PT_Panel
from .header import register_header, unregister_header

CLASSES = (
    IMAGE_SWITCHER_PT_Panel,
    IMAGE_SWITCHER_PT_CameraTools,
)

__all__ = (
    "CLASSES",
    "IMAGE_SWITCHER_PT_CameraTools",
    "IMAGE_SWITCHER_PT_Panel",
    "register_header",
    "unregister_header",
)
