# animation_graph/Core/helper_methoden.py

from mathutils import Quaternion
from types import SimpleNamespace
import re
import bpy

from . import sockets

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
)

def _pointer_uid(value):
    if value is None:
        return None

    try:
        return ("PTR", int(value.as_pointer()))
    except Exception:
        return ("PY", id(value))

def _iter_action_slots(action, context=None):
    seen = set()

    def _emit(slot):
        uid = _pointer_uid(slot)
        if uid is None or uid in seen:
            return
        seen.add(uid)
        yield slot

    if context is not None:
        obj = getattr(context, "object", None)
        ad = getattr(obj, "animation_data", None) if obj else None
        if getattr(ad, "action", None) == action:
            slot = getattr(ad, "action_slot", None)
            if slot is not None:
                yield from _emit(slot)

    for slot in getattr(action, "slots", []):
        yield from _emit(slot)

    for obj in bpy.data.objects:
        ad = getattr(obj, "animation_data", None)
        if getattr(ad, "action", None) != action:
            continue
        slot = getattr(ad, "action_slot", None)
        if slot is None:
            continue
        yield from _emit(slot)

def _resolve_strip_channelbag(strip, slot=None, ensure=False):
    method_names = ("channelbag", "channelbag_for_slot", "channelbag_for", "get_channelbag")

    for method_name in method_names:
        method = getattr(strip, method_name, None)
        if not callable(method):
            continue

        arg_options = []
        if slot is not None:
            arg_options.extend(
                [
                    ((slot,), {}),
                    ((slot,), {"ensure": ensure}),
                    ((slot, ensure), {}),
                    ((), {"slot": slot}),
                    ((), {"slot": slot, "ensure": ensure}),
                ]
            )
        else:
            arg_options.extend(
                [
                    ((), {}),
                    ((), {"ensure": ensure}),
                ]
            )

        for args, kwargs in arg_options:
            try:
                bag = method(*args, **kwargs)
            except TypeError:
                continue
            except Exception:
                continue
            if bag is not None:
                return bag

    return None

def _iter_action_fcurve_collections(action, context=None):
    seen = set()

    def _emit(collection):
        uid = _pointer_uid(collection)
        if uid is None or uid in seen:
            return
        seen.add(uid)
        yield collection

    direct_fcurves = getattr(action, "fcurves", None)
    if direct_fcurves is not None:
        yield from _emit(direct_fcurves)

    slots = list(_iter_action_slots(action, context))

    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            matched_slot_bag = False

            for slot in slots:
                bag = _resolve_strip_channelbag(strip, slot=slot, ensure=False)
                bag_fcurves = getattr(bag, "fcurves", None) if bag is not None else None
                if bag_fcurves is not None:
                    matched_slot_bag = True
                    yield from _emit(bag_fcurves)

            strip_fcurves = getattr(strip, "fcurves", None)
            if strip_fcurves is not None:
                yield from _emit(strip_fcurves)

            if not matched_slot_bag:
                for bag in getattr(strip, "channelbags", []):
                    bag_fcurves = getattr(bag, "fcurves", None)
                    if bag_fcurves is not None:
                        yield from _emit(bag_fcurves)

                if not slots:
                    bag = _resolve_strip_channelbag(strip, slot=None, ensure=False)
                    bag_fcurves = getattr(bag, "fcurves", None) if bag is not None else None
                    if bag_fcurves is not None:
                        yield from _emit(bag_fcurves)

def _iter_action_fcurves(action, context=None):
    seen = set()

    for collection in _iter_action_fcurve_collections(action, context=context):
        try:
            iterator = iter(collection)
        except Exception:
            continue

        for fcurve in iterator:
            uid = _pointer_uid(fcurve)
            if uid is None or uid in seen:
                continue
            seen.add(uid)
            yield fcurve

def _find_writable_fcurve_collection(action, context=None):
    direct_fcurves = getattr(action, "fcurves", None)
    if direct_fcurves is not None and hasattr(direct_fcurves, "new"):
        return direct_fcurves

    for collection in _iter_action_fcurve_collections(action, context=context):
        if hasattr(collection, "new"):
            return collection
    return None

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

    initialize_action_tree_binding(self, tree, context)

def initialize_action_tree_binding(action, tree, context=None):
    if action is None:
        return

    if not tree:
        try:
            action.animgraph_input_values.clear()
        except Exception:
            pass
        _set_action_timekey_editable(action, True)
        return

    sync_action_inputs(action, tree)
    _import_tree_from_action_timekeys(action, tree, context)
    sync_action_timekeys_from_tree(action, tree, context=context)
    _set_action_timekey_editable(action, False)

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

