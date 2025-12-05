import math
import nodes
import node_helpers
import torch
import comfy.model_management
import comfy.utils
import comfy.latent_formats
import comfy.clip_vision
import json
import numpy as np
from typing import Tuple
from typing_extensions import override
from comfy_api.latest import ComfyExtension, io

EXPERIMENTAL = True

class Wan22MiddleFrameToVideo:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "vae": ("VAE", ),
                "width": ("INT", {"default": 832, "min": 16, "max": nodes.MAX_RESOLUTION, "step": 16 }),
                "height": ("INT", {"default": 480, "min": 16, "max": nodes.MAX_RESOLUTION, "step": 16 }),
                "length": ("INT", {"default": 81, "min": 1, "max": nodes.MAX_RESOLUTION, "step": 4 }),
                "batch_size": ("INT", {"default": 1, "min": 1, "max":4096 }),
            },
            "optional": {
                "start_image": ("IMAGE",),
                "middle_image": ("IMAGE",),
                "end_image": ("IMAGE",),
                "middle_image_position": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step":0.01, "display":"slider" }),
            }
        }

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT",)
    RETURN_NAMES = ("positive", "negative", "latent",)
    FUNCTION = "build_latent"
    CATEGORY = "DigbyWan"
    DESCRIPTION = "Builds starting latent for WAN model sampling, including First, Middle, and Last frames"

    def build_latent(self, positive, negative, vae, width, height, length, batch_size, start_image=None, middle_image=None, end_image=None, middle_image_position=0.5):
        spacial_scale = vae.spacial_compression_encode()
        latent = torch.zeros([batch_size, vae.latent_channels, ((length - 1) // 4) + 1, height // spacial_scale, width // spacial_scale], device=comfy.model_management.intermediate_device())

        image = torch.ones((length, height, width, 3)) * 0.5
        mask = torch.ones((1, 1, latent.shape[2] * 4, latent.shape[-2], latent.shape[-1]))
        mask_frame_offset = 3

        if start_image is not None:
            start_image = comfy.utils.common_upscale(start_image[:length].movedim(-1, 1), width, height, "bilinear", "center").movedim(1, -1)
            image[:start_image.shape[0]] = start_image
            mask[:, :, :start_image.shape[0] + mask_frame_offset] = 0.0

        if middle_image is not None:
            middle_image = comfy.utils.common_upscale(middle_image[:length].movedim(-1, 1), width, height, "bilinear", "center").movedim(1, -1)
            mid_start_pos = int(((middle_image_position*length)//4) * 4) # Align the middle frame with a 4-frame latent image boundary - seems to produce cleaner images without color flickering
            mid_end_pos = mid_start_pos + middle_image.shape[0] # end position add length of middle_image batch, typically just 1
            image[mid_start_pos:mid_end_pos] = middle_image
            mask[:, :, mid_start_pos+mask_frame_offset:mid_end_pos + mask_frame_offset] = 0

        if end_image is not None:
            end_image = comfy.utils.common_upscale(end_image[-length:].movedim(-1, 1), width, height, "bilinear", "center").movedim(1, -1)
            image[-end_image.shape[0]:] = end_image
            mask[:, :, -end_image.shape[0]:] = 0.0

        concat_latent_image = vae.encode(image[:, :, :, :3])
        mask = mask.view(1, mask.shape[2] // 4, 4, mask.shape[3], mask.shape[4]).transpose(1, 2)
        positive = node_helpers.conditioning_set_values(positive, {"concat_latent_image": concat_latent_image, "concat_mask": mask})
        negative = node_helpers.conditioning_set_values(negative, {"concat_latent_image": concat_latent_image, "concat_mask": mask})

        out_latent = {}
        out_latent["samples"] = latent
        return (positive, negative, out_latent, )

class Wan22SmoothVideoTransition:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "positive": ("CONDITIONING",),
                "negative": ("CONDITIONING",),
                "vae": ("VAE", ),
                "width": ("INT", {"default": 832, "min": 16, "max": nodes.MAX_RESOLUTION, "step": 16 }),
                "height": ("INT", {"default": 480, "min": 16, "max": nodes.MAX_RESOLUTION, "step": 16 }),
                "batch_size": ("INT", {"default": 1, "min": 1, "max":4096 }),
                "video1": ("IMAGE",),          
                "smooth_length": ("INT", {"default":25, "min":9, "max": nodes.MAX_RESOLUTION, "step":8}),
                "transition_center": ("INT", {"default":0, "min":0, "max": nodes.MAX_RESOLUTION, "step":1}),
                "include_transition_frame": ("BOOLEAN", {"default": True}),            
                },
            "optional": {
                "video2": ("IMAGE",),
            }
        }
    
    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT", "IMAGE","MASK")
    RETURN_NAMES = ("positive", "negative", "latent", "images","masks")

    FUNCTION = "build_transition_latent"
    CATEGORY = "DigbyWan"
    DESCRIPTION = "Experimental node: Builds starting latent for WAN model sampling"

    def build_transition_latent(self, positive, negative, vae, width, height, batch_size, video1, smooth_length, transition_center, include_transition_frame, video2=None):
        assert smooth_length % 8 == 1, f"smooth_length-1 must be a multiple of 8"

        video_context = smooth_length // 2
        keep_frames = video_context // 4 
        transition_frames = keep_frames * 3
        mask_frame_offset = 3
        video1 = comfy.utils.common_upscale(video1[:].movedim(-1, 1), width, height, "bilinear", "center").movedim(1, -1)
    
        if (video2 is None):
            assert transition_center - video_context >= 0, f"Transition frame too close to beginning of input video1."
            assert transition_center + video_context < video1.shape[0], f"Transition frame to close to end of input video1."
            video2 = video1[transition_center:]
            video1 = video1[:transition_center]

        else:
            assert video_context < video1.shape[0], f"Input video1 too short.  Need at least {video_context - video1.shape[0]} more frames."
            assert video_context+1 < video2.shape[0], f"Input video2 too short.  Need at least {video_context+1 - video2.shape[0]} more frames."
            video1 = video1[:]
            video2 = comfy.utils.common_upscale(video2[:].movedim(-1, 1), width, height, "bilinear", "center").movedim(1, -1)

        output_images = torch.ones((smooth_length, height, width, 3)) * 0.5
        output_images[:keep_frames] = video1[-video_context:-transition_frames]
        output_images[-keep_frames:] = video2[transition_frames+1:video_context+1]
        if include_transition_frame: output_images[video_context] = video2[0]

        spacial_scale = vae.spacial_compression_encode()
        latent = torch.zeros([batch_size, vae.latent_channels, ((smooth_length - 1) // 4) + 1, height // spacial_scale, width // spacial_scale], device=comfy.model_management.intermediate_device())
        mask = torch.ones((1, 1, latent.shape[2] * 4, latent.shape[-2], latent.shape[-1]))


        mask[:,:,:keep_frames+mask_frame_offset] = 0
        mask[:,:,-keep_frames:] = 0
        if include_transition_frame: mask[:,:,video_context+mask_frame_offset] = 0
     
        concat_latent_image = vae.encode(output_images[:, :, :, :3])
        condition_mask = mask.view(1, mask.shape[2] // 4, 4, mask.shape[3], mask.shape[4]).transpose(1, 2)
        positive = node_helpers.conditioning_set_values(positive, {"concat_latent_image": concat_latent_image, "concat_mask": condition_mask})
        negative = node_helpers.conditioning_set_values(negative, {"concat_latent_image": concat_latent_image, "concat_mask": condition_mask})

        out_latent = {}
        out_latent["samples"] = latent

        return(positive, negative, out_latent, output_images,mask[:,:,mask_frame_offset:])

class WanVACEVideoSmooth:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video1": ("IMAGE",),          
                "smooth_length": ("INT", {"default":37, "min":13, "max": nodes.MAX_RESOLUTION, "step":12}),
                "transition_center": ("INT", {"default":0, "min":0, "max": nodes.MAX_RESOLUTION, "step":1}),
                "include_transition_frame": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "video2": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "IMAGE", "INT", "INT", "INT", "IMAGE", "IMAGE", )
    RETURN_NAMES = ("vace_control_video", "vace_control_masks", "transition_frame", "width", "height", "length", "start_images", "end_images",  )

    FUNCTION = "vace_smoother"
    CATEGORY = "DigbyWan"
    DESCRIPTION = "Build control_video and mask for VACE workflows"

    def vace_smoother(self, video1, smooth_length, transition_center, include_transition_frame, video2=None):
        assert smooth_length % 12 == 1, f"smooth_length-1 must be a multiple of 12"

        video_context = smooth_length // 2
        keep_frames = video_context // 3 
        transition_frames = keep_frames * 2
        
        height = video1[0].shape[0]
        width = video1[0,0].shape[0]

        if (video2 is None):
            assert transition_center - video_context >= 0, f"Transition frame too close to beginning of input video1."
            assert transition_center + video_context < video1.shape[0], f"Transition frame to close to end of input video1."
            video2 = video1[transition_center:]
            video1 = video1[:transition_center]

        else:
            assert video_context < video1.shape[0], f"Input video1 too short.  Need at least {video_context - video1.shape[0]} more frames."
            assert video_context+1 < video2.shape[0], f"Input video2 too short.  Need at least {video_context+1 - video2.shape[0]} more frames."
            video1 = video1[:]
            video2 = comfy.utils.common_upscale(video2[:].movedim(-1, 1), width, height, "bilinear", "center").movedim(1, -1)

        output_images = torch.ones((smooth_length, height, width, 3)) * 0.5
        output_images[:keep_frames] = video1[-video_context:-transition_frames]
        output_images[-keep_frames:] = video2[transition_frames+1:video_context+1]
        if include_transition_frame: output_images[video_context] = video2[0]
        
        mask = torch.ones((output_images.shape[0], height, width))
        mask[:keep_frames] = 0
        mask[-keep_frames:] = 0
        if include_transition_frame: mask[video_context] = 0

        return(output_images, mask, video2[:1], width, height, smooth_length, video1[:-(video_context)], video2[video_context+1:], )
    
class WanVACEVideoBridge:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video1": ("IMAGE",),          
                "video2": ("IMAGE",),
                "total_length": ("INT", {"default":49, "min":5, "max": nodes.MAX_RESOLUTION, "step":4}),
                "frames_from_each_source": ("INT", {"default":8, "min":1, "max": nodes.MAX_RESOLUTION, "step":1}),
            },
            "optional": {
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "INT", "INT", "INT", "IMAGE", "IMAGE", )
    RETURN_NAMES = ("vace_control_video", "vace_control_masks", "width", "height", "length", "start_images", "end_images",  )

    FUNCTION = "vace_bridge"
    CATEGORY = "DigbyWan"
    DESCRIPTION = "Build control_video and mask for VACE workflows"

    def vace_bridge(self, video1, video2, total_length, frames_from_each_source, ):
        height = video1[0].shape[0]
        width = video1[0,0].shape[0]

        assert frames_from_each_source < video1.shape[0], f"Input video1 too short (minimum {frames_from_each_source+1} frames needed)"
        assert frames_from_each_source < video2.shape[0], f"Input video2 too short (minimum {frames_from_each_source+1} frames needed)"
        video1 = video1[:]
        video2 = comfy.utils.common_upscale(video2[:].movedim(-1, 1), width, height, "bilinear", "center").movedim(1, -1)

        output_images = torch.ones((total_length, height, width, 3)) * 0.5
        output_images[:frames_from_each_source] = video1[-frames_from_each_source:]
        output_images[-frames_from_each_source:] = video2[:frames_from_each_source]
        
        mask = torch.ones((output_images.shape[0], height, width))
        mask[:frames_from_each_source] = 0
        mask[-frames_from_each_source:] = 0

        return(output_images, mask, width, height, total_length, video1[:frames_from_each_source], video2[frames_from_each_source:], )
    

class WanVACEVideoExtend:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video": ("IMAGE",),          
                "frames_to_keep": ("INT", {"default":16, "min":1, "max": nodes.MAX_RESOLUTION,}),
                "output_length": ("INT", {"default": 81, "min":5, "max": nodes.MAX_RESOLUTION, "step": 4}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "IMAGE", "INT", "INT", "INT", "IMAGE", )
    RETURN_NAMES = ("vace_control_video", "vace_control_masks", "start_frame", "width", "height", "length", "start_images", )

    FUNCTION = "vace_extend"
    CATEGORY = "DigbyWan"
    DESCRIPTION = "Build control_video and mask for VACE 2.1 workflows"

    def vace_extend(self, video, frames_to_keep, output_length):
        assert frames_to_keep <= video.shape[0], f"frames_to_keep is longer then video output_length"
        assert frames_to_keep <= output_length, f"frames_to_keep is longer than output video output_length"

        height = video[0].shape[0]
        width = video[0,0].shape[0]

        keep_frames = video[-frames_to_keep:]

        output_images = torch.ones((output_length, height, width, 3)) * 0.5
        output_images[:frames_to_keep] = video[-frames_to_keep:]
        
        mask = torch.ones((output_images.shape[0], height, width))
        mask[:frames_to_keep] = 0

        return(output_images, mask, output_images[:1], width, height, output_length, video[:-frames_to_keep], )
    
class ImageBatchLoopExtract:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video_in": ("IMAGE",),          
            },
        }
    
    RETURN_TYPES = ("IMAGE", )
    RETURN_NAMES = ("video_out", )

    FUNCTION = "loop_maker"
    CATEGORY = "DigbyWan"
    DESCRIPTION = "Extract the middle of a 'loop' video"

    def loop_maker(self, video_in,):
        assert video_in.shape[0] % 2 == 0, f"video_in must have an even number of frames"
        
        out_length = video_in.shape[0] // 2
        start_frame = video_in.shape[0] // 4

        return(video_in[start_frame:start_frame+out_length],)
    
class ImageBatchSplit:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),  
                "split_at_frame": ("INT", { "default": -1} )        
            },
        }
    
    RETURN_TYPES = ("IMAGE", "IMAGE", )
    RETURN_NAMES = ("start_images", "end_images" )

    FUNCTION = "split"
    CATEGORY = "DigbyWan"
    DESCRIPTION = "Remove the last image from a batch of images.  Useful for extending videos using last frame"

    def split(self, images,split_at_frame):

        assert abs(split_at_frame < image.shape[0]), f"Invalid split frame {split_frame}"
        start_images = images[:split_at_frame]
        end_images = images[split_at_frame:]
        return(start_images, end_images)
               
 
    
