# animation_graph/Nodes/iteration_nodes.py

from .Mixin import AnimGraphNodeMixin
import bpy

def register():
    for c in _CLASSES: bpy.utils.register_class(c)
def unregister():
    for c in reversed(_CLASSES): bpy.utils.unregister_class(c)

class AnimNodeRepeatInput(bpy.types.Node, AnimGraphNodeMixin):
    pass

class AnimNodeRepeatOutput(bpy.types.Node, AnimGraphNodeMixin):
    pass

_CLASSES = [
    AnimNodeRepeatInput,
    AnimNodeRepeatOutput,
]