def socket_kind(socket_type):
    socket_type = socket_type or ""

    if socket_type in sockets._SOCKET_BONE or "bone" in socket_type.lower():
        return "BONE"
    if socket_type in sockets._SOCKET_INT or "int" in socket_type.lower():
        return "INT"
    if socket_type in sockets._SOCKET_FLOAT or "float" in socket_type.lower():
        return "FLOAT"
    if socket_type in sockets._SOCKET_MATRIX or "matrix" in socket_type.lower():
        return "MATRIX"
    if socket_type in sockets._SOCKET_VECTORS or any(k in socket_type.lower() for k in ("vector", "rotation", "translation")):
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

def _iter_non_timekey_fcurves(action, context=None):
    for fcurve in _iter_action_fcurves(action, context=context):
        if getattr(fcurve, "data_path", "") in _ALL_TIMEKEY_CHANNEL_PATHS:
            continue
        yield fcurve

def _find_any_timekey_fcurve(action, context=None):
    fcurves = list(_iter_action_fcurves(action, context=context))
    for path in _ALL_TIMEKEY_CHANNEL_PATHS:
        for fcurve in fcurves:
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

def _extract_numeric_tokens(text):
    if text is None:
        return []
    return re.findall(r"-?\d+(?:\.\d+)?", str(text))

def _read_action_property_value(action, prop_name):
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
    return val

def _mapping_items(value):
    if isinstance(value, dict):
        return list(value.items())

    try:
        keys = list(value.keys())
    except Exception:
        return None

    out = []
    for key in keys:
        try:
            out.append((key, value[key]))
        except Exception:
            pass
    return out

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
        for tok in _extract_numeric_tokens(text):
            if not tok:
                continue
            _append_frame_value(out_set, tok)
        return

    items = _mapping_items(value)
    if items is not None:
        lower = {str(k).lower(): v for k, v in items}
        for key in ("frames", "keys", "timeKeys", "time_keys", "times", "values"):
            if key.lower() in lower:
                _collect_frames_from_any(out_set, lower.get(key.lower()))
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

def _extract_scalar_int(value):
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except Exception:
        pass

    if isinstance(value, str):
        toks = _extract_numeric_tokens(value)
        if toks:
            try:
                return int(round(float(toks[0])))
            except Exception:
                return None
    return None

def _extract_vector3(value):
    if value is None:
        return None

    if isinstance(value, str):
        nums = _extract_numeric_tokens(value)
        if len(nums) < 3:
            return None
        try:
            return (float(nums[0]), float(nums[1]), float(nums[2]))
        except Exception:
            return None

    items = _mapping_items(value)
    if items is not None:
        lower = {str(k).lower(): v for k, v in items}
        if all(axis in lower for axis in ("x", "y", "z")):
            try:
                return (
                    float(lower["x"]),
                    float(lower["y"]),
                    float(lower["z"]),
                )
            except Exception:
                return None
        if all(axis in lower for axis in ("0", "1", "2")):
            try:
                return (
                    float(lower["0"]),
                    float(lower["1"]),
                    float(lower["2"]),
                )
            except Exception:
                return None

    try:
        seq = list(value)
    except Exception:
        return None

    if len(seq) < 3:
        return None
    try:
        return (float(seq[0]), float(seq[1]), float(seq[2]))
    except Exception:
        return None

def _extract_timekey_entry_from_mapping(data_items):
    lower = {str(k).lower(): v for k, v in data_items}

    frame = None
    for key in ("frame", "time", "key", "start", "start_frame", "keyframe", "key_frame", "frame_index", "frame_idx", "at"):
        if key in lower:
            frame = _extract_scalar_int(lower.get(key))
            if frame is not None:
                break
    if frame is None:
        return None

    entry = {"frame": int(frame)}

    for key in ("bone", "bone_name", "bonename", "bone_ref", "boneref", "boneid", "target_bone", "targetbone", "target"):
        if key in lower:
            bone = str(lower.get(key) or "").strip()
            if bone:
                entry["bone_name"] = bone
                break

    for key in ("duration", "length", "len", "dur"):
        if key in lower:
            duration = _extract_scalar_int(lower.get(key))
            if duration is not None:
                entry["duration"] = max(0, int(duration))
                break

    for key in ("end", "end_frame", "to", "until"):
        if key in lower:
            end_frame = _extract_scalar_int(lower.get(key))
            if end_frame is not None:
                entry["end_frame"] = int(end_frame)
                break

    for key in ("location", "translation", "position", "loc"):
        if key in lower:
            vec = _extract_vector3(lower.get(key))
            if vec is not None:
                entry["location"] = vec
                break

    for key in ("rotation", "rotation_euler", "rotation_xyz", "euler", "rot"):
        if key in lower:
            vec = _extract_vector3(lower.get(key))
            if vec is not None:
                entry["rotation"] = vec
                break

    for key in ("scale", "scl", "size"):
        if key in lower:
            vec = _extract_vector3(lower.get(key))
            if vec is not None:
                entry["scale"] = vec
                break

    return entry

