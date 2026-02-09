# animation_graph/Nodes/mathe_nodes.py

import bpy
from bpy.types import Node
from bpy.props import EnumProperty
from ..helpers import AnimGraphNodeMixin

class IntMath(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_IntMath"
    bl_label = "Math (Int)"
    bl_icon = "NODE_SOCKET_INT"

    operation: EnumProperty(
        name="Operation",
        items=[
            ("ADD", "Add", ""),
            ("SUBTRACT", "Subtract", ""),
            ("MULTIPLY", "Multiply", ""),
            ("DIVIDE", "Divide", ""),
            ("POWER", "Power", ""),
            ("MINIMUM", "Minimum", ""),
            ("MAXIMUM", "Maximum", ""),
        ],
        default="ADD",
    )

    def init(self, context):
        a = self.inputs.new("NodeSocketInt", "A")
        b = self.inputs.new("NodeSocketInt", "B")
        try:
            a.default_value = 0.0
            b.default_value = 0.0
        except Exception:
            pass
        self.outputs.new("NodeSocketInt", "Result")

    def draw_buttons(self, context, layout):
        layout.prop(self, "operation", text="")

class FloatMath(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_FloatMath"
    bl_label = "Math (Float)"
    bl_icon = "NODE_SOCKET_FLOAT"

    operation: EnumProperty(
        name="Operation",
        items=[
            ("ADD", "Add", ""),
            ("SUBTRACT", "Subtract", ""),
            ("MULTIPLY", "Multiply", ""),
            ("DIVIDE", "Divide", ""),
            ("POWER", "Power", ""),
            ("MINIMUM", "Minimum", ""),
            ("MAXIMUM", "Maximum", ""),
        ],
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

class VectorMath(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_VectorMath"
    bl_label = "Vector Math"
    bl_icon = "NODE_SOCKET_VECTOR"

    operation: EnumProperty(
        name="Operation",
        items=[
            ("ADD", "Add", ""),
            ("SUBTRACT", "Subtract", ""),
            ("MULTIPLY", "Multiply", "Component-wise multiply"),
            ("DOT", "Dot", ""),
            ("CROSS", "Cross", ""),
            ("SCALE", "Scale", "Vector * Float"),
            ("LENGTH", "Length", "Returns float length"),
            ("NORMALIZE", "Normalize", ""),
        ],
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

class CombineXYZ(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_CombineXYZ"
    bl_label = "Combine XYZ"
    bl_icon = "EMPTY_AXIS"

    def init(self, context):
        self.inputs.new("NodeSocketFloat", "X")
        self.inputs.new("NodeSocketFloat", "Y")
        self.inputs.new("NodeSocketFloat", "Z")
        self.outputs.new("NodeSocketVector", "Vector")

class SeparateXYZ(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_SeparateXYZ"
    bl_label = "Separate XYZ"
    bl_icon = "EMPTY_AXIS"

    def init(self, context):
        self.inputs.new("NodeSocketVector", "Vector")
        self.outputs.new("NodeSocketFloat", "X")
        self.outputs.new("NodeSocketFloat", "Y")
        self.outputs.new("NodeSocketFloat", "Z")

class MatrixMultiply(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_MatrixMultiply"
    bl_label = "Matrix Multiply"
    bl_icon = "NODE_SOCKET_MATRIX"

    def init(self, context):
        self.inputs.new("NodeSocketMatrix", "A")
        self.inputs.new("NodeSocketMatrix", "B")
        self.outputs.new("NodeSocketMatrix", "Result")

class ComposeMatrix(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_ComposeMatrix"
    bl_label = "Compose Matrix"
    bl_icon = "NODE_SOCKET_MATRIX"

    def init(self, context):
        self.inputs.new("NodeSocketVector", "Position")
        self.inputs.new("NodeSocketVector", "Rotation")
        self.inputs.new("NodeSocketVector", "Scale")
        self.outputs.new("NodeSocketMatrix", "Matrix")

class DecomposeMatrix(Node, AnimGraphNodeMixin):
    bl_idname = "ANIMGRAPH_DecomposeMatrix"
    bl_label = "Decompose Matrix"
    bl_icon = "NODE_SOCKET_MATRIX"

    def init(self, context):
        self.inputs.new("NodeSocketMatrix", "Matrix")
        self.outputs.new("NodeSocketVector", "Position")
        self.outputs.new("NodeSocketVector", "Rotation")
        self.outputs.new("NodeSocketVector", "Scale")
