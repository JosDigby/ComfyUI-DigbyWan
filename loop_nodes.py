from comfy_execution.graph_utils import GraphBuilder, is_link
from nodes import NODE_CLASS_MAPPINGS as ALL_NODE_CLASS_MAPPINGS
import torch
import comfy.utils
import comfy.model_management as mem_manager
import gc
import tempfile
import os
import folder_paths
import shutil
import re

from PIL import Image, ImageOps, ImageSequence
import numpy as np


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
                "max_loops": ("INT", {"default": 1, "min":1, "tooltip":"Number of times to repeat the loop."}),
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

    def loop_close(self, max_loops, loop_open, loop_variables,
                 dynprompt=None, unique_id=None, loop_index=0, ):
        
        loop_open_node = dynprompt.get_node(loop_open[0])
        assert loop_open_node["class_type"] in {"DigbyLoopOpen"}, "Must be linked to a 'Digby Loop Open' Node"

        print(f"Completed loop iteration {loop_index+1} of {max_loops}")
        
        # 检查是否继续循环  Check whether to continue the loop.
        if loop_index >= max_loops - 1:
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

        print("Cleaning memory")
        mem_manager.soft_empty_cache()
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
        gc.collect()

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
                "int_val": ("INT",),
                "float_val": ("FLOAT",),
                "seed": ("INT",),
            },
            "optional": {
                "images": ("IMAGE",),
                "latent": ("LATENT",),
            }
        }
        
        return inputs

    RETURN_TYPES = ("DIGBY_LOOP_VARIABLES", "INT", )
    RETURN_NAMES = ("loop_variables","seed",)
    FUNCTION = "loop_variables_init"
    CATEGORY = "DigbyWan/loop"
    OUTPUT_NODE = True

    def loop_variables_init(self, string_val, int_val=None, float_val=None, images=None, latent=None, seed=0 ):
        loop_variables = {
            "string_val": string_val,
            "int_val" : int_val,
            "float_val": float_val,
            "images": images,
            "latent": latent,
            "seed": seed,
            "temp_dir": None,
        }
        return([loop_variables, seed])

class DigbyLoopVariables:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "loop_variables": ("DIGBY_LOOP_VARIABLES", {"forceInput": True} ),
            },
            "optional":{
                "images": ("IMAGE",),
                "latent": ("LATENT",),
                "string_val": ("STRING", {"forceInput": True}),
                "int_val": ("INT",{"forceInput": True}),
                "float_val": ("FLOAT",{"forceInput": True}),
            }
        }
        return inputs

    RETURN_TYPES = ("DIGBY_LOOP_VARIABLES", "IMAGE", "LATENT", "STRING", "INT", "FLOAT", )
    RETURN_NAMES = ("loop_variables", "images", "latent", "string_val", "int_val", "float_val", )
    FUNCTION = "loop_variables_set"
    CATEGORY = "DigbyWan/loop"
    OUTPUT_NODE = True

    def loop_variables_set(self, loop_variables, string_val=None, int_val=None, float_val=None, images=None, latent=None, ):
        if images is not None: loop_variables["images"] = images
        if latent is not None: loop_variables["latent"] = latent
        if string_val is not None: loop_variables["string_val"] = string_val
        if int_val is not None: loop_variables["int_val"] = int_val
        if float_val is not None: loop_variables["float_val"] = float_val
        return([loop_variables, loop_variables["images"], loop_variables["latent"], loop_variables["string_val"], loop_variables["int_val"], loop_variables["float_val"], ])

class DigbyLoopStoreImages:
    def __init__(self):
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "loop_variables": ("DIGBY_LOOP_VARIABLES", {"forceInput": True} ),
                "images": ("IMAGE",),
                "image_set_label": ("STRING", { "default": "set1"} ), 
            }
        }
        return inputs

    RETURN_TYPES = ("DIGBY_LOOP_VARIABLES", "STRING", )
    RETURN_NAMES = ("loop_variables", "output_path", )
    FUNCTION = "loop_variables_store_images"
    CATEGORY = "DigbyWan/loop"
    OUTPUT_NODE = True

    def loop_variables_store_images(self, loop_variables, images, image_set_label, ):
        if loop_variables["temp_dir"] is None:
            loop_variables["temp_dir"] = tempfile.TemporaryDirectory(delete=False).name

        temp_path = loop_variables["temp_dir"]
        filename_prefix = os.path.join(image_set_label, "digby_image")

        # Code cribbed from the SaveImage node of core ComfyUI
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, temp_path, images[0].shape[1], images[0].shape[0])

        results = list()
        for (batch_number, image) in enumerate(images):
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
           
            filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
            file = f"{filename_with_batch_num}_{counter:05}_.png"
            img.save(os.path.join(full_output_folder, file))
            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            })
            counter += 1

        return( loop_variables, full_output_folder,  )

        
