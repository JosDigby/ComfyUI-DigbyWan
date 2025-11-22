from comfy_execution.graph_utils import GraphBuilder, is_link
from nodes import NODE_CLASS_MAPPINGS as ALL_NODE_CLASS_MAPPINGS

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
            if class_type not in {'DigbyLoopClose', 'DigbyLoopCloseState'}:
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
                "max_iterations": ("INT", {"default": 5, "min": 1, "max": 100}),
            },
            "optional": {
                "previous_loop": ("DIGBY_LOOP", { "rawLink" : True}),
            },
            "hidden": {             
                "dynprompt": "DYNPROMPT", 
                "unique_id": "UNIQUE_ID",
                "iteration_count": ("INT", {"default": 0}),
                "previous_loop_state": ("DIGBY_LOOP_STATE", {"default": None}), # Unused but including this makes it compatible with LoopClose and LoopCloseState
            }
        }
        return inputs

    RETURN_TYPES = tuple(["FLOW_CONTROL", "INT", ])
    RETURN_NAMES = tuple(["loop_close", "iteration_count", ])
    FUNCTION = "loop_open"
    CATEGORY = "DigbyWan/loop"

    def loop_open(self, max_iterations, previous_loop=None, previous_loop_state=None, dynprompt=None, unique_id=None, iteration_count=0, max_iterations_value=0 ):
        this_node = dynprompt.get_node(unique_id)
        this_node['persistent_values'] = { 'max_iterations' : max_iterations }
        return tuple(["stub", iteration_count ])

class DigbyLoopOpenState:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "max_iterations": ("INT", {"default": 5, "min": 1, "max": 100}),
            },
            "optional": {
                "previous_loop": ("DIGBY_LOOP", { "rawLink" : True}),
                "loop_state": ("DIGBY_LOOP_STATE", { "forceInput" : True}),
            },
            "hidden": {
                "dynprompt": "DYNPROMPT",
                "unique_id": "UNIQUE_ID",
                "iteration_count": ("INT", {"default": 0}),
                "previous_loop_state": ("DIGBY_LOOP_STATE", {"default": None})
            }
        }
        return inputs

    RETURN_TYPES = tuple(["FLOW_CONTROL", "INT", "DIGBY_LOOP_STATE", ])
    RETURN_NAMES = tuple(["loop_close", "iteration_count", "loop_state" ])
    FUNCTION = "loop_open"
    CATEGORY = "DigbyWan/loop"

    def loop_open(self, max_iterations, dynprompt=None, previous_loop=None, previous_loop_state=None, loop_state=None, unique_id=None, 
                 iteration_count=0):
                    
        # Output a valid loop_state structure                          
        if (previous_loop_state is None):
            if (loop_state is not None):
                previous_loop_state = loop_state
            else:
                previous_loop_state = { "string_val": None, "int_val": None, "float_val": None, "image": None }

        this_node = dynprompt.get_node(unique_id)
        this_node['persistent_values'] = { 'max_iterations' : max_iterations }

        return tuple(["stub", iteration_count, previous_loop_state ])

class DigbyLoopClose:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "loop_open": ("FLOW_CONTROL", {"rawLink": True}),
                "any_string": ("STRING", {"forceInput":True, "tooltip":"Link to the last node inside the loop.  This defines the node loop to repeat."}),
            },
            "hidden": {
                "dynprompt": "DYNPROMPT",
                "unique_id": "UNIQUE_ID",
                "iteration_count": ("INT", {"default": 0}),
            }
        }
        return inputs

    RETURN_TYPES = ("DIGBY_LOOP", )
    RETURN_NAMES = ("next_loop", )
    FUNCTION = "loop_close"
    CATEGORY = "DigbyWan/loop"
    OUTPUT_NODE  = True

    def loop_close(self, loop_open, any_string,
                 dynprompt=None, unique_id=None, iteration_count=0, ):
        
        loop_open_node = dynprompt.get_node(loop_open[0])
        assert loop_open_node["class_type"] in {"DigbyLoopOpen", "DigbyLoopOpenState"}, "Link to a 'Digby Loop Open' Node"

        max_iterations = loop_open_node["persistent_values"]["max_iterations"] # As assigned in loop open node

        print(f"Iteration {iteration_count} of {max_iterations}")
        
        # 检查是否继续循环  Check whether to continue the loop.
        if iteration_count >= max_iterations - 1:
            print(f"Loop finished with {iteration_count + 1} iterations") 
            return ("loop_link", )

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
        my_clone.set_input("iteration_count", iteration_count + 1)
        
        new_open = graph.lookup_node(open_node)
        new_open.set_input("iteration_count", iteration_count + 1)

        print(f"Continuing to iteration {iteration_count + 1}")

        return {
            "result": tuple([my_clone.out(0),]),
            "expand": graph.finalize(),
        }
    