def _collect_timekey_entries_from_any(value, out_entries):
    if value is None:
        return

    items = _mapping_items(value)
    if items is not None:
        entry = _extract_timekey_entry_from_mapping(items)
        if entry is not None:
            out_entries.append(entry)

        lower = {str(k).lower(): v for k, v in items}
        for key in ("keys", "timekeys", "time_keys", "entries", "items", "values"):
            if key in lower:
                _collect_timekey_entries_from_any(lower.get(key), out_entries)
        return

    if isinstance(value, str):
        return

    try:
        iterator = iter(value)
    except Exception:
        return

    for item in iterator:
        _collect_timekey_entries_from_any(item, out_entries)

def _collect_timekey_entries_from_action_properties(action):
    entries = []

    for prop_name in _TIMEKEY_PROP_NAMES:
        _collect_timekey_entries_from_any(_read_action_property_value(action, prop_name), entries)

    try:
        for key in action.keys():
            if key in {"_RNA_UI"}:
                continue
            low = str(key).lower()
            if "time" not in low or "key" not in low:
                continue
            _collect_timekey_entries_from_any(action[key], entries)
    except Exception:
        pass

    return entries

def _collect_time_frames_from_action_properties(action):
    frames = set()

    for prop_name in _TIMEKEY_PROP_NAMES:
        val = _read_action_property_value(action, prop_name)
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

def _collect_action_time_frames(action, context=None):
    fcurve, _ = _find_any_timekey_fcurve(action, context=context)
    if fcurve is not None:
        frames = _fcurve_key_frames(fcurve)
        if frames:
            return frames

    entries = _collect_timekey_entries_from_action_properties(action)
    if entries:
        entry_frames = set()
        for entry in entries:
            _append_frame_value(entry_frames, entry.get("frame"))

            end_frame = entry.get("end_frame")
            if end_frame is not None:
                _append_frame_value(entry_frames, end_frame)
                continue

            duration = entry.get("duration")
            if duration is not None:
                _append_frame_value(entry_frames, int(entry.get("frame", 0)) + int(duration))

        frames = sorted(entry_frames)
        if frames:
            return frames

    frames = _collect_time_frames_from_action_properties(action)
    if frames:
        return frames

    seen = set()
    for fcurve in _iter_non_timekey_fcurves(action, context=context):
        for key in getattr(fcurve, "keyframe_points", []):
            try:
                seen.add(int(round(float(key.co[0]))))
            except Exception:
                pass
    return sorted(seen)

def _collect_bone_fcurves(action, context=None):
    bones = {}

    for fcurve in _iter_non_timekey_fcurves(action, context=context):
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

def _find_action_armature(action, context=None):
    obj = getattr(context, "object", None) if context else None
    if obj is not None and getattr(obj, "type", "") == "ARMATURE":
        ad = getattr(obj, "animation_data", None)
        if getattr(ad, "action", None) == action:
            return obj

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

def _clear_input_links(tree, in_sock):
    if tree is None or in_sock is None:
        return
    for link in list(getattr(in_sock, "links", [])):
        try:
            tree.links.remove(link)
        except Exception:
            pass

def _ensure_link(tree, out_sock, in_sock, clear_input=False):
    if tree is None or out_sock is None or in_sock is None:
        return

    if clear_input:
        _clear_input_links(tree, in_sock)

    for link in getattr(in_sock, "links", []):
        if getattr(link, "from_socket", None) == out_sock:
            return
    _link(tree, out_sock, in_sock)

def _socket_default_value(sock, fallback=None):
    if sock is None or not hasattr(sock, "default_value"):
        return fallback
    try:
        value = sock.default_value
    except Exception:
        return fallback

    try:
        return value.copy()
    except Exception:
        pass

    if isinstance(value, (list, tuple)):
        return tuple(value)
    return value

def _copy_transform_settings(src_node, dst_node):
    if src_node is None or dst_node is None:
        return

    for attr in ("representation", "apply_mode", "interpolation", "easing"):
        if not hasattr(src_node, attr) or not hasattr(dst_node, attr):
            continue
        try:
            setattr(dst_node, attr, getattr(src_node, attr))
        except Exception:
            pass

    for sock_name in ("Translation", "Rotation", "Scale", "Matrix"):
        src_sock = getattr(src_node, "inputs", {}).get(sock_name)
        dst_sock = getattr(dst_node, "inputs", {}).get(sock_name)
        if src_sock is None or dst_sock is None or not hasattr(dst_sock, "default_value"):
            continue
        value = _socket_default_value(src_sock)
        if value is None:
            continue
        try:
            dst_sock.default_value = value
        except Exception:
            pass

