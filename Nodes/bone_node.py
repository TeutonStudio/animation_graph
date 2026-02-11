# animation_graph/Nodes/bone_node.py

import bpy
from .Mixin import AnimGraphNodeMixin

class DefineBoneNode(bpy.types.Node, AnimGraphNodeMixin):
    bl_idname = "BoneName"
    bl_label = "Bone"
    bl_icon = "BONE_DATA"

    def init(self, context):
        # Output ist dein Bone-Socket
        self.outputs.new("NodeSocketBone","Bone")

    def draw_buttons(self, context, layout):
        pass
