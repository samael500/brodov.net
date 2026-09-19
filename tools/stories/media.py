"""Public derivatives only; immutable originals stay in the private archive."""
from io import BytesIO
from pathlib import Path
import json
import subprocess
from PIL import Image,ImageOps,ImageCms

def image_derivative(source,dest):
    with Image.open(source) as original:
        im=ImageOps.exif_transpose(original)
        profile=im.info.get('icc_profile')
        if profile:
            im=ImageCms.profileToProfile(im,ImageCms.ImageCmsProfile(BytesIO(profile)),ImageCms.createProfile('sRGB'),outputMode='RGB')
        else:im=im.convert('RGB')
        im.thumbnail((1600,1600),Image.Resampling.LANCZOS)
        im.save(dest,'JPEG',quality=92,icc_profile=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes())
        return im.size

def video_derivative(source,dest,poster):
    # Always make a known web-compatible, metadata-free H.264/AAC derivative.
    subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(source),'-map','0:v:0','-map','0:a?',
                    '-map_metadata','-1','-vf',"scale=w='min(1600,iw)':h='min(1600,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
                    '-c:v','libx264','-crf','23','-preset','medium','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',str(dest)],check=True)
    subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(dest),'-frames:v','1','-update','1',str(poster)],check=True)
    return probe(dest)

def probe(path):
    r=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,duration','-of','json',str(path)],capture_output=True,text=True,check=True)
    return json.loads(r.stdout)['streams'][0]
