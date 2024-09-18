#  Copyright (c) Meta Platforms, Inc. and affiliates.
#  All rights reserved.
#  This source code is licensed under the license found in the
#  LICENSE file in the root directory of this source tree.

import source, cv2
from moviepy.editor import VideoFileClip, AudioFileClip

class Sink():
    """
    A class to create a video from a source and add audio if provided.
    """

    TEMP_FILE = ""

    def __init__(self, source: source.Source, target_fps=60, time=15, output_video_path="sample.mp4", temp_file_path=""):
        """
        Initializes the Sink class with the source, target fps, time, and output video path.
        Args:
            source (source.Source): The source of the frames for the video.
            target_fps (int, optional): The target frames per second for the video. Default is 60.
            time (int, optional): The duration of the video in seconds. Default is 15.
            output_video_path (str, optional): The output path for the video. Default is "./sample.mp4".
        """
        self.source = source
        self.target_fps = target_fps
        self.time = time
        self.output_video_path = output_video_path
        
        Sink.TEMP_FILE = temp_file_path

    def _add_audio(self, audio_path):
        """
        Adds audio to the video using the provided audio path.
        Args:
            audio_path (str): The path to the audio file.
        """

        # Define two clips, one video and one audio
        video_clip = VideoFileClip(Sink.TEMP_FILE)
        audio_clip = AudioFileClip(audio_path)

        # Combine the two clips
        final_clip = video_clip.set_audio(audio_clip)

        # Save
        final_clip.write_videofile(self.output_video_path)

    def create_video(self, audio_path=None):
        """
        Creates a video from the source and adds audio if provided.
        Args:
            audio_path (str, optional): The path to the audio file. If not provided, no audio will be added.
        """

        output_video_path = Sink.TEMP_FILE if audio_path else self.output_video_path

        source = self.source
        target_fps = self.target_fps
        time = self.time

        img = source.next_frame()
        height, width = img.shape[:2]
        
        vw = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*'mp4v'), target_fps, (width, height))

        if not vw.isOpened():
            raise Exception("OpenCV cannot recognize the codec used by the temporary video.")

        for fr in range(time * target_fps):
            vw.write(img)
            img = source.next_frame()

        vw.release()

        if audio_path:
            self._add_audio(audio_path)
