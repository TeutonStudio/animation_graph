# animation_graph/Core/node_tree.py

import re

import bpy
from bpy.types import NodeGroupInput, NodeGroupOutput
from mathutils import Quaternion

from . import sockets

_SOCKET_INT = {"NodeSocketInt"}
_SOCKET_FLOAT = {"NodeSocketFloat"}
_SOCKET_VECTOR = {
    "NodeSocketVector",
    "NodeSocketVectorXYZ",
    "NodeSocketRotation",
    "NodeSocketVectorTranslation",
}
_SOCKET_MATRIX = {"NodeSocketMatrix"}
_SOCKET_BONE = {"NodeSocketBone"}
_TIMEKEY_CHANNEL_PATH = '["animgraph_time"]'
_LEGACY_TIMEKEY_CHANNEL_PATHS = ('["timeKeys"]', '["time_keys"]')
_ALL_TIMEKEY_CHANNEL_PATHS = (_TIMEKEY_CHANNEL_PATH,) + _LEGACY_TIMEKEY_CHANNEL_PATHS
_BONE_FCURVE_RE = re.compile(
    r'^pose\.bones\["(?P<bone>.+)"\]\.(?P<channel>location|rotation_euler|rotation_quaternion|rotation_axis_angle|scale)$'
)
_TIMEKEY_PROP_NAMES = (
    "timeKeys",
    "time_keys",
    "timekeys",
    "animgraph_time",
)


def _on_action_input_changed(self, context):
    action = getattr(self, "id_data", None)
    tree = getattr(action, "animgraph_tree", None) if action else None
    if tree:
        try:
            tree.dirty = True
        except Exception:
            pass


def _on_action_tree_changed(self, context):
    tree = getattr(self, "animgraph_tree", None)

    if tree and getattr(tree, "bl_idname", "") != "AnimNodeTree":
        try:
            self.animgraph_tree = None
        except Exception:
            pass
        return

    if not tree:
        try:
            self.animgraph_input_values.clear()
        except Exception:
            pass
        _set_action_timekey_editable(self, True)
        return

    sync_action_inputs(self, tree)
    _import_tree_from_action_timekeys(self, tree)
    sync_action_timekeys_from_tree(self, tree)
    _set_action_timekey_editable(self, False)

    try:
        tree.dirty = True
    except Exception:
        pass


def _poll_armature_obj(self, obj):
    return obj is not None and obj.type == "ARMATURE"


def _poll_animgraph_tree(self, tree):
    return tree is not None and getattr(tree, "bl_idname", "") == "AnimNodeTree"


def _enum_slot_bones(self, context):
    arm_obj = getattr(self, "bone_armature_obj", None)

    if not arm_obj or arm_obj.type != "ARMATURE" or not arm_obj.data:
        return [("", "(select armature first)", "Pick an armature first.")]

    items = []
    for bone in arm_obj.data.bones:
        items.append((bone.name, bone.name, ""))

    if not items:
        return [("", "(no bones)", "The selected armature has no bones.")]
    return items


def _on_slot_armature_changed(self, context):
    arm_obj = getattr(self, "bone_armature_obj", None)
    current = getattr(self, "bone_name", "")

    if not arm_obj or arm_obj.type != "ARMATURE" or not arm_obj.data:
        self.bone_name = ""
    elif current and current not in arm_obj.data.bones:
        self.bone_name = ""

    _on_action_input_changed(self, context)


class AnimGraphActionInputValue(bpy.types.PropertyGroup):
    identifier: bpy.props.StringProperty()
    name: bpy.props.StringProperty()
    socket_type: bpy.props.StringProperty()

    int_value: bpy.props.IntProperty(
        name="Value",
        default=0,
        update=_on_action_input_changed,
    )
    float_value: bpy.props.FloatProperty(
        name="Value",
        default=0.0,
        update=_on_action_input_changed,
    )
    vector_value: bpy.props.FloatVectorProperty(
        name="Value",
        size=3,
        default=(0.0, 0.0, 0.0),
        update=_on_action_input_changed,
    )
    matrix_value: bpy.props.FloatVectorProperty(
        name="Value",
        size=16,
        default=(
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        ),
        update=_on_action_input_changed,
    )
    bone_armature_obj: bpy.props.PointerProperty(
        name="Armature",
        description="Armature object",
        type=bpy.types.Object,
        poll=_poll_armature_obj,
        update=_on_slot_armature_changed,
    )
    bone_name: bpy.props.EnumProperty(
        name="Bone",
        description="Bone to use",
        items=_enum_slot_bones,
        update=_on_action_input_changed,
    )


