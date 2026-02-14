# animation_graph/Nodes/bone_node.py

import json
import bpy
from bpy.props import EnumProperty

from .Mixin import AnimGraphNodeMixin
from ..Core import sockets


def register():
    for c in _CLASSES: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_CLASSES): bpy.utils.unregister_class(c)

def _on_node_prop_update(self, context):
    try: self.update()
    except Exception: pass

    try:
        nt = getattr(self, "id_data", None)
        if nt: nt.update_tag()
    except Exception: pass

    try:
        if context and context.window and context.window.screen:
            for area in context.window.screen.areas:
                if area.type == "NODE_EDITOR":
                    area.tag_redraw()
    except Exception: pass


def _enum_bone_property_items(self, context):
    try: return self._property_items()
    except Exception: return [("", "(select bone first)", "Pick a linked/selected bone first.")]


class DefineBoneNode(bpy.types.Node, AnimGraphNodeMixin):
    bl_idname = "DefineBoneNode"
    bl_label = "Bone"
    bl_icon = "BONE_DATA"

    def init(self, context): self.outputs.new("NodeSocketBone","Bone")
    def draw_buttons(self, context, layout): pass

class _BoneProperty(bpy.types.Node, AnimGraphNodeMixin):
    bl_icon = "BONE_DATA"

    property_name: EnumProperty(
        name="Property",
        description="Property on the selected/linked pose bone",
        items=_enum_bone_property_items,
        update=_on_node_prop_update,
    )
    
    def init(self, context):
        self.inputs.new("NodeSocketBone", "Bone")

    def update(self):
        if getattr(self, "_syncing", False):
            return

        self._syncing = True
        try:
            self._ensure_property_selection()
            self._ensure_socket()
        finally: self._syncing = False

    def _ensure_property_selection(self):
        valid = [spec["id"] for spec in self._property_specs() if spec.get("id")]
        current = str(getattr(self, "property_name", "") or "")

        if current in valid: return

        new_value = valid[0] if valid else ""
        if current == new_value: return

        try: self.property_name = new_value
        except Exception: pass
    
    def _ensure_socket(self): pass
    def draw_buttons(self, context, layout): layout.prop(self, "property_name")

