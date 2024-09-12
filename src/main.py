#  Copyright (c) Meta Platforms, Inc. and affiliates.
#  All rights reserved.
#  This source code is licensed under the license found in the
#  LICENSE file in the root directory of this source tree.

from source import *
from combinator import *
from sink import *
from tempfile import gettempdir
import os, requests, shutil

# A simple function to store images from the internet to local files
def download(url, file_name_no_ext):
    response = requests.get(url, stream=True)
    file_ext = response.headers['Content-Type'].split('/')[1]
    if response.status_code == 200:
        file_name = os.path.join(f"{file_name_no_ext}.{file_ext}")
        with open(file_name, 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        return file_name
    del response


# Fetch some generic images from the internet and store them as local files
# on temporary directory.
fb_logo = "https://static.xx.fbcdn.net/rsrc.php/v3/y0/r/eFZD1KABzRA.png"
ig_logo = "https://static.cdninstagram.com/rsrc.php/v3/yM/r/7xwrlYffOBb.png"

image_urls = [fb_logo, ig_logo]
image_paths = []

for i, url in enumerate(image_urls):
    file_name = download(url, os.path.join(gettempdir(), str(i)))
    image_paths.append(file_name)

# Create a new source that will slide through these images
# and will be used to create the video.
slideshow_source = ImageSlideshowSource(
    image_paths,                # List of local image paths
    dimensions=(550, 550),      # Dimensions of the combined images
    standby_time=3,             # Time a full image is shown
    transition_time=1,          # Time it takes to complete transition
    target_fps=60,              # Target frames per second
    left_bound_white=True,      # Start with a white image
    right_bound_white=False,
    min_time = 15               # Loop through images until 15s is reached - TODO: check
)


# Now we will configure a larger WhatsApp logo to be used as background.
wa_logo = "https://static.whatsapp.net/rsrc.php/v3/yP/r/rYZqPCBaG70.png"
wa_image_path = download(wa_logo, os.path.join(gettempdir(), "bg"))

bg_source = SingleMediaSource(
    wa_image_path,
    resolution=(720, 720)
)

# Combine the two of them with a margin combinator to create a new source.
combinator_source = MarginCombinator(
    bg_source = bg_source,
    front_source = slideshow_source,
    margin_top = 60,
    margin_left = 85
)


# Use a sample audio file from Meta's Audio Collection.
audio_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sample-audio.wav')

# If you wish to download an audio file off the internet instead, uncomment the following lines and comment out the one above.
# audio_url = "https://scontent.faep8-2.fna.fbcdn.net/v/t39.12897-6/406204921_873681674389419_4350045728225354598_n.wav/Bling-Reels-Sound-Listicle.wav?_nc_cat=108&ccb=1-7&_nc_sid=c2de2f&_nc_ohc=BYS1Nl_5SSMAb519o5h&_nc_ht=scontent.faep8-2.fna&oh=00_AfCMXJ8LklE5_tjeglEy_ScNQX3sGWw95ac-3n4xU2hjnw&oe=662C6FB6&dl=1"
# audio_path = download(audio_url, os.path.join(gettempdir(), "audio"))

# Create a new video with the source and save it to temporary directory.
sink = Sink(
    source=combinator_source,
    target_fps=60,
    time=20,
    output_video_path="sample.mp4"
)
sink.create_video(audio_path)
