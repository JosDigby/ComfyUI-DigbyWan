#
#
# 
# 
# 
# 
# 
from .nodes import Wan22MiddleFrameToVideo, WanVACEVideoSmooth, WanVACEVideoExtend, ImageBatchLoopExtract, ImageBatchSplit, Wan22SmoothVideoTransition
from .loop_nodes import DigbyLoopOpen, DigbyLoopClose, DigbyLoopVariablesInit, DigbyLoopVariables, DigbyLoopStoreImages,  DigbyLoopRetrieveImages
from .moe_ksampler import WanMoeKSampler, WanMoeKSamplerAdvanced, WanMoeKSamplerBasic


NODE_CLASS_MAPPINGS = {
    "Wan22MiddleFrameToVideo":Wan22MiddleFrameToVideo,
#    "Wan22SmoothVideoTransition":Wan22SmoothVideoTransition, # This node is experimental and doesn't produce good output.  Uncomment this line to enable.
    "WanVACEVideoSmooth":WanVACEVideoSmooth,
    "WanVACEVideoExtend":WanVACEVideoExtend,
    "ImageBatchLoopExtract":ImageBatchLoopExtract,
    "ImageBatchSplit":ImageBatchSplit,

    "DigbyLoopOpen": DigbyLoopOpen,
    "DigbyLoopClose": DigbyLoopClose,
    "DigbyLoopVariablesInit": DigbyLoopVariablesInit,
    "DigbyLoopVariables": DigbyLoopVariables,
    "DigbyLoopStoreImages": DigbyLoopStoreImages,
    "DigbyLoopRetrieveImages": DigbyLoopRetrieveImages,

    "WanMoeKSampler": WanMoeKSampler,
#    "WanMoeKSamplerAdvanced": WanMoeKSamplerAdvanced,
    "WanMoeKSamplerBasic": WanMoeKSamplerBasic,

}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Wan22MiddleFrameToVideo": "Wan 2.2 Middle Frame To Video",
    "Wan22SmoothVideoTransition": "Wan 2.2 Smooth Video Transition",
    "WanVACEVideoSmooth": "Wan VACE Video Smooth Transition",
    "WanVACEVideoExtend": "Wan VACE Video Extend",
    "ImageBatchLoopExtract" : "Image Batch Loop Extractor",
    "ImageBatchSplit": "Image Batch Split At",
  
    "DigbyLoopOpen": "Digby Loop Open",
    "DigbyLoopClose": "Digby Loop Close",
    "DigbyLoopVariablesInit": "Digby Loop Variable Initialize",
    "DigbyLoopVariables": "Digby Loop Variables",
    "DigbyLoopStoreImages": "Digby Loop Store Images",
    "DigbyLoopRetrieveImages": "Digby Loop Retrieve Images",

    "WanMoeKSampler": "Wan MoE KSampler",
    "WanMoeKSamplerAdvanced": "Wan MoE KSampler (Advanced)",
    "WanMoeKSamplerBasic": "Wan MoE KSampler (Basic)",
}
