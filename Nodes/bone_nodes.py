# animation_graph/Nodes/bone_node.py

import json
import bpy
from bpy.props import EnumProperty
from .Mixin import AnimGraphNodeMixin


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


class DefineBoneNode(bpy.types.Node, AnimGraphNodeMixin):
    bl_idname = "DefineBoneNode"
    bl_label = "Bone"
    bl_icon = "BONE_DATA"

    def init(self, context): self.outputs.new("NodeSocketBone","Bone")
    def draw_buttons(self, context, layout): pass

class DefineBonePropertyNode(bpy.types.Node, AnimGraphNodeMixin):
    bl_idname = "DefineBonePropertyNode"
    bl_label = "Bone Property"
    bl_icon = "BONE_DATA"

    property_name: EnumProperty(
        name="Property",
        description="Property on the selected/linked pose bone",
        items=lambda self, context: self._enum_bone_properties(context),
        update=_on_node_prop_update,
    )

    def _pose_bone_ref(self):
        arm_ob, bone_name = self.socket_bone_ref("Bone")
        if not arm_ob or getattr(arm_ob, "type", "") != "ARMATURE" or not bone_name:
            return None, ""
        pose = getattr(arm_ob, "pose", None)
        if pose is None: return None, ""
        return pose.bones.get(bone_name), bone_name

    @staticmethod
    def _property_kind_from_value(value):
        if isinstance(value, bool):
            return "BOOL"
        if isinstance(value, int):
            return "INT"
        if isinstance(value, float):
            return "FLOAT"
        if isinstance(value, str):
            return "STRING"

        seq = DefineBonePropertyNode._to_sequence(value)
        if seq is not None:
            if all(DefineBonePropertyNode._is_number(v) for v in seq):
                if len(seq) == 3:
                    return "VECTOR3"
                if len(seq) == 16:
                    return "MATRIX16"
                return "ARRAY_NUMERIC"
            return "JSON"

        if DefineBonePropertyNode._to_mapping_items(value) is not None:
            return "JSON"

        return "JSON"

    @staticmethod
    def _socket_type_for_kind(kind):
        if kind == "BOOL":
            return "NodeSocketBool"
        if kind == "INT":
            return "NodeSocketInt"
        if kind == "FLOAT":
            return "NodeSocketFloat"
        if kind == "STRING":
            return "NodeSocketString"
        if kind == "VECTOR3":
            return "NodeSocketVectorXYZ"
        if kind == "MATRIX16":
            return "NodeSocketMatrix"
        if kind in {"ARRAY_NUMERIC", "JSON"}:
            return "NodeSocketString"
        return None

    @staticmethod
    def _is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @staticmethod
    def _to_sequence(value):
        if isinstance(value, (str, bytes, bytearray)):
            return None
        if DefineBonePropertyNode._to_mapping_items(value) is not None:
            return None
        try:
            return list(value)
        except Exception:
            return None

    @staticmethod
    def _to_mapping_items(value):
        try:
            return list(value.items())
        except Exception:
            return None

    @staticmethod
    def _to_plain_data(value, _depth=0):
        if _depth > 12:
            return str(value)
        if value is None or isinstance(value, (bool, int, float, str)):
            return value

        items = DefineBonePropertyNode._to_mapping_items(value)
        if items is not None:
            out = {}
            for key, item_value in items:
                out[str(key)] = DefineBonePropertyNode._to_plain_data(item_value, _depth + 1)
            return out

        seq = DefineBonePropertyNode._to_sequence(value)
        if seq is not None:
            return [DefineBonePropertyNode._to_plain_data(v, _depth + 1) for v in seq]

        return str(value)

    @staticmethod
    def _json_text(value, fallback=""):
        try:
            return json.dumps(DefineBonePropertyNode._to_plain_data(value), ensure_ascii=True)
        except Exception:
            try:
                return str(value)
            except Exception:
                return str(fallback)

    @staticmethod
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

    @staticmethod
    def _clone_value(value):
        if isinstance(value, list):
            return [DefineBonePropertyNode._clone_value(v) for v in value]
        if isinstance(value, tuple):
            return tuple(DefineBonePropertyNode._clone_value(v) for v in value)
        if isinstance(value, dict):
            return {k: DefineBonePropertyNode._clone_value(v) for k, v in value.items()}
        return value

    @staticmethod
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

    @staticmethod
    def _coerce_int(value, fallback=0):
        try:
            return int(value)
        except Exception:
            try:
                return int(float(value))
            except Exception:
                return int(fallback)

    @staticmethod
    def _coerce_float(value, fallback=0.0):
        try:
            return float(value)
        except Exception:
            return float(fallback)

    @staticmethod
    def _coerce_string(value, fallback=""):
        if value is None:
            return str(fallback)
        try:
            return str(value)
        except Exception:
            return str(fallback)

    @staticmethod
    def _matrix_identity_flat():
        return [
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        ]

    @staticmethod
    def _matrix4_from_flat(values):
        flat = list(values) if values is not None else DefineBonePropertyNode._matrix_identity_flat()
        if len(flat) != 16:
            flat = DefineBonePropertyNode._matrix_identity_flat()
        return (
            (float(flat[0]), float(flat[1]), float(flat[2]), float(flat[3])),
            (float(flat[4]), float(flat[5]), float(flat[6]), float(flat[7])),
            (float(flat[8]), float(flat[9]), float(flat[10]), float(flat[11])),
            (float(flat[12]), float(flat[13]), float(flat[14]), float(flat[15])),
        )

    @staticmethod
    def _coerce_vector3(value, fallback=(0.0, 0.0, 0.0)):
        candidate = DefineBonePropertyNode._parse_json_text(value, fallback=value)

        if hasattr(candidate, "x") and hasattr(candidate, "y") and hasattr(candidate, "z"):
            try:
                return [float(candidate.x), float(candidate.y), float(candidate.z)]
            except Exception:
                pass

        seq = DefineBonePropertyNode._to_sequence(candidate)
        if seq is not None and len(seq) >= 3:
            try:
                return [float(seq[0]), float(seq[1]), float(seq[2])]
            except Exception:
                pass

        fb = DefineBonePropertyNode._to_sequence(fallback)
        if fb is not None and len(fb) >= 3:
            try:
                return [float(fb[0]), float(fb[1]), float(fb[2])]
            except Exception:
                pass

        return [0.0, 0.0, 0.0]

    @staticmethod
    def _coerce_matrix16(value, fallback=None):
        candidate = DefineBonePropertyNode._parse_json_text(value, fallback=value)

        seq = DefineBonePropertyNode._to_sequence(candidate)
        if seq is not None:
            if len(seq) == 16 and all(DefineBonePropertyNode._is_number(v) for v in seq):
                return [float(v) for v in seq]
            if len(seq) == 4:
                rows = []
                ok = True
                for row in seq:
                    rseq = DefineBonePropertyNode._to_sequence(row)
                    if rseq is None or len(rseq) < 4:
                        ok = False
                        break
                    try:
                        rows.extend([float(rseq[0]), float(rseq[1]), float(rseq[2]), float(rseq[3])])
                    except Exception:
                        ok = False
                        break
                if ok and len(rows) == 16:
                    return rows

        fb = DefineBonePropertyNode._to_sequence(fallback)
        if fb is not None:
            if len(fb) == 16 and all(DefineBonePropertyNode._is_number(v) for v in fb):
                return [float(v) for v in fb]
            if len(fb) == 4:
                rows = []
                ok = True
                for row in fb:
                    rseq = DefineBonePropertyNode._to_sequence(row)
                    if rseq is None or len(rseq) < 4:
                        ok = False
                        break
                    try:
                        rows.extend([float(rseq[0]), float(rseq[1]), float(rseq[2]), float(rseq[3])])
                    except Exception:
                        ok = False
                        break
                if ok and len(rows) == 16:
                    return rows

        return DefineBonePropertyNode._matrix_identity_flat()

    @staticmethod
    def _coerce_numeric_array(value, fallback):
        fb_seq = DefineBonePropertyNode._to_sequence(fallback) or []

        candidate = DefineBonePropertyNode._parse_json_text(value, fallback=value)
        seq = DefineBonePropertyNode._to_sequence(candidate)
        if seq is None:
            seq = list(fb_seq)

        if not all(DefineBonePropertyNode._is_number(v) for v in seq):
            seq = list(fb_seq)

        if fb_seq and len(seq) != len(fb_seq):
            seq = list(fb_seq)

        all_int = (
            bool(fb_seq)
            and all(isinstance(v, int) and not isinstance(v, bool) for v in fb_seq)
        )

        out = []
        for v in seq:
            if all_int:
                out.append(DefineBonePropertyNode._coerce_int(v, 0))
            else:
                out.append(DefineBonePropertyNode._coerce_float(v, 0.0))
        return out

    @staticmethod
    def _coerce_json(value, fallback):
        parsed = DefineBonePropertyNode._parse_json_text(value, fallback=fallback)
        plain = DefineBonePropertyNode._to_plain_data(parsed)
        if plain is None:
            return DefineBonePropertyNode._to_plain_data(fallback)
        return plain

    @staticmethod
    def _lerp_numeric_sequence(start_value, target_value, t):
        sseq = DefineBonePropertyNode._to_sequence(start_value)
        tseq = DefineBonePropertyNode._to_sequence(target_value)
        if sseq is None or tseq is None or len(sseq) != len(tseq):
            return DefineBonePropertyNode._clone_value(target_value if t >= 1.0 else start_value)

        all_int = (
            all(isinstance(v, int) and not isinstance(v, bool) for v in sseq)
            and all(isinstance(v, int) and not isinstance(v, bool) for v in tseq)
        )

        out = []
        for a, b in zip(sseq, tseq):
            af = DefineBonePropertyNode._coerce_float(a, 0.0)
            bf = DefineBonePropertyNode._coerce_float(b, 0.0)
            v = (1.0 - t) * af + t * bf
            out.append(int(round(v)) if all_int else float(v))
        return out

    def _property_items(self):
        pbone, _ = self._pose_bone_ref()
        if pbone is None:
            return [("", "(select bone first)", "Pick a linked/selected bone first.")]

        specs = self._property_specs()
        if not specs:
            return [("", "(no custom properties)", "No custom properties found on this bone.")]
        return [(spec["id"], spec["label"], spec["description"]) for spec in specs]

    def _enum_bone_properties(self, context):
        return self._property_items()

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

            kind = self._property_kind_from_value(value)

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

                kind = self._property_kind_from_value(value)

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
            return self._coerce_bool(value, fallback)
        if kind == "INT":
            return self._coerce_int(value, fallback)
        if kind == "FLOAT":
            return self._coerce_float(value, fallback)
        if kind == "STRING":
            return self._coerce_string(value, fallback)
        if kind == "VECTOR3":
            return self._coerce_vector3(value, fallback)
        if kind == "MATRIX16":
            return self._coerce_matrix16(value, fallback)
        if kind == "ARRAY_NUMERIC":
            return self._coerce_numeric_array(value, fallback)
        if kind == "JSON":
            return self._coerce_json(value, fallback)
        return fallback

    def _ensure_property_selection(self):
        valid = [spec["id"] for spec in self._property_specs() if spec.get("id")]
        current = str(getattr(self, "property_name", "") or "")

        if current in valid:
            return

        new_value = valid[0] if valid else ""
        if current == new_value:
            return

        try:
            self.property_name = new_value
        except Exception:
            pass

    def _ensure_value_socket(self):
        kind = self._current_property_kind()
        wanted_type = self._socket_type_for_kind(kind)
        current_socket = self.inputs.get("Value")

        if wanted_type is None:
            if current_socket is not None:
                try:
                    self.inputs.remove(current_socket)
                except Exception:
                    pass
            return

        if current_socket is not None and getattr(current_socket, "bl_idname", "") != wanted_type:
            try:
                self.inputs.remove(current_socket)
            except Exception:
                pass
            current_socket = None

        if current_socket is None:
            current_socket = self.inputs.new(wanted_type, "Value")
            prop_value = self._current_property_value()
            self._set_socket_default_for_kind(current_socket, kind, prop_value)

    def _value_as_socket_payload(self, kind, value):
        if kind == "BOOL":
            return bool(self._coerce_bool(value, False))
        if kind == "INT":
            return int(self._coerce_int(value, 0))
        if kind == "FLOAT":
            return float(self._coerce_float(value, 0.0))
        if kind == "STRING":
            return self._coerce_string(value, "")
        if kind == "VECTOR3":
            vec = self._coerce_vector3(value, (0.0, 0.0, 0.0))
            return (float(vec[0]), float(vec[1]), float(vec[2]))
        if kind == "MATRIX16":
            mat_flat = self._coerce_matrix16(value, self._matrix_identity_flat())
            return self._matrix4_from_flat(mat_flat)
        if kind in {"ARRAY_NUMERIC", "JSON"}:
            return self._json_text(value, "[]")
        return value

    def _set_socket_default_for_kind(self, sock, kind, value):
        if sock is None or not hasattr(sock, "default_value"):
            return
        try:
            sock.default_value = self._value_as_socket_payload(kind, value)
        except Exception:
            pass

    def init(self, context):
        self.inputs.new("NodeSocketBone", "Bone")

        s = self.inputs.new("NodeSocketInt", "Start")
        d = self.inputs.new("NodeSocketInt", "Duration")
        try:
            s.default_value = 0
            d.default_value = 10
        except Exception:
            pass

        self.outputs.new("NodeSocketInt", "End")
        self.update()

    def update(self):
        if getattr(self, "_syncing", False):
            return

        self._syncing = True
        try:
            self._ensure_property_selection()
            self._ensure_value_socket()
        finally:
            self._syncing = False

    def draw_buttons(self, context, layout):
        layout.prop(self, "property_name", text="")

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
        value_socket = self.inputs.get("Value")
        raw_target = self.eval_socket(tree, value_socket, scene, ctx) if value_socket else current_value
        target = self._coerce_for_kind(raw_target, kind, current_value)

        state = ctx.pose_cache.get(cache_key)
        if state is None:
            state = {
                "start_value": self._clone_value(current_value),
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
        elif kind in {"VECTOR3", "MATRIX16", "ARRAY_NUMERIC"}:
            value_out = self._lerp_numeric_sequence(start_value, target, t)
            if kind == "VECTOR3":
                value_out = [float(v) for v in (value_out[:3] if len(value_out) >= 3 else [0.0, 0.0, 0.0])]
        elif kind in {"STRING", "JSON"}:
            value_out = self._clone_value(target if t >= 1.0 else start_value)
        else:
            value_out = self._clone_value(target if t >= 1.0 else start_value)

        try:
            if not self._write_property_value(pbone, spec, value_out): return
            ctx.touched_armatures.add(arm_ob)
        except Exception: pass

class ReadBonePropertyNode(DefineBonePropertyNode):
    bl_idname = "ReadBonePropertyNode"
    bl_label = "Read Bone Property"
    bl_icon = "BONE_DATA"

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
            v = _eval_idx(0, 1.0 if self._coerce_bool(fallback, False) else 0.0)
            return bool(float(v) >= 0.5)

        if kind == "INT":
            v = _eval_idx(0, self._coerce_int(fallback, 0))
            return self._coerce_int(v, fallback)

        if kind == "FLOAT":
            v = _eval_idx(0, self._coerce_float(fallback, 0.0))
            return self._coerce_float(v, fallback)

        if kind in {"VECTOR3", "MATRIX16", "ARRAY_NUMERIC"}:
            base = self._coerce_for_kind(fallback, kind, fallback)
            seq = self._to_sequence(base) or []

            if kind == "VECTOR3":
                wanted_len = 3
            elif kind == "MATRIX16":
                wanted_len = 16
            else:
                wanted_len = len(seq) if seq else (max(by_index.keys()) + 1 if by_index else 0)

            if wanted_len <= 0:
                return base

            if len(seq) < wanted_len:
                seq = list(seq) + [0.0] * (wanted_len - len(seq))
            else:
                seq = list(seq[:wanted_len])

            for idx in range(wanted_len):
                seq[idx] = _eval_idx(idx, seq[idx])

            if kind == "VECTOR3":
                return [self._coerce_float(v, 0.0) for v in seq[:3]]
            if kind == "MATRIX16":
                return [self._coerce_float(v, 0.0) for v in seq[:16]]

            all_int = all(isinstance(v, int) and not isinstance(v, bool) for v in (self._to_sequence(base) or []))
            if all_int:
                return [self._coerce_int(v, 0) for v in seq]
            return [self._coerce_float(v, 0.0) for v in seq]

        return fallback

    def _ensure_output_socket(self):
        kind = self._current_property_kind()
        wanted_type = self._socket_type_for_kind(kind)
        current_socket = self.outputs.get("Value")

        if wanted_type is None:
            if current_socket is not None:
                try:
                    self.outputs.remove(current_socket)
                except Exception:
                    pass
            return

        if current_socket is not None and getattr(current_socket, "bl_idname", "") != wanted_type:
            try:
                self.outputs.remove(current_socket)
            except Exception:
                pass
            current_socket = None

        if current_socket is None:
            current_socket = self.outputs.new(wanted_type, "Value")

        prop_value = self._current_property_value()
        self._set_socket_default_for_kind(current_socket, kind, prop_value)

    def init(self, context):
        self.inputs.new("NodeSocketBone", "Bone")
        frame = self.inputs.new("NodeSocketInt", "Frame")
        try:
            frame.default_value = 0
        except Exception:
            pass
        self.outputs.new("NodeSocketFloat", "Value")
        self.update()

    def update(self):
        if getattr(self, "_syncing", False):
            return

        self._syncing = True
        try:
            self._ensure_property_selection()
            self._ensure_output_socket()
        finally:
            self._syncing = False

    def draw_buttons(self, context, layout):
        layout.prop(self, "property_name", text="")

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

        payload = self._value_as_socket_payload(kind, value)

        out = self.outputs.get("Value")
        if out:
            self._set_socket_default_for_kind(out, kind, value)

        self.set_output_value(ctx, "Value", payload)


_CLASSES = [
    DefineBoneNode,
    DefineBonePropertyNode,
    ReadBonePropertyNode,
]
