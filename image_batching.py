"""
ComfyUI Custom Node: Dynamic Multi-Input Node
=============================================
A boilerplate for a custom node that supports dynamically added/removed inputs.

Features:
  - Starts with a configurable minimum number of inputs
  - "Add Input" / "Remove Input" buttons rendered via JavaScript widget
  - Each input slot is typed (STRING here, but easily swapped)
  - INPUT_TYPES uses the special "required" / "optional" split
  - OUTPUT_NODE flag and RETURN_TYPES show how to return values
"""

from typing import Any


# ──────────────────────────────────────────────────────────────────────────────
# Node Definition
# ──────────────────────────────────────────────────────────────────────────────

class DynamicInputNode:
    """
    A ComfyUI node whose input count can be changed at runtime.

    The JavaScript companion file (dynamic_input_node.js) handles the
    "Add Input" / "Remove Input" buttons and keeps the widget list in sync
    with the server-side INPUT_TYPES.
    """

    # ------------------------------------------------------------------
    # Class-level configuration
    # ------------------------------------------------------------------
    MAX_INPUTS: int = 16        # upper guard rail (optional)
    INPUT_PREFIX: str = "image_" # slot names become input_0, input_1, …

    # ------------------------------------------------------------------
    # ComfyUI node metadata
    # ------------------------------------------------------------------
    CATEGORY = "DigbyWan/keyframes"
    FUNCTION = "process"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    OUTPUT_NODE = True          # set True if this node triggers side-effects

    # ------------------------------------------------------------------
    # INPUT_TYPES
    # ------------------------------------------------------------------
    @classmethod
    def INPUT_TYPES(cls) -> dict:
        """
        Called by ComfyUI to build the initial input schema.

        The JavaScript widget is responsible for adding extra slots beyond
        MIN_INPUTS at runtime; those slots must mirror this schema exactly
        so ComfyUI can validate them.
        """
        required: dict[str, Any] = {}
        optional: dict[str, Any] = {}

        required[f"{cls.INPUT_PREFIX}0"] = ("IMAGE",)

        for i in range(1,cls.MAX_INPUTS):
            optional[f"{cls.INPUT_PREFIX}{i}"] = (
                "IMAGE", 
            )

        return {"required": required, "optional": optional, }

    # ------------------------------------------------------------------
    # IS_CHANGED  (optional – return a hash if you need cache-busting)
    # ------------------------------------------------------------------
    @classmethod
    def IS_CHANGED(cls, **kwargs) -> str:  # noqa: N802
        """
        Return a unique value whenever the node's output would differ.
        Returning NaN forces re-execution every time (useful during dev).
        """
        import float
        return float("nan")

    # ------------------------------------------------------------------
    # VALIDATE_INPUTS  (optional – return True or an error string)
    # ------------------------------------------------------------------
    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs) -> bool | str:  # noqa: N802
        return True

    # ------------------------------------------------------------------
    # Main processing function
    # ------------------------------------------------------------------
    def process(self, input_count: int, **kwargs: Any) -> tuple[str]:
        """
        Collect all dynamic input values and do something useful with them.

        Args:
            input_count: How many input_N slots are currently active.
            **kwargs:    All widget / input values, including input_0…input_N.

        Returns:
            A tuple matching RETURN_TYPES.
        """
        # ── 1. Gather the active inputs in order ──────────────────────
        inputs: list[str] = []
        for i in range(input_count):
            key = f"{self.INPUT_PREFIX}{i}"
            value = kwargs.get(key, "")
            inputs.append(value)

        # ── 2. Your processing logic goes here ────────────────────────
        #       Replace this stub with whatever the node should do.
        result = self._combine_inputs(inputs)

        # ── 3. Return a tuple that matches RETURN_TYPES ───────────────
        return (result,)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def _combine_inputs(self, inputs: list[str]) -> str:
        """
        Default behaviour: join all non-empty inputs with a newline.
        Override or replace with your real logic.
        """
        non_empty = [v for v in inputs if v.strip()]
        if not non_empty:
            return ""
        return "\n".join(non_empty)