def _collect_transform_tracks(tree, scene=None):
    tracks_by_bone = {}
    node_cache = {}
    stack = set()
    eval_state = _new_timekey_eval_state(scene=scene)

    for node in getattr(tree, "nodes", []):
        if getattr(node, "bl_idname", "") != "DefineBoneTransformNode":
            continue

        bone_in = getattr(node, "inputs", {}).get("Bone")
        if bone_in is None or not getattr(bone_in, "is_linked", False) or not bone_in.links:
            continue

        link = bone_in.links[0]
        bone_out = getattr(link, "from_socket", None)
        bone_node = getattr(bone_out, "node", None)
        if bone_out is None or bone_node is None:
            continue
        if getattr(bone_node, "bl_idname", "") != "DefineBoneNode":
            continue

        bone_key = bone_node.as_pointer()
        track = tracks_by_bone.setdefault(
            bone_key,
            {
                "bone_node": bone_node,
                "bone_out": bone_out,
                "bone_name": str(getattr(bone_out, "bone_name", "") or "").strip(),
                "nodes": [],
            },
        )

        start = _resolve_int_input(
            getattr(node, "inputs", {}).get("Start"),
            node_cache,
            stack,
            eval_state=eval_state,
            current_tree=tree,
        )
        end_value = _resolve_transform_end(
            node,
            node_cache,
            stack,
            eval_state=eval_state,
            current_tree=tree,
        )
        track["nodes"].append(
            {
                "node": node,
                "start": int(start),
                "end": int(end_value),
            }
        )

    tracks = []
    for track in tracks_by_bone.values():
        track["nodes"].sort(
            key=lambda item: (
                int(item.get("start", 0)),
                int(item.get("end", 0)),
                float(getattr(item.get("node"), "location", (0.0, 0.0))[0]),
            )
        )
        tracks.append(track)
    return tracks

def _append_new_frames_to_tree(action, tree, context=None):
    if action is None or tree is None:
        return False

    eval_scene = getattr(context, "scene", None) if context is not None else None

    action_frames = _collect_action_time_frames(action, context=context)
    if not action_frames:
        return False

    tree_frames = collect_tree_timekeys(tree, scene=eval_scene)
    if not tree_frames:
        return False

    tree_frame_set = set(int(f) for f in tree_frames)
    action_frame_set = set(int(f) for f in action_frames)
    missing_frames = sorted(action_frame_set - tree_frame_set)
    if not missing_frames:
        return False

    target_frames = sorted(tree_frame_set | action_frame_set)
    if len(target_frames) == 1:
        target_ranges = [(target_frames[0], target_frames[0])]
    else:
        target_ranges = [
            (int(target_frames[i]), int(target_frames[i + 1]))
            for i in range(len(target_frames) - 1)
        ]
    if not target_ranges:
        return False

    tracks = _collect_transform_tracks(tree, scene=eval_scene)
    if not tracks:
        return False

    changed = False
    x_step = 280.0
    duration_eval_state = _new_timekey_eval_state(scene=eval_scene)

    for track in tracks:
        nodes = track.get("nodes", [])
        bone_out = track.get("bone_out")
        if not nodes or bone_out is None:
            continue

        existing_by_start = {}
        for item in nodes:
            start = int(item.get("start", 0))
            existing_by_start.setdefault(start, item["node"])

        bone_name = track.get("bone_name") or ""
        display_name = bone_name or str(getattr(track.get("bone_node"), "label", "") or "Unassigned")

        planned = []
        source_node = nodes[-1]["node"]

        for idx, (start, end_value) in enumerate(target_ranges):
            node = existing_by_start.get(int(start))
            if node is None:
                node = tree.nodes.new("DefineBoneTransformNode")
                _copy_transform_settings(source_node, node)
                changed = True

                if planned:
                    prev_node = planned[-1][0]
                    try:
                        node.location = (float(prev_node.location[0]) + x_step, float(prev_node.location[1]))
                    except Exception:
                        pass
                else:
                    try:
                        node.location = (float(source_node.location[0]) + x_step, float(source_node.location[1]))
                    except Exception:
                        pass

            planned.append((node, int(start), int(end_value)))
            source_node = node

        for idx, (node, start, end_value) in enumerate(planned):
            try:
                node.name = f"{display_name} [{int(start)}-{int(end_value)}]"
            except Exception:
                pass
            try:
                node.label = f"{display_name} {int(start)}->{int(end_value)}"
            except Exception:
                pass

            _ensure_link(tree, bone_out, getattr(node, "inputs", {}).get("Bone"), clear_input=True)

            start_in = getattr(node, "inputs", {}).get("Start")
            if idx == 0:
                _clear_input_links(tree, start_in)
                _set_node_input_default(node, "Start", int(start))
            else:
                prev_node = planned[idx - 1][0]
                _ensure_link(tree, getattr(prev_node, "outputs", {}).get("End"), start_in, clear_input=True)

            wanted_duration = max(0, int(end_value) - int(start))
            current_duration = _resolve_int_input(
                getattr(node, "inputs", {}).get("Duration"),
                {},
                set(),
                eval_state=duration_eval_state,
                current_tree=tree,
            )
            if current_duration != wanted_duration:
                changed = True
            _set_node_input_default(node, "Duration", int(wanted_duration))

    if changed:
        try:
            tree.update_tag()
        except Exception:
            pass
    return changed

