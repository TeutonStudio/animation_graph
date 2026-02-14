# animation_graph/Nodes/mathematik/calculators.py

import bpy
import math
from bpy.types import Node
from mathutils import Vector, Matrix, Euler
from bpy.props import EnumProperty

from ..Mixin import AnimGraphNodeMixin

def register():
    for c in _CALCULATORS: bpy.utils.register_class(c)

def unregister():
    for c in reversed(_CALCULATORS): bpy.utils.unregister_class(c)

basic_operators = {
    ("ADD", "Add", ""),
    ("SUBTRACT", "Subtract", ""),
    ("MULTIPLY", "Multiply", ""),
    ("POWER", "Power", ""),
}

int_operators = basic_operators | {
    ("MODULOS", "Modulos", "Returns integer quotient and remainder"),
    ("MINIMUM", "Minimum", ""),
    ("MAXIMUM", "Maximum", ""),
}

float_operators = basic_operators | {
    ("DIVIDE", "Divide", ""),
    ("MINIMUM", "Minimum", ""),
    ("MAXIMUM", "Maximum", ""),
    ("FLOOR", "Floor", "Biggest integer value <= A"),
    ("CEIL", "Ceil", "Smallest integer value >= A"),
}

vector_operators = basic_operators | {
    ("DOT", "Scalar product", ""),
    ("CROSS", "Vector product", ""),
    ("SCALE", "Scale", "Scale product"),
    ("LENGTH", "Length", "Returns float length"),
    ("NORMALIZE", "Normalize", ""),
    ("DISTANCE", "Distance", "Returns float distance between A and B"),
}

matrix_operators = basic_operators | {
    ("SCALE", "Scale", "Scale product"),
}


class IntMath(Node, AnimGraphNodeMixin):
    bl_idname = "IntMath"
    bl_label = "Math (Int)"
    bl_icon = "NODE_SOCKET_INT"

    operation: EnumProperty(
        name="Operation",
        items=int_operators,
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
        self.outputs.new("NodeSocketInt", "Remainder")

    def draw_buttons(self, context, layout):
        layout.prop(self, "operation", text="")

    def evaluate(self, tree, scene, ctx):
        a = self.socket_int(tree, "A", scene, ctx, 0)
        b = self.socket_int(tree, "B", scene, ctx, 0)
        op = getattr(self, "operation", "ADD")

        try:
            rem = 0
            if op == "ADD":
                r = a + b
            elif op == "SUBTRACT":
                r = a - b
            elif op == "MULTIPLY":
                r = a * b
            elif op in {"MODULOS", "DIVIDE"}:
                if b != 0:
                    r, rem = divmod(a, b)
                else:
                    r, rem = 0, 0
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
            rem = 0

        out_div = self.outputs.get("Result")
        if out_div:
            try: out_div.default_value = int(r)
            except Exception: out_div.default_value = int(0)

        out_rem = self.outputs.get("Remainder")
        if out_rem:
            try: out_rem.default_value = int(rem)
            except Exception: out_rem.default_value = int(0)

class FloatMath(Node, AnimGraphNodeMixin):
    bl_idname = "FloatMath"
    bl_label = "Math (Float)"
    bl_icon = "NODE_SOCKET_FLOAT"

    operation: EnumProperty(
        name="Operation",
        items=float_operators,
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
            elif op == "FLOOR":
                r = math.floor(a)
            elif op == "CEIL":
                r = math.ceil(a)
            elif op == "MINIMUM":
                r = min(a, b)
            elif op == "MAXIMUM":
                r = max(a, b)
            else:
                r = 0.0
        except Exception:
            r = 0.0

        out = self.outputs.get("Result")
        if out: out.default_value = float(r)

class VectorMath(Node, AnimGraphNodeMixin):
    bl_idname = "VectorMath"
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
                if out_v: out_v.default_value = (A.normalized() if A.length > 0.0 else Vector((0.0, 0.0, 0.0)))
            elif op == "DISTANCE":
                if out_f: out_f.default_value = float((A - B).length)
        except Exception: pass

class MatrixMath(Node, AnimGraphNodeMixin):
    bl_idname = "MatrixMath"
    bl_label = "Matrix Math"
    bl_icon = "NODE_SOCKET_MATRIX"

    operation: EnumProperty(
        name="Operation",
        items=matrix_operators,
        default="MULTIPLY",
    )

    def init(self, context):
        a = self.inputs.new("NodeSocketMatrix", "A")
        b = self.inputs.new("NodeSocketMatrix", "B")
        s = self.inputs.new("NodeSocketFloat", "Scale")
        e = self.inputs.new("NodeSocketInt", "Exponent")

        try:
            a.default_value = Matrix.Identity(4)
            b.default_value = Matrix.Identity(4)
            s.default_value = 1.0
            e.default_value = 1
        except Exception:
            pass

        self.outputs.new("NodeSocketMatrix", "Result")

    def draw_buttons(self, context, layout):
        layout.prop(self, "operation", text="")

    def evaluate(self, tree, scene, ctx):
        # Fallbacks: Identity für Matrizen, 1.0 fürs Skalieren
        A = self.socket_matrix(tree, "A", scene, ctx, Matrix.Identity(4))
        B = self.socket_matrix(tree, "B", scene, ctx, Matrix.Identity(4))
        s = self.socket_float(tree, "Scale", scene, ctx, 1.0)
        exp = self.socket_int(tree, "Exponent", scene, ctx, 1)
        op = getattr(self, "operation", "MULTIPLY")

        out = self.outputs.get("Result")
        if not out:
            return

        try:
            if op == "ADD":
                r = A + B
            elif op == "SUBTRACT":
                r = A - B
            elif op == "MULTIPLY":
                # Matrix-Multiplikation (wie dein altes A @ B, nur robust eingebettet)
                r = A @ B
            elif op == "POWER":
                if exp == 0:
                    r = Matrix.Identity(4)
                elif exp > 0:
                    r = Matrix.Identity(4)
                    for _ in range(int(exp)):
                        r = r @ A
                else:
                    r = Matrix.Identity(4)
                    inv = A.inverted()
                    for _ in range(abs(int(exp))):
                        r = r @ inv
            elif op == "SCALE":
                # Skaliert alle Komponenten der Matrix
                r = A * float(s)
            else:
                r = Matrix.Identity(4)

            out.default_value = r
        except Exception:
            # Wenn Blender/Inputs mal wieder “kreativ” sind
            try: out.default_value = Matrix.Identity(4)
            except Exception: pass


_CALCULATORS = [
    IntMath,
    FloatMath,
    VectorMath,
    MatrixMath,
]
