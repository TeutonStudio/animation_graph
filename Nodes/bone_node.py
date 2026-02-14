# animation_graph/Nodes/bone_node.py

import bpy
from bpy.props import EnumProperty
from .Mixin import AnimGraphNodeMixin


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

class DefineBonePropertieNode(bpy.types.Node, AnimGraphNodeMixin):
    bl_idname = "DefineBonePropertieNode"
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
        return None

    @staticmethod
    def _socket_type_for_kind(kind):
        if kind == "BOOL":
            return "NodeSocketBool"
        if kind == "INT":
            return "NodeSocketInt"
        if kind == "FLOAT":
            return "NodeSocketFloat"
        return None

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

    def _property_items(self):
        pbone, _ = self._pose_bone_ref()
        if pbone is None:
            return [("", "(select bone first)", "Pick a linked/selected bone first.")]

        specs = self._property_specs()
        if not specs:
            return [("", "(no bool/int/float properties)", "No compatible bone properties found on this bone.")]
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
            if kind is None:
                continue

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
                if kind is None:
                    continue

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
            try:
                if kind == "BOOL":
                    current_socket.default_value = bool(self._coerce_bool(prop_value, False))
                elif kind == "INT":
                    current_socket.default_value = int(self._coerce_int(prop_value, 0))
                elif kind == "FLOAT":
                    current_socket.default_value = float(self._coerce_float(prop_value, 0.0))
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
        if kind not in {"BOOL", "INT", "FLOAT"}: return

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

        value_socket = self.inputs.get("Value")
        raw_target = self.eval_socket(tree, value_socket, scene, ctx) if value_socket else prop_current
        target = self._coerce_for_kind(raw_target, kind, prop_current)

        state = ctx.pose_cache.get(cache_key)
        if state is None:
            state = {
                "start_value": self._coerce_for_kind(prop_current, kind, prop_current),
            }
            ctx.pose_cache[cache_key] = state
        start_value = state.get("start_value", prop_current)

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
        else:
            value_out = float((1.0 - t) * float(start_value) + t * float(target))

        try:
            if not self._write_property_value(pbone, spec, value_out): return
            ctx.touched_armatures.add(arm_ob)
        except Exception: pass
