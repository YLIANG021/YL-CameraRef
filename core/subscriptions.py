"""Event-driven subscriptions for active camera changes."""

import bpy


def sync_all_scene_cameras():
    from .camera import sync_scene_camera_state

    for scene in tuple(bpy.data.scenes):
        sync_scene_camera_state(scene, context={"scene": scene})


def register():
    unregister()
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.Scene, "camera"),
        owner=sync_all_scene_cameras,
        args=(),
        notify=sync_all_scene_cameras,
        options={'PERSISTENT'},
    )


def unregister():
    bpy.msgbus.clear_by_owner(sync_all_scene_cameras)