def sync_tree_from_action_timekeys(action, tree, context=None):
    if action is None or tree is None:
        return False

    if not _tree_has_user_nodes(tree):
        before_nodes = len(getattr(tree, "nodes", []))
        _import_tree_from_action_timekeys(action, tree, context=context)
        return len(getattr(tree, "nodes", [])) != before_nodes

    return _append_new_frames_to_tree(action, tree, context=context)

def _empty_transform_channels():
    return {
        "location": {},
        "rotation_euler": {},
        "rotation_quaternion": {},
        "rotation_axis_angle": {},
        "scale": {},
    }

def _group_timekey_entries_by_bone(entries):
    grouped = {}

    for entry in entries:
        frame = _extract_scalar_int(entry.get("frame"))
        if frame is None:
            continue

        bone_name = str(entry.get("bone_name", "") or "").strip()
        rec = grouped.setdefault(bone_name, {"frames": set(), "entries_by_frame": {}})
        rec["frames"].add(int(frame))
        rec["entries_by_frame"].setdefault(int(frame), []).append(entry)

        end_frame = _extract_scalar_int(entry.get("end_frame"))
        if end_frame is not None:
            rec["frames"].add(int(end_frame))
            continue

        duration = _extract_scalar_int(entry.get("duration"))
        if duration is not None:
            rec["frames"].add(int(frame) + max(0, int(duration)))

    return grouped

def _entry_for_frame(entry_meta, frame):
    if not entry_meta:
        return None
    values = entry_meta.get("entries_by_frame", {}).get(int(frame), [])
    return values[0] if values else None

def _entry_explicit_end(entry, start):
    if not entry:
        return None

    end_frame = _extract_scalar_int(entry.get("end_frame"))
    if end_frame is not None:
        return max(int(start), int(end_frame))

    duration = _extract_scalar_int(entry.get("duration"))
    if duration is not None:
        return int(start) + max(0, int(duration))

    return None

def _pick_entry_vector(entry, key):
    if not entry:
        return None
    vec = entry.get(key)
    if vec is None:
        return None
    return _extract_vector3(vec)

def _import_tree_from_action_timekeys(action, tree, context=None):
    if action is None or tree is None:
        return
    if _tree_has_user_nodes(tree):
        return

    time_frames = _collect_action_time_frames(action, context=context)
    timekey_entries = _collect_timekey_entries_from_action_properties(action)
    entry_tracks = _group_timekey_entries_by_bone(timekey_entries)
    bones = _collect_bone_fcurves(action, context=context)
    if not bones and not time_frames and not entry_tracks:
        return

    arm_obj = _find_action_armature(action, context=context)
    base_x = -700.0
    base_y = 0.0
    row_step = -260.0
    col_step = 280.0

    tracks = []
    all_bones = set(bones.keys()) | set(entry_tracks.keys())
    if not all_bones and time_frames:
        all_bones.add("")

    use_global_time_frames = not bool(entry_tracks)

    for bone_name in sorted(all_bones):
        data = bones.get(bone_name)
        if data is None:
            data = _empty_transform_channels()
            data["frames"] = set()

        entry_meta = entry_tracks.get(bone_name)
        frames = set(int(f) for f in data.get("frames", []))

        if entry_meta is not None:
            frames |= set(int(f) for f in entry_meta.get("frames", []))
        elif use_global_time_frames and time_frames:
            frames |= set(int(f) for f in time_frames)

        frames = sorted(frames)
        if not frames:
            continue

        tracks.append((bone_name, data, frames, entry_meta))

    for row_idx, (bone_name, data, frames, entry_meta) in enumerate(tracks):
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
            start = frames[0]
            end = start
            explicit_end = _entry_explicit_end(_entry_for_frame(entry_meta, start), start)
            if explicit_end is not None:
                end = explicit_end
            ranges.append((start, end))
        else:
            for idx in range(len(frames) - 1):
                start = frames[idx]
                end = frames[idx + 1]

                explicit_end = _entry_explicit_end(_entry_for_frame(entry_meta, start), start)
                if explicit_end is not None:
                    end = explicit_end

                ranges.append((start, end))

        prev_transform = None
        for col_idx, (start, end) in enumerate(ranges):
            transform = tree.nodes.new("DefineBoneTransformNode")
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

            entry_end = _entry_for_frame(entry_meta, end)
            entry_start = _entry_for_frame(entry_meta, start)

            loc = _pick_entry_vector(entry_end, "location")
            if loc is None:
                loc = _pick_entry_vector(entry_start, "location")

            rot = _pick_entry_vector(entry_end, "rotation")
            if rot is None:
                rot = _pick_entry_vector(entry_start, "rotation")

            scale = _pick_entry_vector(entry_end, "scale")
            if scale is None:
                scale = _pick_entry_vector(entry_start, "scale")

            if loc is None or rot is None or scale is None:
                eval_loc, eval_rot, eval_scale = _evaluate_bone_target(data, int(end))
                if loc is None:
                    loc = eval_loc
                if rot is None:
                    rot = eval_rot
                if scale is None:
                    scale = eval_scale

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

