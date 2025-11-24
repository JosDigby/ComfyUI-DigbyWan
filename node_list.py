from .nodes import Wan22MiddleFrameToVideo, WanVACEVideoSmoother, ImageBatchLoopExtract, ImageBatchLastFrameTrim, Wan22SmoothVideoTransition
from .loop_nodes import DigbyLoopOpen, DigbyLoopClose, DigbyLoopVariablesInit, DigbyLoopVariables

NODE_CLASS_MAPPINGS = {
    "Wan22MiddleFrameToVideo":Wan22MiddleFrameToVideo,
    "Wan22SmoothVideoTransition":Wan22SmoothVideoTransition, # This node is experimental and doesn't produce good output.  Uncomment this line to enable.
    "WanVACEVideoSmoother":WanVACEVideoSmoother,
    "ImageBatchLoopExtract":ImageBatchLoopExtract,
    "ImageBatchLastFrameTrim":ImageBatchLastFrameTrim,

    "DigbyLoopOpen": DigbyLoopOpen,
    "DigbyLoopClose": DigbyLoopClose,
    "DigbyLoopVariablesInit": DigbyLoopVariablesInit,
    "DigbyLoopVariables": DigbyLoopVariables,

}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Wan22MiddleFrameToVideo": "Wan 2.2 Middle Frame To Video",
    "Wan22SmoothVideoTransition": "Wan 2.2 Smooth Video Transition",
    "WanVACEVideoSmoother": "Wan VACE 2.1 Video Smoother",
    "ImageBatchLoopExtract" : "Image Batch Loop Extractor",
    "ImageBatchLastFrameTrim": "Image Batch Last Frame Trim",
  
    "DigbyLoopOpen": "Digby Loop Open",
    "DigbyLoopClose": "Digby Loop Close",
    "DigbyLoopVariablesInit": "Digby Loop Variable Initialize",
    "DigbyLoopVariables": "Digby Loop Variables",
}
