# animation_graph/Nodes/bone_node.py

import bpy
from .Mixin import AnimGraphNodeMixin
from ..Core.sockets import NodeSocketBone

# ---- helpers für die Enums ----

# def _enum_bones_from_selected_armature(self, context):
#     """
#     Baut die Bone-Liste dynamisch basierend auf self.armature_obj.
#     Muss eine Liste von (identifier, name, description) liefern.
#     """
#     arm_obj = getattr(self, "armature_obj", None)

#     if not arm_obj or arm_obj.type != "ARMATURE" or not arm_obj.data:
#         return [("", "(erst Armature wählen)", "Bitte zuerst eine Armature auswählen.")]

#     items = []
#     # arm_obj.data ist bpy.types.Armature, .bones sind Edit/Rest-Bones (nicht PoseBones)
#     for b in arm_obj.data.bones:
#         items.append((b.name, b.name, ""))

#     if not items:
#         return [("", "(keine Bones vorhanden)", "Die gewählte Armature hat keine Bones.")]
#     return items


# def _on_armature_changed(self, context):
#     """
#     Wenn Armature wechselt: Bone-Auswahl zurücksetzen, falls nicht mehr gültig.
#     """
#     arm_obj = getattr(self, "armature_obj", None)
#     current = getattr(self, "bone_name", "")

#     if not arm_obj or arm_obj.type != "ARMATURE" or not arm_obj.data:
#         self.bone_name = ""
#         return

#     if current and current not in arm_obj.data.bones:
#         self.bone_name = ""


# ---- Node ----

class DefineBoneNode(bpy.types.Node, AnimGraphNodeMixin):
    bl_idname = "BoneName"
    bl_label = "Bone"
    bl_icon = "BONE_DATA"

    def init(self, context):
        # Output ist dein Bone-Socket
        self.outputs.new(NodeSocketBone.bl_idname,NodeSocketBone.label)

    def draw_buttons(self, context, layout):
        pass


# ---- Socket ----

# class NodeSocketBone(bpy.types.NodeSocket):
#     bl_idname = "NodeSocketBone"
#     bl_label = "Bone"

#     armature_obj: bpy.props.PointerProperty(
#         name="Armature",
#         description="Armature-Objekt aus der aktuellen Datei",
#         type=bpy.types.Object,
#         poll=lambda self, obj: obj is not None and obj.type == "ARMATURE",
#         update=_on_armature_changed,
#     )

#     bone_name: bpy.props.EnumProperty(
#         name="Bone",
#         description="Bone to use",
#         items=_enum_bones_from_selected_armature,
#     )

#     def draw(self, context, layout, node, text):
#         # Socket-Label links im UI
#         if text:
#             layout.label(text=text)

#         # Wenn verbunden: nur anzeigen, nicht editierbar (dein bisheriges Verhalten)
#         if self.is_linked and self.links and (not self.is_output):
#             from_sock = self.links[0].from_socket
#             linked_arm = getattr(from_sock, "armature_obj", None)
#             linked_bone = getattr(from_sock, "bone_name", "") or "(kein Bone)"
#             linked_arm_name = linked_arm.name if linked_arm else "(keine Armature)"

#             col = layout.column(align=True)
#             col.enabled = False
#             col.label(text=linked_arm_name)
#             col.label(text=linked_bone)
#             return

#         # Unlinked (oder Output) -> editierbar:
#         col = layout.column(align=True)

#         # 1) Armature wählen
#         col.prop(self, "armature_obj", text="")

#         # 2) Bone wählen (nur wenn Armature gültig)
#         arm_obj = self.armature_obj
#         row = col.row(align=True)
#         row.enabled = bool(arm_obj and arm_obj.type == "ARMATURE" and arm_obj.data)
#         row.prop(self, "bone_name", text="")

#     def draw_color(self, context, node):
#         return (0.8, 0.7, 0.2, 1.0)
