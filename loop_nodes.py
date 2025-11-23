from comfy_execution.graph_utils import GraphBuilder, is_link
from nodes import NODE_CLASS_MAPPINGS as ALL_NODE_CLASS_MAPPINGS
import torch
import comfy.utils
#
# Shared functions
#

def explore_dependencies(node_id, dynprompt, upstream, parent_ids):
    node_info = dynprompt.get_node(node_id)
    if "inputs" not in node_info:
        return

    for k, v in node_info["inputs"].items():
        if is_link(v):
            parent_id = v[0]
            display_id = dynprompt.get_display_node_id(parent_id)
            display_node = dynprompt.get_node(display_id)
            class_type = display_node["class_type"]
            if class_type not in {'DigbyLoopClose'}:
                parent_ids.append(display_id)
            if parent_id not in upstream:
                upstream[parent_id] = []
                explore_dependencies(parent_id, dynprompt, upstream, parent_ids)
            upstream[parent_id].append(node_id)
    
    # Organize the output as a list
    parent_ids = list(set(parent_ids))

def explore_output_nodes(dynprompt, upstream, output_nodes, parent_ids):
    for parent_id in upstream:
        display_id = dynprompt.get_display_node_id(parent_id)
        for output_id in output_nodes:
            id = output_nodes[output_id][0]
            if id in parent_ids and display_id == id and output_id not in upstream[parent_id]:
                if '.' in parent_id:
                    arr = parent_id.split('.')
                    arr[len(arr)-1] = output_id
                    upstream[parent_id].append('.'.join(arr))
                else:
                    upstream[parent_id].append(output_id)


def collect_contained(node_id, upstream, contained):
    if node_id not in upstream:
        return
    for child_id in upstream[node_id]:
        if child_id not in contained:
            contained[child_id] = True
            collect_contained(child_id, upstream, contained)

#
#
#

class DigbyLoopOpen:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
            },
            "optional": {
                "previous_loop": ("DIGBY_LOOP", { "rawLink" : True}),
                "loop_variables": ("DIGBY_LOOP_VARIABLES", { "forceInput" : True}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "loop_index": ("INT", {"default": 0}),
                "previous_loop_variables": ("DIGBY_LOOP_VARIABLES", {"default": None})
            }
        }
        return inputs

    RETURN_TYPES = tuple(["FLOW_CONTROL", "DIGBY_LOOP_VARIABLES", "INT", ])
    RETURN_NAMES = tuple(["loop_close", "loop_variables", "loop_index", ])
    FUNCTION = "loop_open"
    CATEGORY = "DigbyWan/loop"

    def loop_open(self, previous_loop=None, previous_loop_variables=None, loop_variables=None, unique_id=None, 
                 loop_index=0):
                    
        # Output a valid loop_variables structure                          
        if (previous_loop_variables is None):
            if (loop_variables is not None):
                previous_loop_variables = loop_variables
            else:
                previous_loop_variables = { "string_val": None, "int_val": None, "float_val": None, "images": None, }

        return tuple(["stub", previous_loop_variables, loop_index ])