class DigbyLoopCloseState:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "loop_open": ("FLOW_CONTROL", {"rawLink": True}),
                "loop_state": ("DIGBY_LOOP_STATE", {"forceInput":True, "tooltip":"Link to the last node inside the loop.  This defines the node loop to repeat."}),
            },
            "hidden": {
                "dynprompt": "DYNPROMPT",
                "unique_id": "UNIQUE_ID",
                "iteration_count": ("INT", {"default": 0}),
            }
        }
        return inputs

    RETURN_TYPES = ("DIGBY_LOOP", "DIGBY_LOOP_STATE",)
    RETURN_NAMES = ("next_loop", "state_passthough", )
    FUNCTION = "loop_close"
    CATEGORY = "DigbyWan/loop"
    OUTPUT_NODE  = True

    def loop_close(self, loop_open, loop_state,
                 dynprompt=None, unique_id=None, iteration_count=0, ):
        
        loop_open_node = dynprompt.get_node(loop_open[0])
        assert loop_open_node["class_type"] in {"DigbyLoopOpen", "DigbyLoopOpenState"}, "Link to a 'Digby Loop Open' Node"

        max_iterations = loop_open_node["persistent_values"]["max_iterations"] # As assigned in loop open node

        print(f"Iteration {iteration_count} of {max_iterations}")
        
        # 检查是否继续循环  Check whether to continue the loop.
        if iteration_count >= max_iterations - 1:
            print(f"Loop finished with {iteration_count + 1} iterations") 
            return ("loop_link", loop_state, )

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
        my_clone.set_input("iteration_count", iteration_count + 1)
        
        new_open = graph.lookup_node(open_node)
        new_open.set_input("iteration_count", iteration_count + 1)
        new_open.set_input("loop_state", loop_state)

        print(f"Continuing to iteration {iteration_count + 1}")

        return {
            "result": tuple([my_clone.out(0), my_clone.out(1)]),
            "expand": graph.finalize(),
        }
    
class DigbyLoopStatePack:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "string_val": ("STRING", {"forceInput": True}),
            },
            "optional":{
                "int_val": ("INT",),
                "float_val": ("FLOAT",),
                "image": ("IMAGE",),
            }
        }
        return inputs

    RETURN_TYPES = ("DIGBY_LOOP_STATE", )
    RETURN_NAMES = ("loop_state",)
    FUNCTION = "loop_state_pack"
    CATEGORY = "DigbyWan/loop"
    OUTPUT_NODE = True

    def loop_state_pack(self, string_val, int_val=None, float_val=None, image=None ):
        loop_state = {
            "string_val": string_val,
            "int_val" : int_val,
            "float_val": float_val,
            "image": image,
        }
        return([loop_state])

class DigbyLoopStateUnpack:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "loop_state": ("DIGBY_LOOP_STATE", {"forceInput": True} ),
            }
        }
        return inputs
    RETURN_TYPES = ("STRING", "IMAGE", "INT", "FLOAT", )
    RETURN_NAMES = ("sring_val", "image", "int_val", "float_val", )
    FUNCTION = "loop_state_unpack"
    CATEGORY = "DigbyWan/loop"

    def loop_state_unpack(self, loop_state):
        return([loop_state["string_val"], loop_state["image"], loop_state["int_val"], loop_state["float_val"], ])
    