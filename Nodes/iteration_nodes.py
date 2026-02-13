# animation_graph/Nodes/iteration_nodes.py

import bpy

from .Mixin import AnimGraphNodeMixin


_MISSING = object()



def register():
    for c in _CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(_CLASSES):
        bpy.utils.unregister_class(c)


class AnimNodeRepeatInput(bpy.types.Node, AnimGraphNodeMixin):
    bl_idname = "AnimNodeRepeatInput"
    bl_label = "Repeat Input"
    bl_icon = "DRIVER"

    @classmethod
    def poll(cls, ntree):
        return getattr(ntree, "bl_idname", None) == "AnimNodeTree"

    def init(self, context):
        initial = self.inputs.new("NodeSocketInt", "Initial")
        try:
            initial.default_value = 0
        except Exception:
            pass

        self.outputs.new("NodeSocketInt", "Value")
        self.outputs.new("NodeSocketInt", "Index")

    def evaluate(self, tree, scene, ctx):
        value = self.socket_int(tree, "Initial", scene, ctx, 0)

        out_value = self.outputs.get("Value")
        out_index = self.outputs.get("Index")

        if out_value:
            try:
                out_value.default_value = int(value)
            except Exception:
                pass

        if out_index:
            try:
                out_index.default_value = 0
            except Exception:
                pass

        self.set_output_value(ctx, "Value", int(value))
        self.set_output_value(ctx, "Index", 0)


class AnimNodeRepeatOutput(bpy.types.Node, AnimGraphNodeMixin):
    bl_idname = "AnimNodeRepeatOutput"
    bl_label = "Repeat Output"
    bl_icon = "DRIVER"

    @classmethod
    def poll(cls, ntree):
        return getattr(ntree, "bl_idname", None) == "AnimNodeTree"

    def init(self, context):
        iterations = self.inputs.new("NodeSocketInt", "Iterations")
        try:
            iterations.default_value = 1
        except Exception:
            pass

        self.inputs.new("NodeSocketInt", "Repeat In")
        self.inputs.new("NodeSocketInt", "Value")

        self.outputs.new("NodeSocketInt", "Value")

    def _repeat_input_node(self):
        repeat_in = self.inputs.get("Repeat In")
        if not repeat_in or not repeat_in.is_linked or not repeat_in.links:
            return None

        node = repeat_in.links[0].from_node
        if getattr(node, "bl_idname", "") != "AnimNodeRepeatInput":
            return None
        return node

    def evaluate(self, tree, scene, ctx):
        iterations = max(0, self.socket_int(tree, "Iterations", scene, ctx, 1))

        repeat_input = self._repeat_input_node()
        if repeat_input is None:
            value = self.socket_int(tree, "Value", scene, ctx, 0)
            out = self.outputs.get("Value")
            if out:
                try:
                    out.default_value = int(value)
                except Exception:
                    pass
            self.set_output_value(ctx, "Value", int(value))
            return

        state = repeat_input.socket_int(tree, "Initial", scene, ctx, 0)

        repeat_ptr = repeat_input.as_pointer()
        repeat_value_key = (repeat_ptr, "Value")
        repeat_index_key = (repeat_ptr, "Index")

        prev_repeat_value = ctx.values.get(repeat_value_key, _MISSING)
        prev_repeat_index = ctx.values.get(repeat_index_key, _MISSING)

        try:
            for i in range(iterations):
                # Recompute loop body each pass.
                ctx.eval_cache.clear()

                ctx.values[repeat_value_key] = int(state)
                ctx.values[repeat_index_key] = int(i)

                state = _to_int(self.socket_int(tree, "Value", scene, ctx, state), state)
        finally:
            if prev_repeat_value is _MISSING:
                ctx.values.pop(repeat_value_key, None)
            else:
                ctx.values[repeat_value_key] = prev_repeat_value

            if prev_repeat_index is _MISSING:
                ctx.values.pop(repeat_index_key, None)
            else:
                ctx.values[repeat_index_key] = prev_repeat_index

        out = self.outputs.get("Value")
        if out:
            try:
                out.default_value = int(state)
            except Exception:
                pass

        self.set_output_value(ctx, "Value", int(state))

def _to_int(value, fallback=0):
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return int(fallback)


_CLASSES = [
    AnimNodeRepeatInput,
    AnimNodeRepeatOutput,
]
