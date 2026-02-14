# animation_graph/riggraph_nodes.py

import bpy
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories
from .Nodes import bone_nodes, mathe_nodes, iteration_nodes, bone_transform_nodes
from .Nodes.group_node import AnimNodeGroup


# --------------------------------------------------------------------
# register / unregister
# --------------------------------------------------------------------
_MODULES = [
    mathe_nodes,
    bone_nodes,
    iteration_nodes,
    bone_transform_nodes,
]

def register():
    for m in _MODULES: m.register()
    for c in _CLASSES: bpy.utils.register_class(c)
    register_node_categories(_NODE_CATS_ID, _NODE_CATEGORIES)

def unregister():
    try: unregister_node_categories(_NODE_CATS_ID)
    except Exception: pass
    for m in reversed(_MODULES): m.unregister()
    for c in reversed(_CLASSES): bpy.utils.unregister_class(c)

class AnimGraphNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context): return True


_NODE_CATS_ID = "ANIMGRAPH_NODE_CATEGORIES"
_NODE_CATEGORIES = [ # TODO Kontext Menü überarbeiten; Kompatibilität mit NodePieMenu erhalten
    AnimGraphNodeCategory(
        "ANIMGRAPH_RIGGRAPH",
        "RigGraph",
        items=[
            NodeItem("DefineBoneNode"),
            NodeItem("DefineBoneTransformNode"),
            NodeItem("DefineBonePropertyNode"),
            NodeItem("ReadBoneTransformNode"),
            NodeItem("ReadBonePropertyNode"),
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
)