class DefineBonePropertyNode(_BoneProperty):
    bl_idname = "DefineBonePropertyNode"
    bl_label = "Bone Property"
    _ARRAY_SOCKET_NAMES = ("Value X", "Value Y", "Value Z")

    def init(self, context):
        super().init(context)

        s = self.inputs.new("NodeSocketInt", "Start")
        d = self.inputs.new("NodeSocketInt", "Duration")
        try:
            s.default_value = 0
            d.default_value = 10
        except Exception: pass

        self.outputs.new("NodeSocketInt", "End")
        self.update()

    def update(self): super().update()
        # if getattr(self, "_syncing", False):
        #     return

        # self._syncing = True
        # try:
        #     self._ensure_property_selection()
        #     self._ensure_value_socket()
        # finally:
        #     self._syncing = False

    def evaluate(self, tree, scene, ctx):
        arm_ob, bone_name = self.socket_bone_ref("Bone")
        if not arm_ob or getattr(arm_ob, "type", "") != "ARMATURE" or not bone_name:
            return

        pbone = arm_ob.pose.bones.get(bone_name)
        if not pbone:
            return

        spec = self._selected_property_spec()
        if spec is None:
            return
        prop_current = self._read_property_value(pbone, spec)
        if prop_current is None:
            return

        prop_id = str(spec.get("id", "") or "")
        kind = str(spec.get("kind", "") or "")
        if not kind:
            return

        start = int(self.socket_int(tree, "Start", scene, ctx, 0))
        duration = int(self.socket_int(tree, "Duration", scene, ctx, 10))
        duration = max(0, duration)
        frame = int(scene.frame_current)
        end_value = int(start + duration)

        out_end = self.outputs.get("End")
        if out_end:
            try:
                out_end.default_value = int(end_value)
            except Exception: pass
        self.set_output_value(ctx, "End", int(end_value))

        cache_key = (
            "BONE_PROPERTY",
            tree.as_pointer(),
            self.as_pointer(),
            arm_ob.as_pointer(),
            bone_name,
            prop_id,
            start,
            duration,
        )

        if frame < start:
            ctx.pose_cache.pop(cache_key, None)
            return

        current_value = self._coerce_for_kind(prop_current, kind, prop_current)
        if self._uses_array_value_sockets(kind, current_value):
            current_value = self._array_defaults(kind, current_value)
        if self._uses_array_value_sockets(kind, current_value):
            target = self._array_target_from_sockets(tree, scene, ctx, kind, current_value)
        else:
            value_socket = self.inputs.get("Value")
            raw_target = self.eval_socket(tree, value_socket, scene, ctx) if value_socket else current_value
            target = self._coerce_for_kind(raw_target, kind, current_value)

        state = ctx.pose_cache.get(cache_key)
        if state is None:
            state = {
                "start_value": _clone_value(current_value),
            }
            ctx.pose_cache[cache_key] = state
        start_value = state.get("start_value", current_value)

        if duration <= 0:
            t = 1.0
        else:
            t = (frame - start) / float(duration)
            if t < 0.0:
                t = 0.0
            if t > 1.0:
                t = 1.0

        if kind == "BOOL":
            value_out = bool(target if t >= 1.0 else start_value)
        elif kind == "INT":
            value_out = int(round((1.0 - t) * int(start_value) + t * int(target)))
        elif kind == "FLOAT":
            value_out = float((1.0 - t) * float(start_value) + t * float(target))
        elif kind in {"INT_ARRAY", "FLOAT_ARRAY"}:
            value_out = _lerp_numeric_sequence(start_value, target, t)
            value_out = self._array_defaults(kind, value_out)
        elif kind == "BOOL_ARRAY":
            value_out = self._array_defaults(kind, target if t >= 1.0 else start_value)
        elif kind in {"STRING", "DATA_BLOCK", "PYTHON"}:
            value_out = _clone_value(target if t >= 1.0 else start_value)
        else:
            value_out = _clone_value(target if t >= 1.0 else start_value)

        try:
            if not self._write_property_value(pbone, spec, value_out): return
            ctx.touched_armatures.add(arm_ob)
        except Exception: pass

    def _ensure_socket(self): self._ensure_value_socket()

    def _pose_bone_ref(self):
        arm_ob, bone_name = self.socket_bone_ref("Bone")
        if not arm_ob or getattr(arm_ob, "type", "") != "ARMATURE" or not bone_name:
            return None, ""
        pose = getattr(arm_ob, "pose", None)
        if pose is None: return None, ""
        return pose.bones.get(bone_name), bone_name

    def _uses_array_value_sockets(self, kind, value=None):
        kind = str(kind or "")
        return kind in {"BOOL_ARRAY", "INT_ARRAY", "FLOAT_ARRAY"}

    def _array_socket_type_for_property(self, kind, value):
        kind = str(kind or "")
        if kind.endswith("_ARRAY"):
            base = kind.removesuffix("_ARRAY")
            if base == "BOOL":
                return sockets._S("BOOL")
            if base == "INT":
                return sockets._S("INT")
            if base == "FLOAT":
                return sockets._S("FLOAT")
        return None

    def _array_defaults(self, kind, value):
        sock_type = self._array_socket_type_for_property(kind, value)
        use_int = sock_type == sockets._S("INT")
        use_bool = sock_type == sockets._S("BOOL")

        seq = list(_to_sequence(value) or [])

        out = []
        for idx in range(3):
            raw = seq[idx] if idx < len(seq) else (False if use_bool else (0 if use_int else 0.0))
            if use_bool:
                out.append(_coerce_bool(raw, False))
            elif use_int:
                out.append(_coerce_int(raw, 0))
            else:
                out.append(_coerce_float(raw, 0.0))
        return out

    def _array_target_from_sockets(self, tree, scene, ctx, kind, fallback):
        defaults = self._array_defaults(kind, fallback)
        use_int = self._array_socket_type_for_property(kind, fallback) == sockets._S("INT")
        use_bool = self._array_socket_type_for_property(kind, fallback) == sockets._S("BOOL")

        out = []
        for idx, name in enumerate(self._ARRAY_SOCKET_NAMES):
            sock = self.inputs.get(name)
            raw_value = self.eval_socket(tree, sock, scene, ctx) if sock is not None else defaults[idx]
            if use_bool:
                out.append(_coerce_bool(raw_value, defaults[idx]))
            elif use_int:
                out.append(_coerce_int(raw_value, defaults[idx]))
            else:
                out.append(_coerce_float(raw_value, defaults[idx]))
        return out

    def _property_items(self):
        pbone, _ = self._pose_bone_ref()
        if pbone is None:
            return [("", "(select bone first)", "Pick a linked/selected bone first.")]

        specs = self._property_specs()
        if not specs:
            return [("", "(no custom properties)", "No custom properties found on this bone.")]
        return [(spec["id"], spec["label"], spec["description"]) for spec in specs]

    def _property_specs(self):
        pbone, _ = self._pose_bone_ref()
        if pbone is None:
            return []

        specs = []

        try:
            keys = list(pbone.keys())
        except Exception:
            keys = []

        for key in keys:
            key_str = str(key)
            if key_str == "_RNA_UI":
                continue
            try:
                value = pbone[key_str]
            except Exception:
                continue

            kind = _property_kind_from_value(value)

            specs.append(
                {
                    "id": f"POSE_IDP:{key_str}",
                    "source": "POSE_IDP",
                    "key": key_str,
                    "kind": kind,
                    "label": f"{key_str} ({kind.lower()}, pose custom)",
                    "description": f"Pose bone custom property '{key_str}' ({kind.lower()})",
                }
            )

        try:
            data_bone = getattr(pbone, "bone", None)
        except Exception:
            data_bone = None

        if data_bone is not None:
            try:
                data_keys = list(data_bone.keys())
            except Exception:
                data_keys = []

            for key in data_keys:
                key_str = str(key)
                if key_str == "_RNA_UI":
                    continue
                try:
                    value = data_bone[key_str]
                except Exception:
                    continue

                kind = _property_kind_from_value(value)

                specs.append(
                    {
                        "id": f"BONE_IDP:{key_str}",
                        "source": "BONE_IDP",
                        "key": key_str,
                        "kind": kind,
                        "label": f"{key_str} ({kind.lower()}, bone custom)",
                        "description": f"Bone-data custom property '{key_str}' ({kind.lower()})",
                    }
                )

        specs.sort(key=lambda spec: spec["label"].lower())
        return specs

    def _selected_property_spec(self):
        selected = str(getattr(self, "property_name", "") or "").strip()
        if not selected:
            return None
        for spec in self._property_specs():
            if spec["id"] == selected:
                return spec
        return None

    def _read_property_value(self, pbone, spec):
        if pbone is None or not spec:
            return None
        key = spec.get("key")
        if not key:
            return None
        source = spec.get("source")
        if source == "BONE_IDP":
            try:
                data_bone = getattr(pbone, "bone", None)
                if data_bone is None:
                    return None
                return data_bone[key]
            except Exception:
                return None
        try:
            return pbone[key]
        except Exception:
            return None

    def _write_property_value(self, pbone, spec, value):
        if pbone is None or not spec:
            return False
        key = spec.get("key")
        if not key:
            return False
        try:
            if spec.get("source") == "BONE_IDP":
                data_bone = getattr(pbone, "bone", None)
                if data_bone is None:
                    return False
                data_bone[key] = value
            else:
                pbone[key] = value
            return True
        except Exception:
            return False

    def _current_property_kind(self):
        spec = self._selected_property_spec()
        if spec is None:
            return None
        return spec.get("kind")

    def _current_property_value(self):
        pbone, _ = self._pose_bone_ref()
        if pbone is None:
            return None
        spec = self._selected_property_spec()
        return self._read_property_value(pbone, spec)

    def _coerce_for_kind(self, value, kind, fallback):
        if kind == "BOOL":
            return _coerce_bool(value, fallback)
        if kind == "INT":
            return _coerce_int(value, fallback)
        if kind == "FLOAT":
            return _coerce_float(value, fallback)
        if kind == "STRING":
            return _coerce_string(value, fallback)
        if str(kind).endswith("_ARRAY"):
            fb = self._array_defaults(kind, fallback)
            candidate = _parse_json_text(value, fallback=value)
            seq = _to_sequence(candidate)
            if seq is None:
                seq = fb

            out = []
            base = str(kind).removesuffix("_ARRAY")
            for idx in range(3):
                raw = seq[idx] if idx < len(seq) else fb[idx]
                if base == "BOOL":
                    out.append(_coerce_bool(raw, fb[idx]))
                elif base == "INT":
                    out.append(_coerce_int(raw, fb[idx]))
                else:
                    out.append(_coerce_float(raw, fb[idx]))
            return out
        if kind == "DATA_BLOCK":
            return _coerce_data_block(value, fallback)
        if kind == "PYTHON":
            return _clone_value(value if value is not None else fallback)
        return fallback

    def _ensure_value_socket(self):
        kind = self._current_property_kind()
        prop_value = self._current_property_value()

        if self._uses_array_value_sockets(kind, prop_value):
            comp_type = self._array_socket_type_for_property(kind, prop_value)
            wanted = [(name, comp_type) for name in self._ARRAY_SOCKET_NAMES if comp_type]
        else:
            wanted_type = _socket_type_for_kind(kind)
            wanted = [("Value", wanted_type)] if wanted_type else []

        dynamic_names = {"Value", *self._ARRAY_SOCKET_NAMES}
        wanted_by_name = {name: sock_type for name, sock_type in wanted}
        kept = set()

        for sock in list(self.inputs):
            name = str(getattr(sock, "name", "") or "")
            if name not in dynamic_names:
                continue

            sock_type = wanted_by_name.get(name)
            keep = (
                sock_type is not None
                and getattr(sock, "bl_idname", "") == sock_type
                and name not in kept
            )
            if keep:
                kept.add(name)
                continue

            try:
                self.inputs.remove(sock)
            except Exception:
                pass

        if self._uses_array_value_sockets(kind, prop_value):
            defaults = self._array_defaults(kind, prop_value)
            for idx, (name, sock_type) in enumerate(wanted):
                sock = self.inputs.get(name)
                if sock is not None:
                    continue
                sock = self.inputs.new(sock_type, name)
                try:
                    sock.default_value = defaults[idx]
                except Exception:
                    pass
            return

        if not wanted:
            return

        current_socket = self.inputs.get("Value")
        if current_socket is None:
            current_socket = self.inputs.new(wanted[0][1], "Value")
            self._set_socket_default_for_kind(current_socket, kind, prop_value)

    def _value_as_socket_payload(self, kind, value):
        if kind == "BOOL":
            return bool(_coerce_bool(value, False))
        if kind == "INT":
            return int(_coerce_int(value, 0))
        if kind == "FLOAT":
            return float(_coerce_float(value, 0.0))
        if kind == "STRING":
            return _coerce_string(value, "")
        if kind == "DATA_BLOCK":
            return _data_block_to_text(value)
        if kind == "PYTHON":
            return _json_text(value, "")
        return value

    def _set_socket_default_for_kind(self, sock, kind, value):
        if sock is None or not hasattr(sock, "default_value"):
            return
        try:
            sock.default_value = self._value_as_socket_payload(kind, value)
        except Exception:
            pass

