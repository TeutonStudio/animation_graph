# animation_graph/UI/action_panel.py

import bpy
from ..Core import node_tree

def register():
    for c in _CLASSES: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_CLASSES): bpy.utils.unregister_class(c)

class ANIMGRAPH_PT_action_binding(bpy.types.Panel):
    bl_label = "AnimationNodes"
    bl_space_type = "DOPESHEET_EDITOR"
    bl_region_type = "UI"
    bl_category = "Action"

    @classmethod
    def poll(cls, context):
        obj = getattr(context, "object", None)
        ad = getattr(obj, "animation_data", None) if obj else None
        return bool(getattr(ad, "action", None))

    def draw(self, context):
        layout = self.layout
        obj = context.object
        action = obj.animation_data.action

        layout.label(text=f"Action: {action.name}")
        layout.template_ID(action, "animgraph_tree", new="node.new_node_tree")

        tree = getattr(action, "animgraph_tree", None)
        if not tree:
            return

        iface_inputs = node_tree.iter_interface_sockets(tree, in_out="INPUT")
        if not iface_inputs:
            return

        layout.separator()
        layout.label(text="Inputs")

        for iface_socket in iface_inputs:
            ident = node_tree.interface_socket_identifier(iface_socket)
            if not ident:
                continue

            slot = node_tree.find_action_input_slot(action, ident)
            if slot is None:
                row = layout.row()
                row.enabled = False
                row.label(text=f"{getattr(iface_socket, 'name', ident)} (noch nicht synchronisiert)")
                continue

            label = getattr(iface_socket, "name", ident)
            kind = node_tree.socket_kind(node_tree.interface_socket_type(iface_socket))

            if kind == "INT":
                layout.prop(slot, "int_value", text=label)
                continue

            if kind == "FLOAT":
                layout.prop(slot, "float_value", text=label)
                continue

            if kind == "VECTOR":
                layout.prop(slot, "vector_value", text=label)
                continue

            if kind == "BONE":
                box = layout.box()
                box.label(text=label)
                col = box.column(align=True)
                col.prop(slot, "bone_armature_obj", text="Armature")
                row = col.row(align=True)
                arm_obj = slot.bone_armature_obj
                row.enabled = bool(arm_obj and arm_obj.type == "ARMATURE" and arm_obj.data)
                row.prop(slot, "bone_name", text="Bone")
                continue

            if kind == "MATRIX":
                box = layout.box()
                box.label(text=label)
                for row_idx in range(4):
                    row = box.row(align=True)
                    base = row_idx * 4
                    row.prop(slot, "matrix_value", index=base + 0, text="")
                    row.prop(slot, "matrix_value", index=base + 1, text="")
                    row.prop(slot, "matrix_value", index=base + 2, text="")
                    row.prop(slot, "matrix_value", index=base + 3, text="")
                continue

            row = layout.row()
            row.enabled = False
            row.label(text=f"{label} ({slot.socket_type} nicht unterstuetzt)")

_CLASSES = [
    ANIMGRAPH_PT_action_binding,
]
