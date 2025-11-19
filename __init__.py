from .nodes import Wan22MiddleFrameToVideo, WanVACEVideoSmoother, LoopExtract

NODE_CLASS_MAPPINGS = {
    "WanMiddleFrameToVideo":Wan22MiddleFrameToVideo,
#    "WanSmoothVideoTransition":WanSmoothVideoTransition, # This node is experimental and doesn't produce good output.  Uncomment this line to enable.
    "WanVACEVideoSmoother":WanVACEVideoSmoother,
    "LoopExtract":LoopExtract,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WanMiddleFrameToVideo": "Wan 2.2 Middle Frame To Video",
    "WanSmoothVideoTransition": "Wan 2.2 Smooth Video Transition",
    "WanVACEVideoSmoother": "Wan VACE 2.1 Video Smoother",
    "LoopExtract" : "Loop Extractor",
}

WEB_DIRECTORY = "./js"