class ReadBonePropertyNode(_BoneProperty):
    bl_idname = "ReadBonePropertyNode"
    bl_label = "Read Bone Property"

    def init(self, context):
        super().init(context)
        frame = self.inputs.new("NodeSocketInt", "Frame")
        try: frame.default_value = 0
        except Exception: pass
        self.outputs.new("NodeSocketFloat", "Value")
        self.update()

    def update(self): super().update()
        # if getattr(self, "_syncing", False):
        #     return

        # self._syncing = True
        # try:
        #     self._ensure_property_selection()
        #     self._ensure_output_socket()
        # finally:
        #     self._syncing = False

    # def draw_buttons(self, context, layout): layout.prop(self, "property_name")

    def evaluate(self, tree, scene, ctx):
        arm_ob, bone_name = self.socket_bone_ref("Bone")
        if not arm_ob or getattr(arm_ob, "type", "") != "ARMATURE" or not bone_name:
            return

        pbone = arm_ob.pose.bones.get(bone_name)
        if not pbone:
            return

        spec = self._selected_property_spec()
        if spec is None:
            return

        kind = str(spec.get("kind", "") or "")
        if not kind:
            return

        value_raw = self._read_property_value(pbone, spec)
        if value_raw is None:
            return

        value = self._coerce_for_kind(value_raw, kind, value_raw)
        frame_in = int(self.socket_int(tree, "Frame", scene, ctx, int(scene.frame_current)))
        cur_frame = int(scene.frame_current)
        if frame_in != cur_frame:
            value = self._sample_property_from_action(arm_ob, bone_name, spec, kind, frame_in, value)

        if self._uses_array_value_sockets(kind, value):
            array_value = self._array_defaults(kind, value)
            for idx, name in enumerate(self._ARRAY_SOCKET_NAMES):
                out = self.outputs.get(name)
                if out is not None:
                    try:
                        out.default_value = array_value[idx]
                    except Exception:
                        pass
                self.set_output_value(ctx, name, array_value[idx])
            return

        payload = self._value_as_socket_payload(kind, value)
        out = self.outputs.get("Value")
        if out:
            self._set_socket_default_for_kind(out, kind, value)
        self.set_output_value(ctx, "Value", payload)

    def _ensure_socket(self): self._ensure_output_socket()
    def _property_data_path(self, bone_name, spec):
        key = str(spec.get("key", "") or "")
        if not key:
            return ""

        if spec.get("source") == "BONE_IDP":
            return f'pose.bones["{bone_name}"].bone["{key}"]'
        return f'pose.bones["{bone_name}"]["{key}"]'

    def _sample_property_from_action(self, arm_ob, bone_name, spec, kind, frame, fallback):
        action = getattr(getattr(arm_ob, "animation_data", None), "action", None)
        if action is None:
            return fallback

        data_path = self._property_data_path(bone_name, spec)
        if not data_path:
            return fallback

        curves = []
        try:
            curves = [fc for fc in getattr(action, "fcurves", []) if getattr(fc, "data_path", "") == data_path]
        except Exception:
            curves = []

        if not curves:
            return fallback

        by_index = {}
        for fc in curves:
            idx = int(getattr(fc, "array_index", 0))
            if idx not in by_index:
                by_index[idx] = fc

        def _eval_idx(idx, fb):
            fc = by_index.get(idx)
            if fc is None:
                return fb
            try:
                return fc.evaluate(float(frame))
            except Exception:
                return fb

        if kind == "BOOL":
            v = _eval_idx(0, 1.0 if _coerce_bool(fallback, False) else 0.0)
            return bool(float(v) >= 0.5)

        if kind == "INT":
            v = _eval_idx(0, _coerce_int(fallback, 0))
            return _coerce_int(v, fallback)

        if kind == "FLOAT":
            v = _eval_idx(0, _coerce_float(fallback, 0.0))
            return _coerce_float(v, fallback)

        if kind.endswith("_ARRAY"):
            base = self._coerce_for_kind(fallback, kind, fallback)
            seq = _to_sequence(base) or []
            wanted_len = 3

            if wanted_len <= 0:
                return base

            if len(seq) < wanted_len:
                seq = list(seq) + [0.0] * (wanted_len - len(seq))
            else:
                seq = list(seq[:wanted_len])

            for idx in range(wanted_len):
                seq[idx] = _eval_idx(idx, seq[idx])

            if kind == "BOOL_ARRAY":
                return [bool(float(v) >= 0.5) for v in seq[:3]]
            if kind == "INT_ARRAY":
                return [_coerce_int(v, 0) for v in seq]
            return [_coerce_float(v, 0.0) for v in seq]

        return fallback

    def _ensure_output_socket(self):
        kind = self._current_property_kind()
        prop_value = self._current_property_value()

        if self._uses_array_value_sockets(kind, prop_value):
            comp_type = self._array_socket_type_for_property(kind, prop_value)
            wanted = [(name, comp_type) for name in self._ARRAY_SOCKET_NAMES if comp_type]
        else:
            wanted_type = _socket_type_for_kind(kind)
            wanted = [("Value", wanted_type)] if wanted_type else []

        dynamic_names = {"Value", *self._ARRAY_SOCKET_NAMES}
        wanted_by_name = {name: sock_type for name, sock_type in wanted}
        kept = set()

        for sock in list(self.outputs):
            name = str(getattr(sock, "name", "") or "")
            if name not in dynamic_names:
                continue

            sock_type = wanted_by_name.get(name)
            keep = (
                sock_type is not None
                and getattr(sock, "bl_idname", "") == sock_type
                and name not in kept
            )
            if keep:
                kept.add(name)
                continue

            try:
                self.outputs.remove(sock)
            except Exception:
                pass

        if self._uses_array_value_sockets(kind, prop_value):
            defaults = self._array_defaults(kind, prop_value)
            for idx, (name, sock_type) in enumerate(wanted):
                sock = self.outputs.get(name)
                if sock is None:
                    sock = self.outputs.new(sock_type, name)
                try:
                    sock.default_value = defaults[idx]
                except Exception:
                    pass
            return

        if not wanted:
            return

        current_socket = self.outputs.get("Value")
        if current_socket is None:
            current_socket = self.outputs.new(wanted[0][1], "Value")
        self._set_socket_default_for_kind(current_socket, kind, prop_value)