def _find_timekey_fcurve(action, context=None):
    fcurve, _ = _find_any_timekey_fcurve(action, context=context)
    return fcurve

def _fcurve_key_frames(fcurve):
    out = []
    for key in getattr(fcurve, "keyframe_points", []):
        try:
            out.append(int(round(float(key.co[0]))))
        except Exception:
            pass
    return sorted(set(out))

def _group_env_key(group_env):
    if not group_env:
        return ()

    out = []
    cur = group_env
    while cur:
        node = cur.get("group_node")
        out.append(_pointer_uid(node) if node is not None else None)
        cur = cur.get("parent_env")
    return tuple(out)

def _coerce_int_scalar(value, fallback=0):
    try:
        return int(round(float(value)))
    except Exception:
        return int(fallback)

def _resolve_timekey_scene(scene=None):
    if scene is not None:
        return scene
    try:
        return bpy.context.scene
    except Exception:
        return None

def _new_timekey_eval_state(scene=None):
    return SimpleNamespace(
        scene=_resolve_timekey_scene(scene),
        contexts={},
        seeded_group_inputs=set(),
        seeding_group_inputs=set(),
    )

def _timekey_eval_scope_key(current_tree, group_env):
    return (_pointer_uid(current_tree), _group_env_key(group_env))

def _timekey_eval_ctx(eval_state, current_tree, group_env):
    if eval_state is None:
        return None

    scope_key = _timekey_eval_scope_key(current_tree, group_env)
    ctx = eval_state.contexts.get(scope_key)
    if ctx is None:
        ctx = SimpleNamespace(
            eval_cache=set(),
            pose_cache={},
            touched_armatures=set(),
            values={},
            eval_stack=set(),
        )
        eval_state.contexts[scope_key] = ctx
    return ctx

def _socket_index(sockets, needle):
    if sockets is None:
        return -1

    try:
        iterator = iter(sockets)
    except Exception:
        return -1

    for idx, sock in enumerate(iterator):
        if sock == needle:
            return idx
        try:
            if sock.as_pointer() == needle.as_pointer():
                return idx
        except Exception:
            pass
    return -1

def _active_group_output_node(tree):
    outputs = [n for n in getattr(tree, "nodes", []) if getattr(n, "type", "") == "GROUP_OUTPUT"]
    if not outputs:
        return None
    for node in outputs:
        if getattr(node, "is_active_output", False):
            return node
    return outputs[0]

def _resolve_group_input_source(group_input_node, from_sock, group_env):
    if not group_env:
        return (None, None)

    group_node = group_env.get("group_node")
    if group_node is None:
        return (None, None)

    idx = _socket_index(getattr(group_input_node, "outputs", []), from_sock)
    if idx < 0:
        return (None, None)

    group_inputs = getattr(group_node, "inputs", [])
    if idx >= len(group_inputs):
        return (None, None)

    return (group_inputs[idx], group_env.get("parent_env"))

def _resolve_group_output_source(group_node, from_sock, group_env):
    subtree = getattr(group_node, "node_tree", None)
    if not subtree or getattr(subtree, "bl_idname", "") != "AnimNodeTree":
        return (None, None)

    out_idx = _socket_index(getattr(group_node, "outputs", []), from_sock)
    if out_idx < 0:
        return (None, None)

    group_output = _active_group_output_node(subtree)
    if group_output is None:
        return (None, None)

    group_output_inputs = getattr(group_output, "inputs", [])
    if out_idx >= len(group_output_inputs):
        return (None, None)

    sub_in = group_output_inputs[out_idx]
    sub_env = {
        "group_node": group_node,
        "parent_env": group_env,
        "tree": getattr(group_node, "id_data", None),
    }
    return (sub_in, sub_env)

