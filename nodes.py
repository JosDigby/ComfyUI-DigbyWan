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

class WAN22MiddleFrameToVideo:
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
                "middle_image_position": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step":0.01 }),
                "middle_image_weight": ("FLOAT", {"default":1, "min":0.0, "max":1.0, "step":0.01, "display":"slider"})
            }
        }

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT",)
    RETURN_NAMES = ("positive", "negative", "latent",)
    FUNCTION = "build_latent"
    CATEGORY = "DigbyWan"
    DESCRIPTION = "Builds starting latent for WAN model sampling"

    def build_latent(self, positive, negative, vae, width, height, length, batch_size, start_image=None, middle_image=None, end_image=None, middle_image_position=0.5,middle_image_weight=1.0):
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
            mask[:, :, mid_start_pos+mask_frame_offset:mid_end_pos + mask_frame_offset] = 1.0 - middle_image_weight

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
                "transition_frame": ("INT", {"default":40, "min":1, "max": nodes.MAX_RESOLUTION, }),
                "transition_context": ("INT", {"default":8, "min":4, "max": nodes.MAX_RESOLUTION, "step":4}),
                "transition_rerender": ("INT", {"default":16, "min":4, "max": nodes.MAX_RESOLUTION, "step":4}),
                "source_images": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT", "IMAGE", "MASK", "IMAGE", "INT")
    RETURN_NAMES = ("positive", "negative", "latent", "transition_images", "transition_masks", "first_frame", "length")

    FUNCTION = "build_transition_latent"
    CATEGORY = "DigbyWan"
    DESCRIPTION = "Builds starting latent for WAN model sampling"

    def build_transition_latent(self, positive, negative, vae, width, height, batch_size, transition_frame, transition_context, transition_rerender, source_images):
        transition_half_length = transition_context + transition_rerender;
        total_length = (transition_half_length * 2) + 1
        start_frame = transition_frame - transition_half_length
        end_frame = transition_frame + transition_half_length 
        mask_frame_offset = 3
        
        assert total_length < source_images.shape[0], f"Not enough frames in source_images.  Need lat least {total_length}"
        assert start_frame >= 0, f"transition_frame too low. must be at least {transition_half_length}"
        assert end_frame < source_images.shape[0], f"transition_frame too high.  Must be no more than {source_images.shape[0] - transition_half_length-1}"

        source_images = comfy.utils.common_upscale(source_images[start_frame:end_frame+1].movedim(-1, 1), width, height, "bilinear", "center").movedim(1, -1)
        source_images[transition_context+1:transition_context+transition_rerender] = 0.5
        source_images[-(transition_context+transition_rerender):-transition_context] = 0.5

        spacial_scale = vae.spacial_compression_encode()
        latent = torch.zeros([batch_size, vae.latent_channels, ((total_length - 1) // 4) + 1, height // spacial_scale, width // spacial_scale], device=comfy.model_management.intermediate_device())
        mask = torch.ones((1, 1, latent.shape[2] * 4, latent.shape[-2], latent.shape[-1]))

        mask[:,:,:mask_frame_offset] = 0
        mask[:,:,transition_half_length + mask_frame_offset] = 0
        for m in range(0,transition_context+2):
            blend_factor = min(1.0,m/transition_context)

            source_images[m] = source_images[m] * (1-blend_factor) + (0.5 * blend_factor)
            source_images[-m] = source_images[-m] * (1-blend_factor) + (0.5 * blend_factor)

            mask[:,:,m+mask_frame_offset] = blend_factor
            mask[:,:,-m] = blend_factor

        concat_latent_image = vae.encode(source_images[:, :, :, :3])
        condition_mask = mask.view(1, mask.shape[2] // 4, 4, mask.shape[3], mask.shape[4]).transpose(1, 2)
        positive = node_helpers.conditioning_set_values(positive, {"concat_latent_image": concat_latent_image, "concat_mask": condition_mask})
        negative = node_helpers.conditioning_set_values(negative, {"concat_latent_image": concat_latent_image, "concat_mask": condition_mask})

        out_latent = {}
        out_latent["samples"] = latent

        return(positive, negative, out_latent, source_images, mask, source_images[:1], total_length,)

class WanVACEVideoSmoother:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video1": ("IMAGE",),          
                "transition_size": ("INT", {"default":24, "min":8, "max": nodes.MAX_RESOLUTION, "step":8}),
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
    DESCRIPTION = "Builds starting latent for WAN model sampling"

    def vace_smoother(self, video1, transition_size, transition_center, include_transition_frame, video2=None):
        transition_frames = transition_size // 2 
        keep_frames = transition_frames // 2 
        video_context = transition_frames + keep_frames 
        total_length = (video_context * 2) + 1 
        
        height = video1[0].shape[0]
        width = video1[0,0].shape[0]

        if (video2 is None):
            assert transition_center - video_context >= 0, f"Transition frame too close to beginning of input video1."
            assert transition_center + video_context < video1.shape[0], f"Transition frame to close to end of input video1."
            video2 = video1[transition_center:]
            video1 = video1[:transition_center]

        else:
            assert video_context < video1.shape[0], f"Input video1 too short.  Need at least {video_context} frames."
            assert video_context < video2.shape[0], f"Input video2 too short.  Need at least {video_context+1} frames."
            video1 = video1[:]
            video2 = comfy.utils.common_upscale(video2[:].movedim(-1, 1), width, height, "bilinear", "center").movedim(1, -1)

        output_images = torch.ones((total_length, height, width, 3)) * 0.5
        output_images[:keep_frames] = video1[-video_context:-transition_frames]
        output_images[-keep_frames:] = video2[transition_frames+1:video_context+1]
        if include_transition_frame: output_images[video_context] = video2[0]
        
        mask = torch.ones((output_images.shape[0], height, width))
        mask[:keep_frames] = 0
        mask[-keep_frames:] = 0
        if include_transition_frame: mask[video_context] = 0

        return(output_images, mask, video2[:1], width, height, total_length, video1[:-(video_context)], video2[video_context+1:], )
    
class LoopExtract:
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
    

               
 
    
