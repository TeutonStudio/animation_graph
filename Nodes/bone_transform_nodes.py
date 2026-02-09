# animation_graph/Nodes/bone_transform_node.py

import bpy
from bpy.types import Node
from bpy.props import EnumProperty
from ..helpers import AnimGraphNodeMixin


class _BoneTransform(Node,AnimGraphNodeMixin):
    bl_icon = "CON_TRANSFORM"

    representation: EnumProperty(
        name="Representation",
        items=[
            ("COMPONENTS", "Components", "Output Position/Rotation/Scale"),
            ("MATRIX", "Matrix", "Output Matrix"),
        ],
        default="COMPONENTS",
        update=update_representation,
    )

    apply_mode: EnumProperty(
        name="Apply",
        items=[
            ("TO", "To (Absolute)", "Read transform at a given frame"),
            ("DELTA", "Delta", "Output change between start and end"),
        ],
        default="TO",
        update=update_mode,
    )

    def update_representation(self,context): pass
    def update_mode(self,context): pass

    def _update_transform_socket(self, sockets):
        use_matrix = (self.representation == "MATRIX")

        # Representation toggles (outputs)
        for name in ("Position", "Rotation", "Scale"):
            if name in sockets: sockets[name].hide = use_matrix
        if "Matrix" in sockets:
            sockets["Matrix"].hide = not use_matrix

    def init(self, context): 
        b = self.inputs.new("NodeSocketBone", "Bone")
        s = self.inputs.new("NodeSocketInt", "Start")
        d = self.inputs.new("NodeSocketInt", "Duration")
        try:
            s.default_value = 0
            d.default_value = 10
        except Exception: pass

    def draw_buttons(self, context, layout): 
        col = layout.column(align=True)
        col.prop(self, "representation", text="")
        col.prop(self, "apply_mode", text="")


class DefineBoneTransform(_BoneTransform):
    bl_idname = "ANIMGRAPH_DefineBoneTransform"
    bl_label = "Transform Bone"

    # TODO
    interpolation: EnumProperty(
        name="Interpolation",
        items=[
            ("CONSTANT", "Constant", "Jump at end"),
            ("LINEAR", "Linear", "Linear transition"),
            ("BEZIER", "Bezier", "Smooth (with easing)"),
        ],
        default="BEZIER",
    )

    easing: EnumProperty(
        name="Easing",
        items=[
            ("AUTO", "Auto", "Default (Ease In/Out-ish)"),
            ("EASE_IN", "Ease In", "Slow start, then faster"),
            ("EASE_OUT", "Ease Out", "Fast start, then slower"),
            ("EASE_IN_OUT", "Ease In/Out", "Slow start & end"),
        ],
        default="AUTO",
    )

    def update_representation(self,context): self.update()
    def update_mode(self,context): self.update()

    def init(self, context):
        super().init(context)
        # Components inputs
        p = self.inputs.new("NodeSocketVector", "Position")
        r = self.inputs.new("NodeSocketVector", "Rotation")
        sc = self.inputs.new("NodeSocketVector", "Scale")
        try:
            p.default_value = (0.0, 0.0, 0.0)
            r.default_value = (0.0, 0.0, 0.0)
            sc.default_value = (1.0, 1.0, 1.0)
        except Exception: pass

        # Matrix input (built-in socket type, if available in your Blender)
        m = self.inputs.new("NodeSocketMatrix", "Matrix")
        # Some Blender versions expose default_value, some don't. Guard it.
        try:
            # 4x4 identity as flat list (column-major in many Blender APIs)
            m.default_value = (
                (1.0, 0.0, 0.0, 0.0),
                (0.0, 1.0, 0.0, 0.0),
                (0.0, 0.0, 1.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
            )
        except Exception: pass

        self.outputs.new("NodeSocketInt", "End")
        self.update()
    def update(self):
        self._update_transform_socket({s.name: s for s in getattr(self, "inputs", [])})

    def draw_buttons(self, context, layout):
        super().draw_buttons(context,layout)
        layout.separator()
        col = layout.column(align=True)
        col.prop(self, "interpolation")
        col.prop(self, "easing")

class ReadBoneTransform(_BoneTransform):
    bl_idname = "ANIMGRAPH_ReadBoneTransform"
    bl_label = "Bone Transform"

    def update_representation(self,context): self.update()
    def update_mode(self,context): pass

    def init(self, context):
        super().init(context)
        # Outputs
        self.outputs.new("NodeSocketVector", "Position")
        self.outputs.new("NodeSocketVector", "Rotation")
        self.outputs.new("NodeSocketVector", "Scale")
        self.outputs.new("NodeSocketMatrix", "Matrix")
        self.outputs.new("NodeSocketFloat", "Length")
        self.update()

    def update(self):
        ins = {s.name: s for s in getattr(self, "inputs", [])}
        outs = {s.name: s for s in getattr(self, "outputs", [])}

        self._update_transform_socket(outs)

        use_delta = (getattr(self, "apply_mode", "TO") == "DELTA")
        if "End" in ins: ins["End"].hide = not use_delta

    # def draw_buttons(self, context, layout): passs
