# animation_graph/riggraph_ui.py
import bpy

from .Core.node_tree import AnimNodeTree
from .UI import interface_manage, group_operator

_MODULES = [
    # interface_manage, # TODO
    group_operator,
]

def register(): 
    for m in _MODULES: m.register()
    
def unregister(): 
    for m in reversed(_MODULES): m.unregister()
