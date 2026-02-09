# animation_graph/__init__.py

bl_info = {
    "name": "AnimationGraph",
    "author": "TeutonStudios",
    "version": (0, 1, 2),
    "blender": (5, 0, 0),
    "category": "Animation",
}

import importlib
import bpy

from .Core import node_tree
from . import animgraph_eval, animgraph_nodes, animgraph_ui

_modules = (node_tree, animgraph_nodes, animgraph_ui, animgraph_eval)

def register():
    for m in _modules: importlib.reload(m).register()

def unregister():
    for m in reversed(_modules): m.unregister()