def socket_kind(socket_type):
    socket_type = socket_type or ""

    if socket_type in _SOCKET_BONE or "bone" in socket_type.lower():
        return "BONE"
    if socket_type in _SOCKET_INT or "int" in socket_type.lower():
        return "INT"
    if socket_type in _SOCKET_FLOAT or "float" in socket_type.lower():
        return "FLOAT"
    if socket_type in _SOCKET_MATRIX or "matrix" in socket_type.lower():
        return "MATRIX"
    if socket_type in _SOCKET_VECTOR or any(k in socket_type.lower() for k in ("vector", "rotation", "translation")):
        return "VECTOR"
    return "UNSUPPORTED"


def interface_socket_identifier(iface_socket):
    return getattr(iface_socket, "identifier", None) or getattr(iface_socket, "name", None) or ""


def interface_socket_type(iface_socket):
    return getattr(iface_socket, "bl_socket_idname", None) or getattr(iface_socket, "socket_type", None) or ""


def iter_interface_sockets(tree, in_out=None):
    iface = getattr(tree, "interface", None)
    if iface is None:
        return []

    sockets_out = []
    try:
        for item in iface.items_tree:
            if getattr(item, "item_type", None) != "SOCKET":
                continue
            if in_out and getattr(item, "in_out", None) != in_out:
                continue
            sockets_out.append(item)
    except Exception:
        return []
    return sockets_out


def find_action_input_slot(action, identifier):
    for slot in getattr(action, "animgraph_input_values", []):
        if slot.identifier == identifier:
            return slot
    return None


def _matrix_to_16(value):
    ident = (
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    )
    try:
        rows = [tuple(r) for r in value]
        if len(rows) < 4:
            return ident
        flat = []
        for row in rows[:4]:
            if len(row) < 4:
                return ident
            flat.extend(float(v) for v in row[:4])
        return tuple(flat)
    except Exception:
        return ident


def _assign_slot_default(slot, iface_socket):
    kind = socket_kind(slot.socket_type)
    default_value = getattr(iface_socket, "default_value", None)

    try:
        if kind == "INT":
            slot.int_value = int(default_value if default_value is not None else 0)
        elif kind == "FLOAT":
            slot.float_value = float(default_value if default_value is not None else 0.0)
        elif kind == "VECTOR":
            if default_value is None:
                slot.vector_value = (0.0, 0.0, 0.0)
            else:
                slot.vector_value = (
                    float(default_value[0]),
                    float(default_value[1]),
                    float(default_value[2]),
                )
        elif kind == "MATRIX":
            slot.matrix_value = _matrix_to_16(default_value)
        elif kind == "BONE":
            slot.bone_armature_obj = getattr(iface_socket, "armature_obj", None)
            slot.bone_name = getattr(iface_socket, "bone_name", "") or ""
    except Exception:
        pass