def _property_kind_from_value(value):
    if isinstance(value, bool):
        return "BOOL"
    if isinstance(value, int):
        return "INT"
    if isinstance(value, float):
        return "FLOAT"
    if isinstance(value, str):
        return "STRING"

    seq = _to_sequence(value)
    if seq is not None:
        if len(seq) == 3 and all(isinstance(v, bool) for v in seq):
            return "BOOL_ARRAY"
        if len(seq) == 3 and all(isinstance(v, int) and not isinstance(v, bool) for v in seq):
            return "INT_ARRAY"
        if len(seq) == 3 and all(_is_number(v) for v in seq):
            return "FLOAT_ARRAY"

    try:
        if isinstance(value, bpy.types.ID):
            return "DATA_BLOCK"
    except Exception:
        pass

    return "PYTHON"


def _socket_type_for_kind(kind):
    kind = str(kind or "")
    if not kind:
        return None
    if kind.endswith("_ARRAY"):
        kind = kind.removesuffix("_ARRAY")
    if kind == "DATA_BLOCK":
        kind = "STRING"
    if kind == "PYTHON":
        kind = "STRING"
    return sockets._S(kind)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _to_sequence(value):
    if isinstance(value, (str, bytes, bytearray)):
        return None
    if _to_mapping_items(value) is not None:
        return None
    try:
        return list(value)
    except Exception:
        return None


