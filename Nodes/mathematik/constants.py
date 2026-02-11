# animation_graph/Nodes/mathematik/constants.py

import bpy
from bpy.types import Node

from ..Mixin import AnimGraphNodeMixin

def register():
    for c in _CONSTANTS: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_CONSTANTS): bpy.utils.unregister_class(c)


class IntConst(Node, AnimGraphNodeMixin):
    bl_idname = "IntConst"
    bl_label = "Constant (Int)"
    bl_icon = "NODE_SOCKET_INT"

    def init(self, context):
        i = self.outputs.new("NodeSocketInt", "Int")
    
    def evaluate(self, tree, scene, ctx): pass

class FloatConst(Node, AnimGraphNodeMixin):
    bl_idname = "FloatConst"
    bl_label = "Constant (Float)"
    bl_icon = "NODE_SOCKET_FLOAT"

    def init(self, context):
        f = self.outputs.new("NodeSocketFloat", "Float")
    
    def evaluate(self, tree, scene, ctx): pass

class VectorConst(Node, AnimGraphNodeMixin):
    bl_idname = "VectorConst"
    bl_label = "Constant (Vector)"
    bl_icon = "EMPTY_AXIS"

    def init(self, context):
        v = self.outputs.new("NodeSocketVectorXYZ", "Vector")
    
    def evaluate(self, tree, scene, ctx): pass

class RotationConst(Node, AnimGraphNodeMixin):
    bl_idname = "RotationConst"
    bl_label = "Constant (Rotation)"
    bl_icon = "EMPTY_AXIS"

    def init(self, context):
        v = self.outputs.new("NodeSocketRotation", "Rotation")
    
    def evaluate(self, tree, scene, ctx): pass

class TranslationConst(Node, AnimGraphNodeMixin):
    bl_idname = "TranslationConst"
    bl_label = "Constant (Rotation)"
    bl_icon = "EMPTY_AXIS"

    def init(self, context):
        v = self.outputs.new("NodeSocketVectorTranslation", "Translation")
    
    def evaluate(self, tree, scene, ctx): pass

class MatrixConst(Node, AnimGraphNodeMixin):
    bl_idname = "MatrixConst"
    bl_label = "Constant (Matrix)"
    bl_icon = "NODE_SOCKET_MATRIX"

    def init(self, context):
        m = self.outputs.new("NodeSocketMatrix", "Matrix")
    
    def evaluate(self, tree, scene, ctx): pass

_CONSTANTS = [
    IntConst,
    FloatConst,
    VectorConst,
    RotationConst,
    TranslationConst,
    MatrixConst,
]