def sync_action_inputs(action, tree):
    if action is None or tree is None:
        return []

    iface_inputs = iter_interface_sockets(tree, in_out="INPUT")
    wanted = {}
    for iface_socket in iface_inputs:
        ident = interface_socket_identifier(iface_socket)
        if ident:
            wanted[ident] = iface_socket

    stale = []
    for idx, slot in enumerate(action.animgraph_input_values):
        if slot.identifier not in wanted:
            stale.append(idx)
    for idx in reversed(stale):
        action.animgraph_input_values.remove(idx)

    for ident, iface_socket in wanted.items():
        slot = find_action_input_slot(action, ident)
        socket_type = interface_socket_type(iface_socket)

        if slot is None:
            slot = action.animgraph_input_values.add()
            slot.identifier = ident
            slot.name = getattr(iface_socket, "name", ident)
            slot.socket_type = socket_type
            _assign_slot_default(slot, iface_socket)
            continue

        old_type = slot.socket_type
        slot.name = getattr(iface_socket, "name", ident)
        slot.socket_type = socket_type
        if old_type != socket_type:
            _assign_slot_default(slot, iface_socket)

    return iface_inputs


def _iter_non_timekey_fcurves(action):
    for fcurve in getattr(action, "fcurves", []):
        if getattr(fcurve, "data_path", "") in _ALL_TIMEKEY_CHANNEL_PATHS:
            continue
        yield fcurve


def _find_any_timekey_fcurve(action):
    for path in _ALL_TIMEKEY_CHANNEL_PATHS:
        for fcurve in getattr(action, "fcurves", []):
            if getattr(fcurve, "data_path", "") != path:
                continue
            if int(getattr(fcurve, "array_index", 0)) != 0:
                continue
            return fcurve, path
    return None, None


def _append_frame_value(out_set, value):
    try:
        out_set.add(int(round(float(value))))
    except Exception:
        pass


def _collect_frames_from_any(out_set, value):
    if value is None:
        return

    if isinstance(value, (int, float)):
        _append_frame_value(out_set, value)
        return

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return
        for tok in re.findall(r"-?\d+(?:\.\d+)?", text):
            if not tok:
                continue
            _append_frame_value(out_set, tok)
        return

    if isinstance(value, dict):
        for key in ("frames", "keys", "timeKeys", "time_keys", "times", "values"):
            if key in value:
                _collect_frames_from_any(out_set, value.get(key))
        return

    if isinstance(value, (list, tuple, set)):
        for item in value:
            _collect_frames_from_any(out_set, item)
        return

    for attr in ("frame", "time", "value"):
        if hasattr(value, attr):
            try:
                _collect_frames_from_any(out_set, getattr(value, attr))
                return
            except Exception:
                pass

    try:
        iterator = iter(value)
    except Exception:
        return

    for item in iterator:
        _collect_frames_from_any(out_set, item)


def _collect_time_frames_from_action_properties(action):
    frames = set()

    for prop_name in _TIMEKEY_PROP_NAMES:
        val = None
        try:
            if prop_name in action:
                val = action[prop_name]
        except Exception:
            pass
        if val is None:
            try:
                val = getattr(action, prop_name, None)
            except Exception:
                val = None
        _collect_frames_from_any(frames, val)

    try:
        for key in action.keys():
            if key in {"_RNA_UI"}:
                continue
            low = str(key).lower()
            if "time" not in low or "key" not in low:
                continue
            try:
                _collect_frames_from_any(frames, action[key])
            except Exception:
                pass
    except Exception:
        pass

    for marker in getattr(action, "pose_markers", []):
        _append_frame_value(frames, getattr(marker, "frame", None))

    return sorted(frames)


def _collect_action_time_frames(action):
    fcurve, _ = _find_any_timekey_fcurve(action)
    if fcurve is not None:
        frames = _fcurve_key_frames(fcurve)
        if frames:
            return frames

    frames = _collect_time_frames_from_action_properties(action)
    if frames:
        return frames

    seen = set()
    for fcurve in _iter_non_timekey_fcurves(action):
        for key in getattr(fcurve, "keyframe_points", []):
            try:
                seen.add(int(round(float(key.co[0]))))
            except Exception:
                pass
    return sorted(seen)


