# animation_graph/Nodes/mathematik/adapters.py

import bpy
from bpy.types import Node
from mathutils import Vector, Matrix, Euler

from ..Mixin import AnimGraphNodeMixin

def register():
    for c in _ADAPTERS: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_ADAPTERS): bpy.utils.unregister_class(c)

class CombineXYZ(Node, AnimGraphNodeMixin):
    bl_idname = "CombineXYZ"
    bl_label = "Combine XYZ"
    bl_icon = "EMPTY_AXIS"

    def init(self, context):
        self.inputs.new("NodeSocketFloat", "X")
        self.inputs.new("NodeSocketFloat", "Y")
        self.inputs.new("NodeSocketFloat", "Z")
        self.outputs.new("NodeSocketVectorXYZ", "Vector")

    def evaluate(self, tree, scene, ctx):
        x = self.socket_float(tree, "X", scene, ctx, 0.0)
        y = self.socket_float(tree, "Y", scene, ctx, 0.0)
        z = self.socket_float(tree, "Z", scene, ctx, 0.0)
        out = self.outputs.get("Vector")
        if out: out.default_value = (float(x), float(y), float(z))

class SeparateXYZ(Node, AnimGraphNodeMixin):
    bl_idname = "SeparateXYZ"
    bl_label = "Separate XYZ"
    bl_icon = "EMPTY_AXIS"

    def init(self, context):
        self.inputs.new("NodeSocketVectorXYZ", "Vector")
        self.outputs.new("NodeSocketFloat", "X")
        self.outputs.new("NodeSocketFloat", "Y")
        self.outputs.new("NodeSocketFloat", "Z")

    def evaluate(self, tree, scene, ctx):
        v = self.socket_vector(tree, "Vector", scene, ctx, (0.0, 0.0, 0.0))
        ox = self.outputs.get("X")
        oy = self.outputs.get("Y")
        oz = self.outputs.get("Z")
        if ox: ox.default_value = float(v.x)
        if oy: oy.default_value = float(v.y)
        if oz: oz.default_value = float(v.z)

class ComposeMatrix(Node, AnimGraphNodeMixin):
    bl_idname = "ComposeMatrix"
    bl_label = "Compose Matrix"
    bl_icon = "NODE_SOCKET_MATRIX"

    def init(self, context):
        self.inputs.new("NodeSocketVectorTranslation", "Translation")
        self.inputs.new("NodeSocketRotation", "Rotation")
        self.inputs.new("NodeSocketVectorXYZ", "Scale")
        self.outputs.new("NodeSocketMatrix", "Matrix")

    def evaluate(self, tree, scene, ctx):
        t = self.socket_vector(tree, "Translation", scene, ctx, (0.0, 0.0, 0.0))
        r = self.socket_vector(tree, "Rotation", scene, ctx, (0.0, 0.0, 0.0))
        s = self.socket_vector(tree, "Scale", scene, ctx, (1.0, 1.0, 1.0))

        try:
            e = Euler((r.x, r.y, r.z), "XYZ")
            m = Matrix.LocRotScale(t, e.to_quaternion(), s)
        except Exception:
            m = Matrix.Identity(4)

        out = self.outputs.get("Matrix")
        if out:
            out.default_value = m

class DecomposeMatrix(Node, AnimGraphNodeMixin):
    bl_idname = "DecomposeMatrix"
    bl_label = "Decompose Matrix"
    bl_icon = "NODE_SOCKET_MATRIX"

    def init(self, context):
        self.inputs.new("NodeSocketMatrix", "Matrix")
        self.outputs.new("NodeSocketVectorTranslation", "Translation")
        self.outputs.new("NodeSocketRotation", "Rotation")
        self.outputs.new("NodeSocketVectorXYZ", "Scale")

    def evaluate(self, tree, scene, ctx):
        m = self.socket_matrix(tree, "Matrix", scene, ctx, None)
        if m is None:
            return

        try:
            loc, rot_q, scale = m.decompose()
            rot_e = rot_q.to_euler("XYZ")
        except Exception:
            loc = Vector((0.0, 0.0, 0.0))
            rot_e = Euler((0.0, 0.0, 0.0), "XYZ")
            scale = Vector((1.0, 1.0, 1.0))

        ot = self.outputs.get("Translation")
        orot = self.outputs.get("Rotation")
        os = self.outputs.get("Scale")

        if ot: ot.default_value = (loc.x, loc.y, loc.z)
        if orot: orot.default_value = (rot_e.x, rot_e.y, rot_e.z)
        if os: os.default_value = (scale.x, scale.y, scale.z)

_ADAPTERS = [
    CombineXYZ,
    SeparateXYZ,
    ComposeMatrix,
    DecomposeMatrix,
]
