# animation_graph/riggraph_nodes.py

import bpy
from bpy.types import NodeTree, Node, NodeSocket, FunctionNodeIntegerMath
from bpy.props import FloatProperty, EnumProperty, FloatVectorProperty, StringProperty, PointerProperty
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories
from .Nodes import mathe_nodes
from .Nodes.group_nodes import AnimNodeGroup
from .Nodes.bone_node import DefineBoneNode
from .Nodes.bone_transform_nodes import DefineBoneTransform, ReadBoneTransform


# --------------------------------------------------------------------
# register / unregister
# --------------------------------------------------------------------


def register():
    mathe_nodes.register()
    for c in _CLASSES: bpy.utils.register_class(c)
    register_node_categories(_NODE_CATS_ID, _NODE_CATEGORIES)

def unregister():
    mathe_nodes.unregister()
    try: unregister_node_categories(_NODE_CATS_ID)
    except Exception: pass
    for c in reversed(_CLASSES): bpy.utils.unregister_class(c)

class AnimGraphNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context): return True


_NODE_CATS_ID = "ANIMGRAPH_NODE_CATEGORIES"
_NODE_CATEGORIES = [
    AnimGraphNodeCategory(
        "ANIMGRAPH_RIGGRAPH",
        "RigGraph",
        items=[
            NodeItem("DefineBoneNode"),
            NodeItem("DefineBoneTransform"),
            NodeItem("ReadBoneTransform"),
        ],
    ),

    AnimGraphNodeCategory(
        "ANIMGRAPH_INPUT_CONSTANT",
        "Input: Constant",
        items=[
            NodeItem("IntConst"),
            NodeItem("FloatConst"),
            NodeItem("VectorConst"),
            NodeItem("RotationConst"),
            NodeItem("TranslationConst"),
            NodeItem("MatrixConst"),
        ],
    ),

    AnimGraphNodeCategory(
        "ANIMGRAPH_UTILITY_MATH",
        "Utility: Math",
        items=[
            NodeItem("IntMath"),
            NodeItem("FloatMath"),
            NodeItem("VectorMath"),
            NodeItem("MatrixMath"),
        ],
    ),

    AnimGraphNodeCategory(
        "ANIMGRAPH_ADAPT",
        "Adapter",
        items=[
            NodeItem("CombineXYZ"),
            NodeItem("SeparateXYZ"),
            NodeItem("ComposeMatrix"),
            NodeItem("DecomposeMatrix"),
        ],
    ),

    AnimGraphNodeCategory(
        "ANIMGRAPH_GROUP",
        "Group",
        items=[
            NodeItem("AnimNodeGroup"),
            NodeItem("NodeGroupInput"),
            NodeItem("NodeGroupOutput"),
        ],
    ),
]


_CLASSES = (
    AnimNodeGroup,

    DefineBoneNode,
    DefineBoneTransform,
    ReadBoneTransform,
)