# animation_graph/Nodes/mathe_nodes.py

from .mathematik import constants, calculators, adapters

_MODULE = [
    constants,
    calculators,
    adapters,
]

def register():
    for m in _MODULE: m.register()

def unregister():
    for m in reversed(_MODULE): m.unregister()
