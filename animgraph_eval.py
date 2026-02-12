# animation_graph/animgraph_eval.py

import bpy
from bpy.app.handlers import persistent, frame_change_post, depsgraph_update_post

from .Core.node_tree import AnimNodeTree

_RUNNING = False

# Persistent pose cache across frames (needed for interpolation / start pose capture)
# Keying is done by nodes themselves (see DefineBoneTransform / ReadBoneTransform implementations)
_POSE_CACHE = {}

# Per-frame evaluation cache to prevent cycles / re-evaluation
_EVAL_CACHE = set()


# --------------------------------------------------------------------
# evaluation context
# --------------------------------------------------------------------

class AnimGraphEvalContext:
    """
    Shared context passed into node.evaluate(...)
    """
    __slots__ = ("eval_cache", "pose_cache", "touched_armatures", "values", "eval_stack")

    def __init__(self, eval_cache, pose_cache):
        self.eval_cache = eval_cache
        self.pose_cache = pose_cache
        self.touched_armatures = set()

        # per-frame runtime channel (Outputs der Nodes)
        self.values = {}

        # recursion / cycle guard for eval_socket()
        self.eval_stack = set()


# --------------------------------------------------------------------
# register / unregister
# --------------------------------------------------------------------

def register():
    if _on_frame_change not in frame_change_post: frame_change_post.append(_on_frame_change)
    if _on_depsgraph_update not in depsgraph_update_post: depsgraph_update_post.append(_on_depsgraph_update)


def unregister():
    if _on_frame_change in frame_change_post: frame_change_post.remove(_on_frame_change)
    if _on_depsgraph_update in depsgraph_update_post: depsgraph_update_post.remove(_on_depsgraph_update)

    _POSE_CACHE.clear()
    _EVAL_CACHE.clear()


# --------------------------------------------------------------------
# tree utilities
# --------------------------------------------------------------------

def _iter_animtrees():
    for ng in bpy.data.node_groups:
        if getattr(ng, "bl_idname", "") == AnimNodeTree.bl_idname:
            yield ng


def _find_nodes(tree, bl_idname):
    return [n for n in getattr(tree, "nodes", []) if getattr(n, "bl_idname", "") == bl_idname]


def _evaluate_tree(tree, scene, ctx):
    """
    Kick off evaluation. We only "tick" transform nodes.
    Everything else is pulled via upstream evaluation when sockets are read.
    """
    for n in _find_nodes(tree, "DefineBoneTransform"):
        # Preferred path: mixin provides eval_upstream (handles caching)
        if hasattr(n, "eval_upstream"):
            n.eval_upstream(tree, scene, ctx)
            continue

        # Fallback: call evaluate directly if present
        fn = getattr(n, "evaluate", None)
        if callable(fn):
            fn(tree, scene, ctx)


# --------------------------------------------------------------------
# handlers
# --------------------------------------------------------------------

@persistent
def _on_frame_change(scene, depsgraph):
    global _RUNNING
    if _RUNNING:
        return

    _RUNNING = True@persistent
def _on_frame_change(scene, depsgraph):
    global _RUNNING
    if _RUNNING:
        return

    _RUNNING = True
    try:
        # Per-frame cache reset
        _EVAL_CACHE.clear()

        ctx = AnimGraphEvalContext(_EVAL_CACHE, _POSE_CACHE)

        for tree in _iter_animtrees():
            _evaluate_tree(tree, scene, ctx)

        # Update once per armature, not per node
        for arm_ob in ctx.touched_armatures:
            try:
                arm_ob.update_tag(refresh={"DATA"})
            except Exception:
                pass

    finally:
        _RUNNING = False
    try:
        _EVAL_CACHE.clear()

        # ctx.values und ctx.eval_stack werden im __init__ neu angelegt
        ctx = AnimGraphEvalContext(_EVAL_CACHE, _POSE_CACHE)

        for tree in _iter_animtrees():
            _evaluate_tree(tree, scene, ctx)

        for arm_ob in ctx.touched_armatures:
            try:
                arm_ob.update_tag(refresh={"DATA"})
            except Exception:
                pass

    finally:
        _RUNNING = False



@persistent
def _on_depsgraph_update(scene, depsgraph):
    if _RUNNING:
        return

    # Keep your UI tweak
    scr = bpy.context.screen
    if scr:
        for area in scr.areas:
            if area.type == "NODE_EDITOR":
                space = area.spaces.active
                if space.edit_tree and getattr(space.edit_tree, "bl_idname", "") == "AnimNodeTree":
                    space.overlay.show_context_path = True

    # Dirty flag handling + optional redraw
    for tree in _iter_animtrees():
        if getattr(tree, "dirty", False):
            tree.dirty = False

            if scr:
                for area in scr.areas:
                    if area.type == "VIEW_3D":
                        area.tag_redraw()