def _seed_group_input_runtime_values(tree, group_env, node_cache, stack, group_stack, eval_state, eval_ctx):
    if tree is None or eval_state is None:
        return

    seed_key = (_pointer_uid(tree), _group_env_key(group_env))
    if seed_key in eval_state.seeded_group_inputs or seed_key in eval_state.seeding_group_inputs:
        return

    eval_state.seeding_group_inputs.add(seed_key)
    try:
        for node in getattr(tree, "nodes", []):
            if getattr(node, "type", "") != "GROUP_INPUT":
                continue

            for out_sock in getattr(node, "outputs", []):
                if getattr(out_sock, "bl_idname", "") != "NodeSocketInt":
                    continue

                value = getattr(out_sock, "default_value", 0)
                if group_env:
                    parent_sock, parent_env = _resolve_group_input_source(node, out_sock, group_env)
                    if parent_sock is not None:
                        value = _resolve_int_input(
                            parent_sock,
                            node_cache,
                            stack,
                            group_env=parent_env,
                            group_stack=group_stack,
                            eval_state=eval_state,
                            current_tree=group_env.get("tree"),
                        )

                eval_ctx.values[(node.as_pointer(), out_sock.name)] = _coerce_int_scalar(value, 0)
    finally:
        eval_state.seeding_group_inputs.discard(seed_key)
        eval_state.seeded_group_inputs.add(seed_key)

def _resolve_linked_socket_int(from_sock, node_cache, stack, group_env, group_stack, eval_state, current_tree):
    fallback = getattr(from_sock, "default_value", 0)
    node = getattr(from_sock, "node", None)
    if eval_state is None or node is None:
        return _coerce_int_scalar(fallback, 0)

    node_type = getattr(node, "bl_idname", "")
    if node_type in {"DefineBoneTransformNode", "DefineBonePropertyNode", "AnimNodeGroup"}:
        return _coerce_int_scalar(fallback, 0)

    eval_ctx = _timekey_eval_ctx(eval_state, current_tree, group_env)
    if eval_ctx is None:
        return _coerce_int_scalar(fallback, 0)

    try:
        _seed_group_input_runtime_values(
            current_tree,
            group_env,
            node_cache,
            stack,
            group_stack,
            eval_state,
            eval_ctx,
        )
    except Exception:
        pass

    eval_tree = getattr(node, "id_data", None) or current_tree
    scene = eval_state.scene
    if eval_tree is not None and scene is not None:
        try:
            if hasattr(node, "eval_upstream"):
                node.eval_upstream(eval_tree, scene, eval_ctx)
            else:
                fn = getattr(node, "evaluate", None)
                if callable(fn):
                    fn(eval_tree, scene, eval_ctx)
        except Exception:
            pass

    value = eval_ctx.values.get((node.as_pointer(), from_sock.name), fallback)
    return _coerce_int_scalar(value, 0)

def _resolve_int_input(sock, node_cache, stack, group_env=None, group_stack=None, eval_state=None, current_tree=None):
    if sock is None:
        return 0

    if group_stack is None:
        group_stack = set()

    if getattr(sock, "is_linked", False) and sock.links:
        from_sock = sock.links[0].from_socket
        node = getattr(from_sock, "node", None)

        if (
            node
            and getattr(node, "bl_idname", "") in {"DefineBoneTransformNode", "DefineBonePropertyNode"}
            and from_sock.name == "End"
        ):
            return _resolve_transform_end(
                node,
                node_cache,
                stack,
                group_env=group_env,
                group_stack=group_stack,
                eval_state=eval_state,
                current_tree=current_tree,
            )

        if node and getattr(node, "type", "") == "GROUP_INPUT":
            parent_sock, parent_env = _resolve_group_input_source(node, from_sock, group_env)
            if parent_sock is not None:
                return _resolve_int_input(
                    parent_sock,
                    node_cache,
                    stack,
                    group_env=parent_env,
                    group_stack=group_stack,
                    eval_state=eval_state,
                    current_tree=group_env.get("tree") if group_env else None,
                )

        if node and getattr(node, "bl_idname", "") == "AnimNodeGroup":
            guard = (
                _pointer_uid(node),
                getattr(from_sock, "name", ""),
                _group_env_key(group_env),
            )
            if guard not in group_stack:
                group_stack.add(guard)
                try:
                    sub_sock, sub_env = _resolve_group_output_source(node, from_sock, group_env)
                    if sub_sock is not None:
                        return _resolve_int_input(
                            sub_sock,
                            node_cache,
                            stack,
                            group_env=sub_env,
                            group_stack=group_stack,
                            eval_state=eval_state,
                            current_tree=getattr(node, "node_tree", None),
                        )
                finally:
                    group_stack.discard(guard)

        return _resolve_linked_socket_int(
            from_sock,
            node_cache,
            stack,
            group_env,
            group_stack,
            eval_state,
            current_tree,
        )

    return _coerce_int_scalar(getattr(sock, "default_value", 0), 0)

