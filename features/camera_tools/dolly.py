"""Camera-axis dolly and subject-framing compensation."""

from mathutils import Vector

from .context import get_active_transform_target, get_perspective_view_camera


PROP_DOLLY = "dolly_value"


def get_camera_forward(camera):
    forward = -(camera.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0)))
    forward.normalize()
    return forward


def apply_camera_dolly(camera, distance, target=None, keep_subject_framing=False):
    if abs(distance) <= 1e-8:
        return 0.0

    forward = get_camera_forward(camera)
    camera_location = camera.matrix_world.translation.copy()
    applied_distance = distance
    new_lens = None

    if keep_subject_framing:
        if target is None:
            return 0.0

        target_location = target.matrix_world.translation
        old_depth = (target_location - camera_location).dot(forward)
        minimum_depth = max(float(camera.data.clip_start), 1e-4)
        if old_depth <= minimum_depth:
            return 0.0

        new_depth = max(old_depth - distance, minimum_depth)
        old_lens = float(camera.data.lens)
        lens_property = camera.data.bl_rna.properties["lens"]
        requested_lens = old_lens * new_depth / old_depth
        new_lens = min(max(requested_lens, lens_property.hard_min), lens_property.hard_max)
        new_depth = old_depth * new_lens / old_lens
        applied_distance = old_depth - new_depth

    camera_matrix = camera.matrix_world.copy()
    camera_matrix.translation = camera_location + forward * applied_distance
    camera.matrix_world = camera_matrix
    if new_lens is not None:
        camera.data.lens = new_lens
    return applied_distance


def update_camera_dolly(settings, context):
    value = float(settings.dolly_value)
    previous_value = float(settings.dolly_previous)
    settings.dolly_previous = value
    delta = value - previous_value
    if abs(delta) <= 1e-8:
        return

    view_camera = get_perspective_view_camera(context)
    if view_camera is None:
        return

    target = get_active_transform_target(context, view_camera)
    if settings.keep_subject_framing and target is None:
        return

    apply_camera_dolly(
        view_camera,
        delta,
        target=target,
        keep_subject_framing=settings.keep_subject_framing,
    )
