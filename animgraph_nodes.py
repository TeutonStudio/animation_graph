# animation_graph/riggraph_nodes.py

import bpy
from bpy.types import NodeTree, Node, NodeSocket, FunctionNodeIntegerMath
from bpy.props import FloatProperty, EnumProperty, FloatVectorProperty, StringProperty, PointerProperty
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories
from .Nodes.group_nodes import AnimGroupNode, AnimGroupInputNode, AnimGroupOutputNode
from .Nodes.mathe_nodes import IntConst, FloatConst, VectorConst, MatrixConst, IntMath, FloatMath, VectorMath, CombineXYZ, SeparateXYZ, MatrixMultiply, ComposeMatrix, DecomposeMatrix
from .Nodes.bone_node import NodeSocketBone, DefineBoneNode
from .Nodes.bone_transform_nodes import DefineBoneTransform, ReadBoneTransform


# --------------------------------------------------------------------
# register / unregister
# --------------------------------------------------------------------


def register():
    for c in _CLASSES: bpy.utils.register_class(c)
    register_node_categories(_NODE_CATS_ID, _NODE_CATEGORIES)

def unregister():
    try: unregister_node_categories(_NODE_CATS_ID)
    except Exception: pass
    for c in reversed(_CLASSES): bpy.utils.unregister_class(c)

class AnimGraphNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        # Add-Menü darf immer verfügbar sein
        return True


_NODE_CATS_ID = "ANIMGRAPH_NODE_CATEGORIES"
_NODE_CATEGORIES = [
    AnimGraphNodeCategory(
        "ANIMGRAPH_RIGGRAPH",
        "RigGraph",
        items=[
            NodeItem(AnimGroupNode.bl_idname),
            NodeItem(AnimGroupInputNode.bl_idname),
            NodeItem(AnimGroupOutputNode.bl_idname),
            NodeItem(DefineBoneNode.bl_idname),
            NodeItem(DefineBoneTransform.bl_idname),
            NodeItem(ReadBoneTransform.bl_idname),
        ],
    ),

    AnimGraphNodeCategory(
        "ANIMGRAPH_INPUT_CONSTANT",
        "Input: Constant",
        items=[
            NodeItem(IntConst.bl_idname),
            NodeItem(FloatConst.bl_idname),
            NodeItem(VectorConst.bl_idname),
            NodeItem(MatrixConst.bl_idname),
        ],
    ),

    AnimGraphNodeCategory(
        "ANIMGRAPH_UTILITY_MATH",
        "Utility: Math",
        items=[
            NodeItem(IntMath.bl_idname),
            NodeItem(FloatMath.bl_idname),
            NodeItem(VectorMath.bl_idname),
            NodeItem(MatrixMultiply.bl_idname),
        ],
    ),

    AnimGraphNodeCategory(
        "ANIMGRAPH_MATH",
        "Math",
        items=[
            NodeItem(IntMath.bl_idname),
            NodeItem(FloatMath.bl_idname),
            NodeItem(VectorMath.bl_idname),
            NodeItem(CombineXYZ.bl_idname),
            NodeItem(SeparateXYZ.bl_idname),
            NodeItem(MatrixMultiply.bl_idname),
            NodeItem(ComposeMatrix.bl_idname),
            NodeItem(DecomposeMatrix.bl_idname),
        ],
    ),
]


_CLASSES = (
    NodeSocketBone,
    DefineBoneNode,
    AnimGroupNode,
    AnimGroupInputNode,
    AnimGroupOutputNode,
    DefineBoneTransform,
    ReadBoneTransform,

    IntConst, FloatConst, VectorConst, MatrixConst,
    IntMath, FloatMath, VectorMath,
    CombineXYZ, SeparateXYZ,
    MatrixMultiply, ComposeMatrix, DecomposeMatrix,
)