def _resolve_transform_end(node, node_cache, stack, group_env=None, group_stack=None, eval_state=None, current_tree=None):
    cache_key = (_pointer_uid(node), _group_env_key(group_env))
    if cache_key in node_cache:
        return node_cache[cache_key]
    if cache_key in stack:
        return _coerce_int_scalar(getattr(node.outputs.get("End"), "default_value", 0), 0)

    stack.add(cache_key)
    try:
        start = _resolve_int_input(
            node.inputs.get("Start"),
            node_cache,
            stack,
            group_env=group_env,
            group_stack=group_stack,
            eval_state=eval_state,
            current_tree=current_tree,
        )
        duration = _resolve_int_input(
            node.inputs.get("Duration"),
            node_cache,
            stack,
            group_env=group_env,
            group_stack=group_stack,
            eval_state=eval_state,
            current_tree=current_tree,
        )
        end_value = int(start + max(0, duration))
    finally:
        stack.discard(cache_key)

    node_cache[cache_key] = end_value
    return end_value

def _collect_tree_timekeys_recursive(tree, keys, node_cache, stack, tree_stack, group_env=None, group_stack=None, eval_state=None):
    if tree is None:
        return

    tree_uid = _pointer_uid(tree)
    if tree_uid is None:
        tree_uid = id(tree)
    if tree_uid in tree_stack:
        return
    tree_stack.add(tree_uid)

    try:
        for node in getattr(tree, "nodes", []):
            bl_idname = getattr(node, "bl_idname", "")
            if bl_idname in {"DefineBoneTransformNode", "DefineBonePropertyNode"}:
                start = _resolve_int_input(
                    node.inputs.get("Start"),
                    node_cache,
                    stack,
                    group_env=group_env,
                    group_stack=group_stack,
                    eval_state=eval_state,
                    current_tree=tree,
                )
                duration = _resolve_int_input(
                    node.inputs.get("Duration"),
                    node_cache,
                    stack,
                    group_env=group_env,
                    group_stack=group_stack,
                    eval_state=eval_state,
                    current_tree=tree,
                )
                end_value = int(start + max(0, duration))

                keys.add(int(start))
                keys.add(int(end_value))
                continue

            if bl_idname != "AnimNodeGroup":
                continue

            subtree = getattr(node, "node_tree", None)
            if not subtree or getattr(subtree, "bl_idname", "") != "AnimNodeTree":
                continue

            sub_env = {"group_node": node, "parent_env": group_env, "tree": tree}
            _collect_tree_timekeys_recursive(
                subtree,
                keys,
                node_cache,
                stack,
                tree_stack,
                group_env=sub_env,
                group_stack=group_stack,
                eval_state=eval_state,
            )
    finally:
        tree_stack.discard(tree_uid)

def collect_tree_timekeys(tree, scene=None):
    if tree is None:
        return []

    keys = set()
    node_cache = {}
    stack = set()
    tree_stack = set()
    group_stack = set()
    eval_state = _new_timekey_eval_state(scene=scene)

    _collect_tree_timekeys_recursive(
        tree,
        keys,
        node_cache,
        stack,
        tree_stack,
        group_env=None,
        group_stack=group_stack,
        eval_state=eval_state,
    )

    return sorted(keys)

def _write_action_timekey_channel(action, frames, context=None):
    if action is None:
        return

    fcurve, _ = _find_any_timekey_fcurve(action, context=context)
    wanted = sorted(set(int(f) for f in frames))

    if not wanted and fcurve is None:
        return

    if fcurve is not None:
        current = _fcurve_key_frames(fcurve)
        if current == wanted:
            try:
                fcurve.hide = True
            except Exception:
                pass
            return

    if wanted:
        try:
            action["animgraph_time"] = float(wanted[0])
        except Exception:
            pass

    if fcurve is None and wanted:
        collection = _find_writable_fcurve_collection(action, context=context)
        try:
            if collection is not None:
                fcurve = collection.new(data_path=_TIMEKEY_CHANNEL_PATH, index=0, action_group="AnimGraph")
            else:
                fcurve = None
        except TypeError:
            try:
                if collection is not None:
                    fcurve = collection.new(data_path=_TIMEKEY_CHANNEL_PATH, index=0)
                else:
                    fcurve = None
            except Exception:
                fcurve = None
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

    try:
        fcurve.hide = True
    except Exception:
        pass

def _set_action_timekey_editable(action, editable):
    lock = not bool(editable)
    for fcurve in _iter_action_fcurves(action):
        try:
            if bool(getattr(fcurve, "lock", False)) != lock:
                fcurve.lock = lock
        except Exception:
            pass

def sync_action_timekeys_from_tree(action, tree, context=None):
    if action is None:
        return

    if tree is None:
        _set_action_timekey_editable(action, True)
        return

    eval_scene = getattr(context, "scene", None) if context is not None else None
    frames = collect_tree_timekeys(tree, scene=eval_scene)
    _write_action_timekey_channel(action, frames, context=context)
    _set_action_timekey_editable(action, False)

def sync_actions_for_tree(tree, context=None):
    if tree is None:
        return

    for action in bpy.data.actions:
        if getattr(action, "animgraph_tree", None) != tree:
            continue
        sync_action_inputs(action, tree)
        sync_action_timekeys_from_tree(action, tree, context=context)

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