def _collect_bone_fcurves(action):
    bones = {}

    for fcurve in _iter_non_timekey_fcurves(action):
        data_path = getattr(fcurve, "data_path", "") or ""
        match = _BONE_FCURVE_RE.match(data_path)
        if not match:
            continue

        bone_name = match.group("bone")
        channel = match.group("channel")
        array_idx = int(getattr(fcurve, "array_index", 0))

        entry = bones.setdefault(
            bone_name,
            {
                "frames": set(),
                "location": {},
                "rotation_euler": {},
                "rotation_quaternion": {},
                "rotation_axis_angle": {},
                "scale": {},
            },
        )
        entry[channel][array_idx] = fcurve

        for key in getattr(fcurve, "keyframe_points", []):
            try:
                entry["frames"].add(int(round(float(key.co[0]))))
            except Exception:
                pass

    return bones


def _fcurve_eval(fcurve, frame, fallback):
    if fcurve is None:
        return fallback
    try:
        return float(fcurve.evaluate(float(frame)))
    except Exception:
        return fallback


def _evaluate_bone_target(channels, frame):
    loc_curves = channels.get("location", {})
    rot_euler_curves = channels.get("rotation_euler", {})
    rot_quat_curves = channels.get("rotation_quaternion", {})
    rot_axis_angle_curves = channels.get("rotation_axis_angle", {})
    scale_curves = channels.get("scale", {})

    loc = (
        _fcurve_eval(loc_curves.get(0), frame, 0.0),
        _fcurve_eval(loc_curves.get(1), frame, 0.0),
        _fcurve_eval(loc_curves.get(2), frame, 0.0),
    )

    scale = (
        _fcurve_eval(scale_curves.get(0), frame, 1.0),
        _fcurve_eval(scale_curves.get(1), frame, 1.0),
        _fcurve_eval(scale_curves.get(2), frame, 1.0),
    )

    if rot_quat_curves:
        quat = Quaternion(
            (
                _fcurve_eval(rot_quat_curves.get(0), frame, 1.0),
                _fcurve_eval(rot_quat_curves.get(1), frame, 0.0),
                _fcurve_eval(rot_quat_curves.get(2), frame, 0.0),
                _fcurve_eval(rot_quat_curves.get(3), frame, 0.0),
            )
        )
        euler = quat.to_euler("XYZ")
        rot = (float(euler.x), float(euler.y), float(euler.z))
    elif rot_axis_angle_curves:
        angle = _fcurve_eval(rot_axis_angle_curves.get(0), frame, 0.0)
        axis = (
            _fcurve_eval(rot_axis_angle_curves.get(1), frame, 1.0),
            _fcurve_eval(rot_axis_angle_curves.get(2), frame, 0.0),
            _fcurve_eval(rot_axis_angle_curves.get(3), frame, 0.0),
        )
        try:
            quat = Quaternion(axis, angle)
            euler = quat.to_euler("XYZ")
            rot = (float(euler.x), float(euler.y), float(euler.z))
        except Exception:
            rot = (0.0, 0.0, 0.0)
    else:
        rot = (
            _fcurve_eval(rot_euler_curves.get(0), frame, 0.0),
            _fcurve_eval(rot_euler_curves.get(1), frame, 0.0),
            _fcurve_eval(rot_euler_curves.get(2), frame, 0.0),
        )

    return loc, rot, scale


def _find_action_armature(action):
    for obj in bpy.data.objects:
        ad = getattr(obj, "animation_data", None)
        if getattr(ad, "action", None) != action:
            continue
        if getattr(obj, "type", "") == "ARMATURE":
            return obj
    return None


def _tree_has_user_nodes(tree):
    for node in getattr(tree, "nodes", []):
        if getattr(node, "type", "") in {"GROUP_INPUT", "GROUP_OUTPUT"}:
            continue
        return True
    return False


def _set_node_input_default(node, socket_name, value):
    sock = getattr(node, "inputs", {}).get(socket_name) if node else None
    if sock is None:
        return
    try:
        sock.default_value = value
    except Exception:
        pass


def _link(tree, out_sock, in_sock):
    if tree is None or out_sock is None or in_sock is None:
        return
    try:
        tree.links.new(out_sock, in_sock)
    except Exception:
        pass