def _to_mapping_items(value):
    try:
        return list(value.items())
    except Exception:
        return None


def _to_plain_data(value, _depth=0):
    if _depth > 12:
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    items = _to_mapping_items(value)
    if items is not None:
        out = {}
        for key, item_value in items:
            out[str(key)] = _to_plain_data(item_value, _depth + 1)
        return out

    seq = _to_sequence(value)
    if seq is not None:
        return [_to_plain_data(v, _depth + 1) for v in seq]

    return str(value)


def _json_text(value, fallback=""):
    try:
        return json.dumps(_to_plain_data(value), ensure_ascii=True)
    except Exception:
        try:
            return str(value)
        except Exception:
            return str(fallback)


def _parse_json_text(value, fallback=None):
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return fallback
    try:
        return json.loads(text)
    except Exception:
        return fallback


def _clone_value(value):
    if isinstance(value, list):
        return [_clone_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_clone_value(v) for v in value)
    if isinstance(value, dict):
        return {k: _clone_value(v) for k, v in value.items()}
    return value


def _coerce_bool(value, fallback=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        low = value.strip().lower()
        if low in {"1", "true", "yes", "on"}:
            return True
        if low in {"0", "false", "no", "off", ""}:
            return False
    try:
        return bool(value)
    except Exception:
        return bool(fallback)


def _coerce_int(value, fallback=0):
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return int(fallback)


def _coerce_float(value, fallback=0.0):
    try:
        return float(value)
    except Exception:
        return float(fallback)


def _coerce_string(value, fallback=""):
    if value is None:
        return str(fallback)
    try:
        return str(value)
    except Exception:
        return str(fallback)


def _coerce_data_block(value, fallback=None):
    try:
        if isinstance(value, bpy.types.ID):
            return value
    except Exception:
        pass
    return fallback


def _data_block_to_text(value):
    if value is None:
        return ""
    try:
        if isinstance(value, bpy.types.ID):
            type_name = str(getattr(value, "bl_rna", None).name if getattr(value, "bl_rna", None) else "ID")
            return f"{type_name}:{getattr(value, 'name_full', getattr(value, 'name', ''))}"
    except Exception:
        pass
    return str(value)


def _lerp_numeric_sequence(start_value, target_value, t):
    sseq = _to_sequence(start_value)
    tseq = _to_sequence(target_value)
    if sseq is None or tseq is None or len(sseq) != len(tseq):
        return _clone_value(target_value if t >= 1.0 else start_value)

    all_int = (
        all(isinstance(v, int) and not isinstance(v, bool) for v in sseq)
        and all(isinstance(v, int) and not isinstance(v, bool) for v in tseq)
    )

    out = []
    for a, b in zip(sseq, tseq):
        af = _coerce_float(a, 0.0)
        bf = _coerce_float(b, 0.0)
        v = (1.0 - t) * af + t * bf
        out.append(int(round(v)) if all_int else float(v))
    return out


_CLASSES = [
    DefineBoneNode,
    DefineBonePropertyNode,
    ReadBonePropertyNode,
]
