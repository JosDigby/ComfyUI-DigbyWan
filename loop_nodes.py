from comfy_execution.graph_utils import GraphBuilder, is_link
from nodes import NODE_CLASS_MAPPINGS as ALL_NODE_CLASS_MAPPINGS

# @VariantSupport()
class DigbyLoopOpen:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "max_iterations": ("INT", {"default": 5, "min": 1, "max": 100}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "optional": {
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "iteration_count": ("INT", {"default": 0}),
                "heartbeat_string": ("STRING", )
            }
        }
        return inputs

    RETURN_TYPES = tuple(["FLOW_CONTROL", "INT", ])
    RETURN_NAMES = tuple(["link_to_loop_close", "iteration_count", ])
    FUNCTION = "loop_open"
    CATEGORY = "DigbyWan"

    def loop_open(self, max_iterations, seed=0, unique_id=None, 
                 iteration_count=0, heartbeat_string="DigbyLoopOpen"):
                                
        return tuple(["stub", max_iterations, iteration_count,  ])

# @VariantSupport()
class DigbyLoopClose:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "link_from_loop_open": ("FLOW_CONTROL", {"rawLink": True}),
                "end_of_loop": ("STRING", {"forceInput":True}),
            },
            "hidden": {
                "dynprompt": "DYNPROMPT",
                "unique_id": "UNIQUE_ID",
                "iteration_count": ("INT", {"default": 0}),
            }
        }
        return inputs

    RETURN_TYPES = ("STRING", )
    RETURN_NAMES = ("final_value", )
    FUNCTION = "loop_close"
    CATEGORY = "DigbyWan"

    def explore_dependencies(self, node_id, dynprompt, upstream, parent_ids):
        node_info = dynprompt.get_node(node_id)
        if "inputs" not in node_info:
            return

        for k, v in node_info["inputs"].items():
            if is_link(v):
                parent_id = v[0]
                display_id = dynprompt.get_display_node_id(parent_id)
                display_node = dynprompt.get_node(display_id)
                class_type = display_node["class_type"]
                if class_type not in ['DigbyLoopClose']:
                    parent_ids.append(display_id)
                if parent_id not in upstream:
                    upstream[parent_id] = []
                    self.explore_dependencies(parent_id, dynprompt, upstream, parent_ids)
                upstream[parent_id].append(node_id)

    def explore_output_nodes(self, dynprompt, upstream, output_nodes, parent_ids):
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

    def collect_contained(self, node_id, upstream, contained):
        if node_id not in upstream:
            return
        for child_id in upstream[node_id]:
            if child_id not in contained:
                contained[child_id] = True
                self.collect_contained(child_id, upstream, contained)

    def loop_close(self, link_from_loop_open, end_of_loop,
                 dynprompt=None, unique_id=None, iteration_count=0, ):
        
        loop_open_node = dynprompt.get_node(link_from_loop_open[0])
        assert loop_open_node["class_type"] == "DigbyLoopOpen", "Link to a Loop Open Node"
        max_iterations = loop_open_node["inputs"]["max_iterations"]

        print(f"Iteration {iteration_count} of {max_iterations}")
        
        # 检查是否继续循环  Check whether to continue the loop.
        if iteration_count >= max_iterations - 1:
            print(f"Loop finished with {iteration_count + 1} iterations")
            return ([end_of_loop])

        # 准备下一次循环 Preparing for the next cycle
        this_node = dynprompt.get_node(unique_id)
        upstream = {}
        parent_ids = []
        self.explore_dependencies(unique_id, dynprompt, upstream, parent_ids)
        parent_ids = list(set(parent_ids))

        # 获取并处理输出节点 Get and process the output node
        prompts = dynprompt.get_original_prompt()
        output_nodes = {}
        for id in prompts:
            node = prompts[id]
            if "inputs" not in node:
                continue
            class_type = node["class_type"]
            if class_type in ALL_NODE_CLASS_MAPPINGS:
                class_def = ALL_NODE_CLASS_MAPPINGS[class_type]
                if hasattr(class_def, 'OUTPUT_NODE') and class_def.OUTPUT_NODE == True:
                    for k, v in node['inputs'].items():
                        if is_link(v):
                            output_nodes[id] = v

        # 创建新图 Create a new graph
        graph = GraphBuilder()
        self.explore_output_nodes(dynprompt, upstream, output_nodes, parent_ids)
        
        contained = {}
        open_node = link_from_loop_open[0]
        print(f"flow control node: {dynprompt.get_node(open_node)}")
        self.collect_contained(open_node, upstream, contained)
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
        new_open.set_input("heartbeat_string", str(end_of_loop))

        print(f"Continuing to iteration {iteration_count + 1}")

        return {
            "result": tuple([my_clone.out(0)]),
            "expand": graph.finalize(),
        }
    
