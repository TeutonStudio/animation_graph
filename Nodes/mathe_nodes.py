# animation_graph/Nodes/mathe_nodes.py

import bpy
from bpy.types import Node
from bpy.props import EnumProperty
from mathutils import Vector, Matrix, Euler

from .Mixin import AnimGraphNodeMixin

class IntConst(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_IntConst"
    bl_label = "Constant (Int)"
    bl_icon = "NODE_SOCKET_INT"

    def init(self, context):
        i = self.outputs.new("NodeSocketInt", "Int")
    
    def evaluate(self, tree, scene, ctx): pass


class FloatConst(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_FloatConst"
    bl_label = "Constant (Float)"
    bl_icon = "NODE_SOCKET_FLOAT"

    def init(self, context):
        f = self.outputs.new("NodeSocketFloat", "Float")
    
    def evaluate(self, tree, scene, ctx): pass


class VectorConst(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_VectorConst"
    bl_label = "Constant (Vector)"
    bl_icon = "EMPTY_AXIS"

    def init(self, context):
        v = self.outputs.new("NodeSocketVectorXYZ", "Vector")
    
    def evaluate(self, tree, scene, ctx): pass


class MatrixConst(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_MatrixConst"
    bl_label = "Constant (Matrix)"
    bl_icon = "NODE_SOCKET_MATRIX"

    def init(self, context):
        m = self.outputs.new("NodeSocketMatrix", "Matrix")
    
    def evaluate(self, tree, scene, ctx): pass


class IntMath(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_IntMath"
    bl_label = "Math (Int)"
    bl_icon = "NODE_SOCKET_INT"

    operation: EnumProperty(
        name="Operation",
        items=number_operators,
        default="ADD",
    )

    def init(self, context):
        a = self.inputs.new("NodeSocketInt", "A")
        b = self.inputs.new("NodeSocketInt", "B")
        try:
            a.default_value = 0
            b.default_value = 0
        except Exception:
            pass
        self.outputs.new("NodeSocketInt", "Result")

    def draw_buttons(self, context, layout):
        layout.prop(self, "operation", text="")

    def evaluate(self, tree, scene, ctx):
        a = self.socket_int(tree, "A", scene, ctx, 0)
        b = self.socket_int(tree, "B", scene, ctx, 0)
        op = getattr(self, "operation", "ADD")

        try:
            if op == "ADD":
                r = a + b
            elif op == "SUBTRACT":
                r = a - b
            elif op == "MULTIPLY":
                r = a * b
            elif op == "DIVIDE":
                r = int(a / b) if b != 0 else 0
            elif op == "POWER":
                r = int(a ** b)
            elif op == "MINIMUM":
                r = min(a, b)
            elif op == "MAXIMUM":
                r = max(a, b)
            else:
                r = 0
        except Exception:
            r = 0

        out = self.outputs.get("Result")
        if out:
            try:
                out.default_value = int(r)
            except Exception:
                # Some socket implementations are picky
                out.default_value = int(0)


class FloatMath(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_FloatMath"
    bl_label = "Math (Float)"
    bl_icon = "NODE_SOCKET_FLOAT"

    operation: EnumProperty(
        name="Operation",
        items=number_operators,
        default="ADD",
    )

    def init(self, context):
        a = self.inputs.new("NodeSocketFloat", "A")
        b = self.inputs.new("NodeSocketFloat", "B")
        try:
            a.default_value = 0.0
            b.default_value = 0.0
        except Exception:
            pass
        self.outputs.new("NodeSocketFloat", "Result")

    def draw_buttons(self, context, layout):
        layout.prop(self, "operation", text="")

    def evaluate(self, tree, scene, ctx):
        a = self.socket_float(tree, "A", scene, ctx, 0.0)
        b = self.socket_float(tree, "B", scene, ctx, 0.0)
        op = getattr(self, "operation", "ADD")

        try:
            if op == "ADD":
                r = a + b
            elif op == "SUBTRACT":
                r = a - b
            elif op == "MULTIPLY":
                r = a * b
            elif op == "DIVIDE":
                r = a / b if b != 0.0 else 0.0
            elif op == "POWER":
                r = a ** b
            elif op == "MINIMUM":
                r = min(a, b)
            elif op == "MAXIMUM":
                r = max(a, b)
            else:
                r = 0.0
        except Exception:
            r = 0.0

        out = self.outputs.get("Result")
        if out:
            out.default_value = float(r)


class VectorMath(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_VectorMath"
    bl_label = "Vector Math"
    bl_icon = "NODE_SOCKET_VECTOR"

    operation: EnumProperty(
        name="Operation",
        items=vector_operators,
        default="ADD",
    )

    def init(self, context):
        self.inputs.new("NodeSocketVector", "A")
        self.inputs.new("NodeSocketVector", "B")
        self.inputs.new("NodeSocketFloat", "Scale")
        self.outputs.new("NodeSocketVector", "Vector")
        self.outputs.new("NodeSocketFloat", "Float")

    def draw_buttons(self, context, layout):
        layout.prop(self, "operation", text="")

    def evaluate(self, tree, scene, ctx):
        A = self.socket_vector(tree, "A", scene, ctx, (0.0, 0.0, 0.0))
        B = self.socket_vector(tree, "B", scene, ctx, (0.0, 0.0, 0.0))
        s = self.socket_float(tree, "Scale", scene, ctx, 1.0)
        op = getattr(self, "operation", "ADD")

        out_v = self.outputs.get("Vector")
        out_f = self.outputs.get("Float")

        try:
            if op == "ADD":
                if out_v: out_v.default_value = (A + B)
            elif op == "SUBTRACT":
                if out_v: out_v.default_value = (A - B)
            elif op == "MULTIPLY":
                if out_v: out_v.default_value = Vector((A.x * B.x, A.y * B.y, A.z * B.z))
            elif op == "DOT":
                if out_f: out_f.default_value = float(A.dot(B))
            elif op == "CROSS":
                if out_v: out_v.default_value = A.cross(B)
            elif op == "SCALE":
                if out_v: out_v.default_value = (A * float(s))
            elif op == "LENGTH":
                if out_f: out_f.default_value = float(A.length)
            elif op == "NORMALIZE":
                if out_v:
                    out_v.default_value = (A.normalized() if A.length > 0.0 else Vector((0.0, 0.0, 0.0)))
        except Exception:
            pass


class CombineXYZ(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_CombineXYZ"
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
    bl_idname = "ANIMGRAPH_SeparateXYZ"
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


# TODO redefine to MatrixMath
class MatrixMultiply(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_MatrixMultiply"
    bl_label = "Matrix Multiply"
    bl_icon = "NODE_SOCKET_MATRIX"

    def init(self, context):
        self.inputs.new("NodeSocketMatrix", "A")
        self.inputs.new("NodeSocketMatrix", "B")
        self.outputs.new("NodeSocketMatrix", "Result")

    def evaluate(self, tree, scene, ctx):
        A = self.socket_matrix(tree, "A", scene, ctx, None)
        B = self.socket_matrix(tree, "B", scene, ctx, None)
        out = self.outputs.get("Result")
        if out and A is not None and B is not None:
            out.default_value = (A @ B)


class ComposeMatrix(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_ComposeMatrix"
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
    bl_idname = "ANIMGRAPH_DecomposeMatrix"
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


number_operators = [
    ("ADD", "Add", ""),
    ("SUBTRACT", "Subtract", ""),
    ("MULTIPLY", "Multiply", ""),
    ("DIVIDE", "Divide", ""),
    ("POWER", "Power", ""),
    ("MINIMUM", "Minimum", ""),
    ("MAXIMUM", "Maximum", ""),
]

vector_operators = [
    ("ADD", "Add", ""),
    ("SUBTRACT", "Subtract", ""),
    ("MULTIPLY", "Multiply", "Component-wise multiply"),
    ("DOT", "Scalar product", ""),
    ("CROSS", "Vector product", ""),
    ("SCALE", "Scale", "Scale product"),
    ("LENGTH", "Length", "Returns float length"),
    ("NORMALIZE", "Normalize", ""),
]

