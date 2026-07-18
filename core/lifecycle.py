"""Top-level add-on register/unregister orchestration."""

from bpy.props import PointerProperty
from bpy.types import Scene, WindowManager

from . import registry, subscriptions
from .. import i18n
from ..features import adjust, camera_tools
from ..features.camera import add_view_camera
from ..properties.settings import BG_AdjustRuntimeSettings, BG_Opacity_Settings


def register():
    i18n.register()
    registry.register_classes()
    Scene.bg_opacity_settings = PointerProperty(type=BG_Opacity_Settings)
    camera_tools.register_properties()
    WindowManager.yl_cameraref_runtime = PointerProperty(
        type=BG_AdjustRuntimeSettings,
    )
    registry.ui.register_header()
    add_view_camera.register_menu()
    subscriptions.register()


def unregister():
    adjust.stop_active_adjust()
    subscriptions.unregister()
    if hasattr(Scene, 'bg_opacity_settings'):
        del Scene.bg_opacity_settings
    camera_tools.unregister_properties()

    if hasattr(WindowManager, 'yl_cameraref_runtime'):
        del WindowManager.yl_cameraref_runtime

    add_view_camera.unregister_menu()
    registry.ui.unregister_header()
    registry.unregister_classes()
    i18n.unregister()