def _import_tree_from_action_timekeys(action, tree):
    if action is None or tree is None:
        return
    if _tree_has_user_nodes(tree):
        return

    time_frames = _collect_action_time_frames(action)
    bones = _collect_bone_fcurves(action)
    if not bones and not time_frames:
        return

    arm_obj = _find_action_armature(action)
    base_x = -700.0
    base_y = 0.0
    row_step = -260.0
    col_step = 280.0

    tracks = []
    if bones:
        for bone_name in sorted(bones.keys()):
            data = bones[bone_name]
            frames = sorted(set(int(f) for f in data["frames"]))
            if time_frames:
                frames = sorted(set(frames) | set(time_frames))
            if not frames and time_frames:
                frames = list(time_frames)
            if not frames:
                continue
            tracks.append((bone_name, data, frames))
    else:
        tracks.append(
            (
                "",
                {
                    "location": {},
                    "rotation_euler": {},
                    "rotation_quaternion": {},
                    "rotation_axis_angle": {},
                    "scale": {},
                },
                list(time_frames),
            )
        )

    for row_idx, (bone_name, data, frames) in enumerate(tracks):
        if not frames:
            continue

        y = base_y + (row_idx * row_step)

        bone_node = tree.nodes.new("DefineBoneNode")
        display_name = bone_name or "Unassigned"
        bone_node.name = f"Bone {display_name}"
        bone_node.label = display_name
        bone_node.location = (base_x, y)

        bone_out = bone_node.outputs.get("Bone")
        if bone_out is not None:
            if arm_obj is not None:
                try:
                    bone_out.armature_obj = arm_obj
                except Exception:
                    pass
            if bone_name:
                try:
                    bone_out.bone_name = bone_name
                except Exception:
                    pass

        ranges = []
        if len(frames) == 1:
            ranges.append((frames[0], frames[0]))
        else:
            for idx in range(len(frames) - 1):
                ranges.append((frames[idx], frames[idx + 1]))

        prev_transform = None
        for col_idx, (start, end) in enumerate(ranges):
            transform = tree.nodes.new("DefineBoneTransform")
            transform_name = display_name
            transform.name = f"{transform_name} [{start}-{end}]"
            transform.label = f"{transform_name} {start}->{end}"
            transform.location = (base_x + col_step + (col_idx * col_step), y)

            try:
                transform.apply_mode = "TO"
                transform.interpolation = "LINEAR"
            except Exception:
                pass

            duration = max(0, int(end) - int(start))
            _set_node_input_default(transform, "Start", int(start))
            _set_node_input_default(transform, "Duration", int(duration))

            loc, rot, scale = _evaluate_bone_target(data, int(end))
            _set_node_input_default(transform, "Translation", loc)
            _set_node_input_default(transform, "Rotation", rot)
            _set_node_input_default(transform, "Scale", scale)

            _link(tree, bone_out, transform.inputs.get("Bone"))
            if prev_transform is not None:
                _link(
                    tree,
                    prev_transform.outputs.get("End"),
                    transform.inputs.get("Start"),
                )
            prev_transform = transform


def _find_timekey_fcurve(action):
    fcurve, _ = _find_any_timekey_fcurve(action)
    return fcurve


def _fcurve_key_frames(fcurve):
    out = []
    for key in getattr(fcurve, "keyframe_points", []):
        try:
            out.append(int(round(float(key.co[0]))))
        except Exception:
            pass
    return sorted(set(out))


def _resolve_int_input(sock, node_cache, stack):
    if sock is None:
        return 0

    if getattr(sock, "is_linked", False) and sock.links:
        from_sock = sock.links[0].from_socket
        node = getattr(from_sock, "node", None)
        if node and getattr(node, "bl_idname", "") == "DefineBoneTransform" and from_sock.name == "End":
            return _resolve_transform_end(node, node_cache, stack)

        try:
            return int(round(float(getattr(from_sock, "default_value", 0))))
        except Exception:
            return 0

    try:
        return int(round(float(getattr(sock, "default_value", 0))))
    except Exception:
        return 0