class DigbyLoopRetrieveImages:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "loop_variables": ("DIGBY_LOOP_VARIABLES", {"forceInput": True} ),
                "image_set_label": ("STRING", { "default": "set1"} ), 
                "delete_temp_files": ("BOOLEAN", {"default": True}),
            }
        }
        return inputs

    RETURN_TYPES = ("IMAGE", )
    RETURN_NAMES = ("images", )
    FUNCTION = "loop_variables_retrieve_images"
    CATEGORY = "DigbyWan/loop"

# Cribbed from KJNodes Load Images from Folder
    def loop_variables_retrieve_images(self, loop_variables, image_set_label, delete_temp_files):       
        folder_path = os.path.join(loop_variables["temp_dir"], image_set_label)
        if not os.path.isdir(folder_path):
            raise FileNotFoundError(f"Folder '{folder_path}' cannot be found.")
        
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.tga']
        image_paths = []
        for file in os.listdir(folder_path):
            if any(file.lower().endswith(ext) for ext in valid_extensions):
                image_paths.append(os.path.join(folder_path, file))

        dir_files = sorted(image_paths)

        if len(dir_files) == 0:
            raise FileNotFoundError(f"No files in directory '{folder_path}'.")

        images = []
        image_count = 0
        width = -1
        height = -1

        for image_path in dir_files:
            if os.path.isdir(image_path):
                continue
            i = Image.open(image_path)
            i = ImageOps.exif_transpose(i)
            
            # Resize image to maximum dimensions
            if width == -1 and height == -1:
                width = i.size[0]
                height = i.size[1]
            if i.size != (width, height):
                i = i.resize((width, height), resample = Image.LANCZOS) # self.resize_with_aspect_ratio(i, width, height, keep_aspect_ratio)  
            
            image = i.convert("RGB")
            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
                    
            images.append(image)
            image_count += 1

        if delete_temp_files:
            shutil.rmtree(folder_path, ignore_errors=True)

        if len(images) == 1:
            return (images[0],)
        elif len(images) > 1:
            image1 = images[0]
            for image2 in images[1:]:
                image1 = torch.cat((image1, image2), dim=0)
            return (image1,)
        
class DigbyLoopPromptList:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "index": ("INT", {"forceInput": True} ),
                "prompt_list": ("STRING", {"multiline": True, "placeholder":"List of prompts seperated by 'delimiter' specified below.  Default delimiter is a newline '\\n'"}),
                "delimiter": ("STRING", { "default": "", "placeholder": "Uses newline if blank"} ), 
                "merge_consecutive_delimiters": ("BOOLEAN", {"default": True}),          
            }
        }
        return inputs

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt_at_index",)
    FUNCTION = "prompt_string_at_index"
    CATEGORY = "DigbyWan/loop"

    def prompt_string_at_index(self, index, prompt_list, delimiter, merge_consecutive_delimiters, ):
        if (prompt_list is None): 
            return("")

        final_delimiter = delimiter
        final_prompt_list = prompt_list

        if ((delimiter is None) or (delimiter =="")):
            final_delimiter = "\n"

        if (merge_consecutive_delimiters):
            final_prompt_list = re.sub(rf"{final_delimiter}+", final_delimiter, final_prompt_list)   

        split_prompts = final_prompt_list.split(final_delimiter)
        i = min(index, len(split_prompts) - 1)
        return([split_prompts[i]])

class DigbyLoopLastImage:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "images": ("IMAGE", ),
            }
        }
        return inputs
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("last_image",)
    FUNCTION = "get_last_image"
    CATEGORY = "DigbyWan/loop"

    def get_last_image(self, images):
        return([images[-1:]])