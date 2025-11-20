from .nodes import Wan22MiddleFrameToVideo, WanVACEVideoSmoother, ImageBatchLoopExtract

NODE_CLASS_MAPPINGS = {
    "WanMiddleFrameToVideo":Wan22MiddleFrameToVideo,
#    "WanSmoothVideoTransition":WanSmoothVideoTransition, # This node is experimental and doesn't produce good output.  Uncomment this line to enable.
    "WanVACEVideoSmoother":WanVACEVideoSmoother,
    "ImageBatchLoopExtract":ImageBatchLoopExtract,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WanMiddleFrameToVideo": "Wan 2.2 Middle Frame To Video",
    "WanSmoothVideoTransition": "Wan 2.2 Smooth Video Transition",
    "WanVACEVideoSmoother": "Wan VACE 2.1 Video Smoother",
    "ImageBatchLoopExtract" : "Image Batch Loop Extractor",
}

WEB_DIRECTORY = "./js"