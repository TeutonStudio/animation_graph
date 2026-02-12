# animation_graph/Core/node_tree.py

import bpy
from bpy.types import NodeGroupInput, NodeGroupOutput

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

    if not tree:
        try:
            self.animgraph_input_values.clear()
        except Exception:
            pass
        return

    sync_action_inputs(self, tree)

    try:
        tree.dirty = True
    except Exception:
        pass


def _poll_armature_obj(self, obj):
    return obj is not None and obj.type == "ARMATURE"


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


def sync_actions_for_tree(tree):
    if tree is None:
        return

    for action in bpy.data.actions:
        if getattr(action, "animgraph_tree", None) != tree:
            continue
        sync_action_inputs(action, tree)


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