def _resolve_transform_end(node, node_cache, stack):
    node_ptr = node.as_pointer()
    if node_ptr in node_cache:
        return node_cache[node_ptr]
    if node_ptr in stack:
        try:
            return int(round(float(getattr(node.outputs.get("End"), "default_value", 0))))
        except Exception:
            return 0

    stack.add(node_ptr)
    try:
        start = _resolve_int_input(node.inputs.get("Start"), node_cache, stack)
        duration = _resolve_int_input(node.inputs.get("Duration"), node_cache, stack)
        end_value = int(start + max(0, duration))
    finally:
        stack.discard(node_ptr)

    node_cache[node_ptr] = end_value
    return end_value


def collect_tree_timekeys(tree):
    if tree is None:
        return []

    keys = set()
    node_cache = {}
    stack = set()

    for node in getattr(tree, "nodes", []):
        if getattr(node, "bl_idname", "") != "DefineBoneTransform":
            continue

        start = _resolve_int_input(node.inputs.get("Start"), node_cache, stack)
        duration = _resolve_int_input(node.inputs.get("Duration"), node_cache, stack)
        end_value = int(start + max(0, duration))

        keys.add(int(start))
        keys.add(int(end_value))

    return sorted(keys)


def _write_action_timekey_channel(action, frames):
    if action is None:
        return

    fcurve, data_path = _find_any_timekey_fcurve(action)
    wanted = sorted(set(int(f) for f in frames))

    if not wanted and fcurve is None:
        return

    if fcurve is not None:
        current = _fcurve_key_frames(fcurve)
        if current == wanted:
            return

    if wanted:
        for prop_name in ("animgraph_time", "timeKeys", "time_keys"):
            try:
                action[prop_name] = float(wanted[0])
            except Exception:
                pass

    if fcurve is None and wanted:
        data_path = _TIMEKEY_CHANNEL_PATH
        try:
            fcurve = action.fcurves.new(data_path=data_path, index=0, action_group="AnimGraph")
        except Exception:
            fcurve = None

    if fcurve is None:
        return

    while len(fcurve.keyframe_points) > 0:
        try:
            fcurve.keyframe_points.remove(fcurve.keyframe_points[0], fast=True)
        except TypeError:
            fcurve.keyframe_points.remove(fcurve.keyframe_points[0])
        except Exception:
            break

    for frame in wanted:
        try:
            key = fcurve.keyframe_points.insert(float(frame), 0.0, options={"FAST"})
        except TypeError:
            key = fcurve.keyframe_points.insert(float(frame), 0.0)
        except Exception:
            continue
        try:
            key.interpolation = "CONSTANT"
        except Exception:
            pass

    try:
        fcurve.update()
    except Exception:
        pass


def _set_action_timekey_editable(action, editable):
    lock = not bool(editable)
    for fcurve in getattr(action, "fcurves", []):
        try:
            if bool(getattr(fcurve, "lock", False)) != lock:
                fcurve.lock = lock
        except Exception:
            pass


def sync_action_timekeys_from_tree(action, tree):
    if action is None:
        return

    if tree is None:
        _set_action_timekey_editable(action, True)
        return

    frames = collect_tree_timekeys(tree)
    _write_action_timekey_channel(action, frames)
    _set_action_timekey_editable(action, False)


def sync_actions_for_tree(tree):
    if tree is None:
        return

    for action in bpy.data.actions:
        if getattr(action, "animgraph_tree", None) != tree:
            continue
        sync_action_inputs(action, tree)
        sync_action_timekeys_from_tree(action, tree)


def _slot_runtime_value(slot):
    kind = socket_kind(slot.socket_type)
    if kind == "BONE":
        return (slot.bone_armature_obj, slot.bone_name or "")
    if kind == "INT":
        return int(slot.int_value)
    if kind == "FLOAT":
        return float(slot.float_value)
    if kind == "VECTOR":
        return (
            float(slot.vector_value[0]),
            float(slot.vector_value[1]),
            float(slot.vector_value[2]),
        )
    if kind == "MATRIX":
        v = slot.matrix_value
        return (
            (float(v[0]), float(v[1]), float(v[2]), float(v[3])),
            (float(v[4]), float(v[5]), float(v[6]), float(v[7])),
            (float(v[8]), float(v[9]), float(v[10]), float(v[11])),
            (float(v[12]), float(v[13]), float(v[14]), float(v[15])),
        )
    return None


