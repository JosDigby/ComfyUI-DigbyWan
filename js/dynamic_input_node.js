/**
 * dynamic_input_node.js
 * ──────────────────────────────────────────────────────────────────────────
 * ComfyUI front-end extension for DynamicInputNode.
 *
 * What it does:
 *   • Adds "＋ Add Input" and "－ Remove Input" buttons to the node.
 *   • Dynamically creates / removes input slots on the graph canvas.
 *   • Keeps the hidden `input_count` widget in sync so Python always
 *     knows how many slots to expect.
 *
 * File location inside your custom-node folder:
 *   <custom_nodes>/<your_node_pack>/js/dynamic_input_node.js
 *
 * ComfyUI picks up .js files automatically from a `js/` subfolder when
 * your __init__.py exports WEB_DIRECTORY = "./js".
 * ──────────────────────────────────────────────────────────────────────────
 */

import { app } from "../../scripts/app.js";

// ── Constants (must match the Python class) ───────────────────────────────
const NODE_TYPE    = "DigbyImageBatch";
const INPUT_PREFIX = "image";
const MAX_INPUTS   = 16;


// ── Extension registration ────────────────────────────────────────────────
app.registerExtension({
  name: "DigbyImageBatch",

  // ── Called once for every node of our type when it is created ──────────
  async nodeCreated(node) {
    if (node.comfyClass !== NODE_TYPE) return;

    const baseGetConnectionPos = node.getConnectionPos.bind(node);

    node.getConnectionPos = function(is_input, slot_number, out) {
        if (is_input && slot_number === 5) {
            // Stack it on slot 0 so it doesn't take up space
            return baseGetConnectionPos(is_input, 0, out);
        }
        return baseGetConnectionPos(is_input, slot_number, out);
    };


    // ── Helper: rebuild visible slot labels ──────────────────────────────
    const relabelInputs = () => {
      console.log("[Digby] started relabelInputs")
      node.inputs?.forEach((input, idx) => {
        console.log(input)
        console.warn("[Digby] Reading inputs and trying to hide them")
      });
    };

    // ── Restore state after graph load ───────────────────────────────────
    //    ComfyUI serialises widget values; on reload we re-create any extra
    //    inputs that were present when the graph was saved.
    const onConfigure = node.onConfigure?.bind(node);
    node.onConfigure = function (config) {
      onConfigure?.(config);

      relabelInputs();
      node.setSize(node.computeSize());
    };

    // Initial label pass
    console.log("[Digby] in the nodeCreate function")
    relabelInputs();
  },
});
