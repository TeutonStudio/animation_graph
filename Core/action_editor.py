# animation_graph/Core/action_editor.py

import bpy

from .node_tree import AnimNodeTree
from .helper_methoden import _on_action_input_changed, _poll_armature_obj, _enum_slot_bones, _on_slot_armature_changed

def register(): 
    for c in _CLASSES: bpy.utils.register_class(c)
    bpy.types.Action.animgraph_input_values = bpy.props.CollectionProperty(
        name="AnimGraph Inputs",
        type=AnimGraphActionInputValue,
    )
def unregister(): 
    if hasattr(bpy.types.Action, "animgraph_input_values"):
        del bpy.types.Action.animgraph_input_values
    for c in reversed(_CLASSES): bpy.utils.unregister_class(c)



class AnimGraphActionInputValue(bpy.types.PropertyGroup):
    identifier: bpy.props.StringProperty()
    name: bpy.props.StringProperty()
    socket_type: bpy.props.StringProperty()

    int_value: bpy.props.IntProperty(
        name="Value",
        default=0,
        update=_on_action_input_changed,
    )
    float_value: bpy.props.FloatProperty(
        name="Value",
        default=0.0,
        update=_on_action_input_changed,
    )
    vector_value: bpy.props.FloatVectorProperty(
        name="Value",
        size=3,
        default=(0.0, 0.0, 0.0),
        update=_on_action_input_changed,
    )
    matrix_value: bpy.props.FloatVectorProperty(
        name="Value",
        size=16,
        default=(
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        ),
        update=_on_action_input_changed,
    )
    bone_armature_obj: bpy.props.PointerProperty(
        name="Armature",
        description="Armature object",
        type=bpy.types.Object,
        poll=_poll_armature_obj,
        update=_on_slot_armature_changed,
    )
    bone_name: bpy.props.EnumProperty(
        name="Bone",
        description="Bone to use",
        items=_enum_slot_bones,
        update=_on_action_input_changed,
    )


_CLASSES = [
    AnimGraphActionInputValue,
]
