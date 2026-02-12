# animation_graph/riggraph_ui.py
import bpy

from .Core.node_tree import AnimNodeTree
from .UI import group_operator, action_panel

_MODULES = [
    group_operator,
    action_panel,
]

def register(): 
    for m in _MODULES: m.register()
    
def unregister(): 
    for m in reversed(_MODULES): m.unregister()

