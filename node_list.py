from .nodes import Wan22MiddleFrameToVideo, WanVACEVideoSmoother, ImageBatchLoopExtract
from .loop_nodes import DigbyLoopOpen, DigbyLoopClose, DigbyLoopStatePack, DigbyLoopStateUnpack, DigbyLoopOpenState, DigbyLoopCloseState

NODE_CLASS_MAPPINGS = {
    "WanMiddleFrameToVideo":Wan22MiddleFrameToVideo,
#    "WanSmoothVideoTransition":WanSmoothVideoTransition, # This node is experimental and doesn't produce good output.  Uncomment this line to enable.
    "WanVACEVideoSmoother":WanVACEVideoSmoother,
    "ImageBatchLoopExtract":ImageBatchLoopExtract,
    "DigbyLoopOpen": DigbyLoopOpen,
    "DigbyLoopClose": DigbyLoopClose,
    "DigbyLoopOpenState": DigbyLoopOpenState,
    "DigbyLoopCloseState": DigbyLoopCloseState,
    "DigbyLoopStatePack": DigbyLoopStatePack,
    "DigbyLoopStateUnpack": DigbyLoopStateUnpack,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WanMiddleFrameToVideo": "Wan 2.2 Middle Frame To Video",
    "WanSmoothVideoTransition": "Wan 2.2 Smooth Video Transition",
    "WanVACEVideoSmoother": "Wan VACE 2.1 Video Smoother",
    "ImageBatchLoopExtract" : "Image Batch Loop Extractor",
  
    "DigbyLoopOpen": "Digby Loop Open",
    "DigbyLoopClose": "Digby Loop Close",
    "DigbyLoopOpenState": "Digby Loop Open w/ State",
    "DigbyLoopCloseState": "Digby Loop Close w/ State",
    "DigbyLoopStatePack": "Digby Loop State Pack",
    "DigbyLoopStateUnpack": "Digby Loop State Unpack",
}