def build_action_input_value_map(action, tree):
    values = {}
    iface_inputs = sync_action_inputs(action, tree)
    for iface_socket in iface_inputs:
        ident = interface_socket_identifier(iface_socket)
        if not ident:
            continue

        slot = find_action_input_slot(action, ident)
        if slot is None:
            continue

        value = _slot_runtime_value(slot)
        if value is None:
            continue

        sock_name = getattr(iface_socket, "name", ident)
        values[sock_name] = value
    return values


def register(): 
    for c in _CLASSES: bpy.utils.register_class(c)

    bpy.types.Action.animgraph_tree = bpy.props.PointerProperty(
        name="Animation Graph",
        description="AnimGraph node tree used when this Action is active",
        type=AnimNodeTree,
        poll=_poll_animgraph_tree,
        update=_on_action_tree_changed,
    )
    bpy.types.Action.animgraph_input_values = bpy.props.CollectionProperty(
        name="AnimGraph Inputs",
        type=AnimGraphActionInputValue,
    )
def unregister(): 
    for c in reversed(_CLASSES): bpy.utils.unregister_class(c)
    if hasattr(bpy.types.Action, "animgraph_input_values"):
        del bpy.types.Action.animgraph_input_values
    if hasattr(bpy.types.Action, "animgraph_tree"):
        del bpy.types.Action.animgraph_tree

class AnimNodeTree(bpy.types.NodeTree):
    """AnimGraph node tree."""

    bl_idname = "AnimNodeTree"
    bl_label = "Animation Node Editor"
    bl_icon = "ARMATURE_DATA"
    bl_description = "Wird verwendet um eine Amatur Pose abhängig vom Zeitpunkt zu definieren"
    bl_use_group_interface = True

    def update(self):
        # RigInput Node-Ausgänge aktualisieren (optional)
        for n in getattr(self, "nodes", []): self.update_node(n)
        for l in getattr(self, "links", []): self.update_link(l)
        try:
            sync_actions_for_tree(self)
        except Exception:
            pass

    def update_node(self,n: bpy.types.Node): pass

    def update_link(self,l: bpy.types.NodeLink): 
        if not sockets.isValidLink(l):
            try: self.links.remove(l)
            except RuntimeError: pass

    def interface_update(self, context):
        # 1) IO-Nodes im *gleichen* Tree (das ist der Tree dessen Interface gerade geändert wurde)
        for n in getattr(self, "nodes", []):
            if n.bl_idname == NodeGroupInput.bl_idname:
                try: n.sync_from_tree_interface()
                except Exception: pass
            elif n.bl_idname == NodeGroupOutput.bl_idname:
                try: n.sync_from_tree_interface()
                except Exception: pass

        # 2) Alle Group-Instanzen in *anderen* Trees, die diese node_tree benutzen
        #    (sonst aktualisiert sich deine Group-Node im Parent-Tree nie)
        for parent in bpy.data.node_groups:
            if getattr(parent, "bl_idname", None) != AnimNodeTree.bl_idname:
                continue

            touched = False
            for node in parent.nodes:
                if node.bl_idname == "AnimGroupNode" and node.node_tree == self:
                    try:
                        node.sync_sockets_from_subtree()
                        touched = True
                    except Exception: pass

            if touched:
                try: parent.update_tag()   # UI/Depsgraph refresh
                except Exception: pass

        # 3) Action-Panel Inputs für alle Actions aktualisieren, die diesen Tree verwenden
        try:
            sync_actions_for_tree(self)
        except Exception:
            pass



_CLASSES = [
    AnimGraphActionInputValue,
    AnimNodeTree,
    sockets.NodeSocketBone
]
