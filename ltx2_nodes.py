import math
import nodes
import node_helpers
import torch
import comfy.model_management
import comfy.utils
import comfy.latent_formats

EXPERIMENTAL = True

class LTX2_AVLatent:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video_vae": ("VAE", ),
                "audio_vae": ("VAE", ),
                "frames": ("INT", {"default": 121, "min": 1, "step": 8}),
                "long_dimension": ("INT", {"default":1280, "step": 4}),
                "orientation": ("COMBO", {"default" : "landscape", "options":["landscape","portrait"],})
            },
            "optional": {
                "start_image": ("IMAGE",),
                "audio": ("AUDIO",),
                "use_audio_length": ("BOOLEAN", {"default":False} ),
            }
        }

    RETURN_TYPES = ("LATENT", "LATENT", "LATENT", "INT", "INT", "INT",)
    RETURN_NAMES = ("ltx_av_latent", "video_latent", "audio_latent", "frame_count", "width", "height",)
    FUNCTION = "build_latent"
    CATEGORY = "DigbyWan"
    DESCRIPTION = "Create latent for LTX-2"

    def build_latent(self, video_vae, audio_vae, frames, long_dimension, orientation, start_image=None, audio=None, use_audio_length=False):
        # Variable calculations
        batch_size = 1
        frame_count = frames
        frame_rate = 25

        # Audio Section
        if ((audio is not None) and (use_audio_length)):
            waveform = audio["waveform"]
            sample_rate = audio["sample_rate"]
            audio_length = waveform.shape[-1]
            audio_frames = int(((frame_rate * audio_length / sample_rate) // 8) * 8) + 1
            frame_count = min(frame_count, audio_frames)

            print(f"audio_length = {audio_length} and sample_rate = {sample_rate} =>  audio_frames of {audio_frames}")

        if (audio is not None):
            audio_samples = audio_vae.encode(audio)
            audio_mask = torch.zeros((batch_size, 1, audio_samples.shape[2], 1, 1))
        else:
            z_channels = audio_vae.latent_channels
            audio_freq = audio_vae.latent_frequency_bins
            num_audio_latents = audio_vae.num_of_latents_from_frames(frame_count, frame_rate)

            audio_samples = torch.zeros(
                (batch_size, z_channels, num_audio_latents, audio_freq),
                device=comfy.model_management.intermediate_device(),
            )
            audio_mask = torch.ones((batch_size, 1, audio_samples.shape[2], 1, 1))

        audio_latents = {
            "samples": audio_samples,
            "sample_rate": int(audio_vae.sample_rate),
            "type": "audio",
            "noise_mask": audio_mask,
            }

        # Video Section

        # Image size setup
        if (start_image is not None):
            length, img_height, img_width, channels = start_image.shape
        else:
            img_width = 1280
            img_height = 720
            channels = 3
            if (orientation == "portrait"):
                img_width = 720
                img_height = 1280
                  
        if (img_width > img_height):
            scale_factor = long_dimension / img_width 
        else:
            scale_factor = long_dimension / img_height 

        width = int((img_width * scale_factor) // 4) * 4
        height = int((img_height * scale_factor) // 4) * 4
        # mask is of the form [batch, channel, latent count, height, width]
        # I am following the Comfy implementation which is just [B,1,Latents,1,1]
        # I assume the image sizes and channel counts don't really matter - which has been my observation
        # Trying to do masking
        video_mask = torch.ones((batch_size, 1, frame_count//4 + 1, 1,1))
                          
        
        print(f"creating base images at {width} w and {height} h with a scale_factor of {scale_factor}")                          
        base_images = torch.ones((frame_count,height,width,channels)) * 0.5 # Setting the initial image value.  
        if (start_image is not None):
            length, img_height, img_width, channels = start_image.shape
            start_image = comfy.utils.common_upscale(start_image[:length].movedim(-1, 1), width, height, "bilinear", "center").movedim(1, -1)
            base_images[:length,:,:] = start_image[:,:,:]
            latent_length = (length // 4) + 1
            video_mask[:,:,:latent_length] = 0

        video_samples = video_vae.encode(base_images[:, :, :, :3])

        out_video = {}
        out_video["samples"] = video_samples
        out_video["noise_mask"] = video_mask

        out_audio = {}
        out_audio["samples"] = audio_samples
        out_audio["noise_mask"] = audio_mask

        out_av = {}
        out_av["noise_mask"] = comfy.nested_tensor.NestedTensor((video_mask, audio_mask))
        out_av["samples"] = comfy.nested_tensor.NestedTensor((video_samples, audio_samples))

        return(out_av, out_video, out_audio, frame_count, width, height,)


            



