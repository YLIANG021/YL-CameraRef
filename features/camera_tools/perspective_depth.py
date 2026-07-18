"""Perspective-preserving object depth adjustment."""

import math

from mathutils import Matrix

from .context import get_active_transform_target, get_perspective_view_camera


PROP_DEPTH = "depth_value"


def get_depth_target(context, camera):
    return get_active_transform_target(context, camera)


def apply_depth_factor(target, camera, factor):
    camera_location = camera.matrix_world.translation
    scale_about_camera = (
        Matrix.Translation(camera_location)
        @ Matrix.Scale(factor, 4)
        @ Matrix.Translation(-camera_location)
    )
    target.matrix_world = scale_about_camera @ target.matrix_world


def update_camera_depth(settings, context):
    value = float(settings.depth_value)
    previous_value = float(settings.depth_previous)
    settings.depth_previous = value
    delta = value - previous_value
    if abs(delta) <= 1e-8:
        return

    camera = get_perspective_view_camera(context)
    target = get_depth_target(context, camera) if camera else None

    if camera is None or target is None:
        return

    factor = math.pow(2.0, max(-20.0, min(delta, 20.0)))
    apply_depth_factor(target, camera, factor)
