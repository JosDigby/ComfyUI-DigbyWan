#
#
# 
# 
# 
# 
# 
from .nodes import Wan22MiddleFrameToVideo, WanVACEVideoSmooth, WanVACEVideoExtend, ImageBatchLoopExtract, ImageBatchSplit, Wan22SmoothVideoTransition, WanVACEVideoBridge
from .loop_nodes import DigbyLoopOpen, DigbyLoopClose, DigbyLoopVariablesInit, DigbyLoopVariables, DigbyLoopStoreImages,  DigbyLoopRetrieveImages
from .moe_ksampler import WanMoeKSampler, WanMoeKSamplerAdvanced, WanMoeKSamplerBasic


NODE_CLASS_MAPPINGS = {
    "DigbyWan22MiddleFrameToVideo":Wan22MiddleFrameToVideo,
#    "DigbyWan22SmoothVideoTransition":Wan22SmoothVideoTransition, # This node is experimental and doesn't produce good output.  Uncomment this line to enable.
    "DigbyWanVACEVideoSmooth":WanVACEVideoSmooth,
    "DigbyWanVACEVideoExtend":WanVACEVideoExtend,
    "DigbyWanVACEVideoBridge":WanVACEVideoBridge,
#    "ImageBatchLoopExtract":ImageBatchLoopExtract,
#    "ImageBatchSplit":ImageBatchSplit,

    "DigbyLoopOpen": DigbyLoopOpen,
    "DigbyLoopClose": DigbyLoopClose,
    "DigbyLoopVariablesInit": DigbyLoopVariablesInit,
    "DigbyLoopVariables": DigbyLoopVariables,
    "DigbyLoopStoreImages": DigbyLoopStoreImages,
    "DigbyLoopRetrieveImages": DigbyLoopRetrieveImages,

    "DigbyWanMoeKSampler": WanMoeKSampler,
#    "DigbyWanMoeKSamplerAdvanced": WanMoeKSamplerAdvanced,
    "DigbyWanMoeKSamplerBasic": WanMoeKSamplerBasic,

}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DigbyWan22MiddleFrameToVideo": "Wan 2.2 Middle Frame To Video",
    "DigbyWan22SmoothVideoTransition": "Wan 2.2 Smooth Video Transition",
    "DigbyWanVACEVideoSmooth": "Wan VACE Video Smooth",
    "DigbyWanVACEVideoExtend": "Wan VACE Video Extend",
    "DigbyWanVACEVideoBridge": "Wan VACE Video Bridge",
#    "ImageBatchLoopExtract" : "Image Batch Loop Extractor",
#    "ImageBatchSplit": "Image Batch Split At",
  
    "DigbyLoopOpen": "Digby Loop Open",
    "DigbyLoopClose": "Digby Loop Close",
    "DigbyLoopVariablesInit": "Digby Loop Variable Initialize",
    "DigbyLoopVariables": "Digby Loop Variables",
    "DigbyLoopStoreImages": "Digby Loop Store Images",
    "DigbyLoopRetrieveImages": "Digby Loop Retrieve Images",

    "DigbyWanMoeKSampler": "Digby MoE KSampler",
#    "DigbyWanMoeKSamplerAdvanced": "Digby MoE KSampler (Advanced)",
    "DigbyWanMoeKSamplerBasic": "Digby MoE KSampler (Basic)",
}
