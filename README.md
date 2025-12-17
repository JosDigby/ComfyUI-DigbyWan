# ComfyUI-DigbyWan

This collection of nodes is intended to provide simplified ways to use various Wan models. **These nodes are a WIP.  Future changes may break things.**

## Node List

| Node Name | Description |
| --- | --- |
| [Wan VACE Video Smooth](#wan-vace-video-smooth) | Prepares VACE control_video to create a smooth transition between two videos, or within a single video at a specific frame.
| [Wan VACE Video Bridge](#wan-vace-video-bridge) | Prepares VACE control_video for generating new video that smoothly extends one video into another.
| [Wan VACE Video Extend](#wan-vace-video-extend) | Prepares VACE control_video for generating new video that continues smoothly from the end of a video.
| [Wan 2.2 Middle Frame To Video](#wan-22-middle-frame-to-video) | Experimental implementation of FMLF2V for Wan 2.2.  Best results when images are very similar in color grade.  
|  |  |
 | [Digby Loop Open](#digby-loop-open--close) | A streamlined loop implementation. |
 | [Digby Loop Close](#digby-loop-open--close) | A stramlined loop implementation. |
 | [Digby Loop Variable Initialize](#digby-loop-variables) | Loop variables for saving state through iterations. |
 | [Digby Loop Variables](#digby-loop-variables) | Loop variables for saving state through iterations. |
 | [Digby Loop Store Images](#digby-loop-store--retrieve-images) | Store images into temporary disk storage in loops. |
 | [Digby Loop Retrieve Images](#digby-loop-store--retrieve-images) | Retrieve stored temporary images from disk. |
 | | |
 | [Digby MoE KSampler (Basic)](#digby-moe-ksampler-basic) | Basic Moe (Mixture of Expert) KSampler with sane defaults for 4 step WAN and proper sigma steps  |
 | [Digby MoE KSampler](#digby-moe-ksampler) | Standard Moe (Mixture of Expert) KSampler with proper sigma steps |
 | | |
<!---
| [Image Batch Loop Extractor](#image-batch-loop-extractor) | Extracts the middle frames of a video.  Use case is for a looping video that has been smoothed with itself.
--->

## Node Descriptions

### Wan VACE Video Smooth

![](docs/media/VACE-smooth.png)

### Wan VACE Video Bridge

### Wan VACE Video Extend

### Wan 2.2 Middle Frame To Video

Image to follow


### Digby Loop Open & Close

### Digby Loop Variables

### Digby Loop Store & Retrieve Images

### Digby Moe KSampler (Basic)

### Digby Moe KSampler 