class DigbyLoopClose:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "how_many_loops": ("INT", {"default": 1, "min":1, "tooltip":"Number of times to repeat the loop."}),
                "loop_open": ("FLOW_CONTROL", {"rawLink": True}),
                "loop_variables": ("DIGBY_LOOP_VARIABLES", {"forceInput":True, "tooltip":"Link to the last node inside the loop.  This defines the node loop to repeat."}),
            },
            "hidden": {
                "dynprompt": "DYNPROMPT",
                "unique_id": "UNIQUE_ID",
                "loop_index": ("INT", {"default": 0}),
            }
        }
        return inputs

    RETURN_TYPES = ("DIGBY_LOOP", "DIGBY_LOOP_VARIABLES",)
    RETURN_NAMES = ("next_loop", "loop_variables", )
    FUNCTION = "loop_close"
    CATEGORY = "DigbyWan/loop"
    OUTPUT_NODE  = True

    def loop_close(self, how_many_loops, loop_open, loop_variables,
                 dynprompt=None, unique_id=None, loop_index=0, ):
        
        loop_open_node = dynprompt.get_node(loop_open[0])
        assert loop_open_node["class_type"] in {"DigbyLoopOpen"}, "Must be linked to a 'Digby Loop Open' Node"

        print(f"Iteration {loop_index+1} of {how_many_loops}")
        
        # 检查是否继续循环  Check whether to continue the loop.
        if loop_index >= how_many_loops - 1:
            print(f"Loop finished with {loop_index + 1} iterations") 
            return ("loop_link", loop_variables, )

        # 准备下一次循环 Preparing for the next cycle
        this_node = dynprompt.get_node(unique_id)
        upstream = {}
        parent_ids = []
        explore_dependencies(unique_id, dynprompt, upstream, parent_ids)
 
        # 获取并处理输出节点 Get and process the output node
        prompts = dynprompt.get_original_prompt()
        output_nodes = {}
        for id in prompts:
            node = prompts[id]
            if "inputs" not in node:
                continue
            class_type = node["class_type"]
            if class_type == this_node["class_type"]:
                continue
            if class_type in ALL_NODE_CLASS_MAPPINGS:
                class_def = ALL_NODE_CLASS_MAPPINGS[class_type]
                if hasattr(class_def, 'OUTPUT_NODE') and class_def.OUTPUT_NODE == True:
                    for k, v in node['inputs'].items():
                        if is_link(v):
                            output_nodes[id] = v

        # 创建新图 Create a new graph
        graph = GraphBuilder()
        explore_output_nodes(dynprompt, upstream, output_nodes, parent_ids)
        
        contained = {}
        open_node = loop_open[0]
        collect_contained(open_node, upstream, contained)
        contained[unique_id] = True
        contained[open_node] = True

        # 创建节点 Create a node
        for node_id in contained:
            original_node = dynprompt.get_node(node_id)
            node = graph.node(original_node["class_type"], 
                            "Recurse" if node_id == unique_id else node_id)
            node.set_override_display_id(node_id)
            
        # 设置连接 Set up connection
        for node_id in contained:
            original_node = dynprompt.get_node(node_id)
            node = graph.lookup_node("Recurse" if node_id == unique_id else node_id)
            for k, v in original_node["inputs"].items():
                if is_link(v) and v[0] in contained:
                    parent = graph.lookup_node(v[0])
                    node.set_input(k, parent.out(v[1]))
                else:
                    node.set_input(k, v)

        # 设置节点参数 Set node parameters
        my_clone = graph.lookup_node("Recurse")
        my_clone.set_input("loop_index", loop_index + 1)
        
        new_open = graph.lookup_node(open_node)
        new_open.set_input("loop_index", loop_index + 1)
        new_open.set_input("loop_variables", loop_variables)

        print(f"Continuing to iteration {loop_index + 2}")

        return {
            "result": tuple([my_clone.out(0), my_clone.out(1)]),
            "expand": graph.finalize(),
        }
    
class DigbyLoopVariablesInit:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "string_val": ("STRING", { "default": ""}),
            },
            "optional":{
                "int_val": ("INT",),
                "float_val": ("FLOAT",),
                "images": ("IMAGE",),
            }
        }
        return inputs

    RETURN_TYPES = ("DIGBY_LOOP_VARIABLES", )
    RETURN_NAMES = ("loop_variables",)
    FUNCTION = "loop_variables_init"
    CATEGORY = "DigbyWan/loop"
    OUTPUT_NODE = True

    def loop_variables_init(self, string_val, int_val=None, float_val=None, images=None, ):
        loop_variables = {
            "string_val": string_val,
            "int_val" : int_val,
            "float_val": float_val,
            "images": images,
            "image_accumulator" : None,
        }
        return([loop_variables])

class DigbyLoopVariables:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "loop_variables": ("DIGBY_LOOP_VARIABLES", {"forceInput": True} ),
            },
            "optional":{
                "images": ("IMAGE",),
                "string_val": ("STRING", {"forceInput": True}),
                "int_val": ("INT",{"forceInput": True}),
                "float_val": ("FLOAT",{"forceInput": True}),
                "image_accumulator": ("IMAGE",),
            }
        }
        return inputs

    RETURN_TYPES = ("DIGBY_LOOP_VARIABLES", "IMAGE", "STRING", "INT", "FLOAT", "IMAGE" )
    RETURN_NAMES = ("loop_variables", "images", "string_val", "int_val", "float_val", "stored_images")
    FUNCTION = "loop_variables_set"
    CATEGORY = "DigbyWan/loop"
    OUTPUT_NODE = True

    def loop_variables_set(self, loop_variables, string_val=None, int_val=None, float_val=None, images=None, image_accumulator=None,):
        if images is not None: loop_variables["images"] = images
        if string_val is not None: loop_variables["string_val"] = string_val
        if int_val is not None: loop_variables["int_val"] = int_val
        if float_val is not None: loop_variables["float_val"] = float_val
        if image_accumulator is not None:
            if loop_variables["image_accumulator"] is None:
                loop_variables["image_accumulator"] = image_accumulator
            else:
                image1 = loop_variables["image_accumulator"]
                if image1.shape[1:] != image_accumulator.shape[1:]:
                    image_accumulator = comfy.utils.common_upscale(image_accumulator.movedim(-1,1), image1.shape[2], image1.shape[1], "bilinear", "center").movedim(1,-1)
                loop_variables["image_accumulator"] = torch.cat((image1, image_accumulator), dim=0)

        return([loop_variables, loop_variables["images"], loop_variables["string_val"], loop_variables["int_val"], loop_variables["float_val"], loop_variables["image_accumulator"]])

