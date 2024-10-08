#  Copyright (c) Meta Platforms, Inc. and affiliates.
#  All rights reserved.
#  This source code is licensed under the license found in the
#  LICENSE file in the root directory of this source tree.

import av
import cv2
import numpy as np
import platform, os
from enum import Enum

class Blending(Enum):
    """
    This class serves as a list of strategies for blending images
    """
    ALPHA=0
    CHROMA_KEYING=1

class Source:
    def blending_strategy(self):
        return self.blending

    def next_frame(self):
        """
        Computes as necessary and returns the next frame in the source.

        Returns:
            np.ndarray: The next frame in the source as an array with shape (height, width, color_channel)
        """
        frame = self._next_frame()
        return cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA) if frame.shape[2] == 3 else frame

    def reset(self, producst):
        pass

    def _next_frame(self):
        pass

    def _known_image_extension(video_path):
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
        return any(video_path.lower().endswith(ext) for ext in valid_extensions)


class SingleMediaSource(Source):
    """
    A class used to represent a single creative asset, with no added modification or effects.
    This class handles both image and video inputs and allows for frame skipping to reach a desired fps for videos.
    It also provides an option to loop the video from the beginning or freeze on the last frame when it ends.
    """

    def __init__(self, video_path, resolution=(720, 720), target_fps=None, on_end_loop=True, blending=None):
        """
        The constructor for SingleMediaSource class.

        Parameters:
            video_path (str): Path to the video or image file.
            resolution (tuple): The desired resolution to which the asset is rescaled. Default is (720, 720).
            target_fps (int): The desired frames per second for video assets. Default is 60.
            on_end_loop (bool): If True, loops the video from the beginning when it ends. If False, freezes on the last frame. Default is True.
            blending (Blending): The strategy for blending this source into the background. Options are: None, ALPHA and CHROMA_KEYING. Default is None.
        """
        super().__init__()
        self.target_fps = target_fps
        if Source._known_image_extension(video_path):
            self.container = None
            self.source_fps = target_fps
            self.target_fpa = target_fps
            self.fps_factor = 1
            self.last_frame = cv2.imread(video_path, cv2.IMREAD_UNCHANGED)
            self.last_frame = cv2.resize(self.last_frame, resolution)
        else:
            self.container = av.open(video_path)
            video_stream = self.container.streams.video[0]

            self.frames = []
            for frame in self.container.decode(video=0):
                if frame.format.name != 'argb':
                    frame = frame.reformat(resolution[0], resolution[1], 'argb')
                    frame = frame.to_ndarray()
                    b,g,r,a = cv2.split(frame)
                    frame = cv2.merge((a,r,g,b))
                else:
                    frame = frame.to_ndarray()
                self.frames.append(frame)
            self.total_frames = video_stream.frames
            self.source_fps =  int(video_stream.average_rate)
            self.target_fps = target_fps
            self.fps_factor = 1 if target_fps is None else int(self.target_fps / self.source_fps)
            self.last_frame = None

        self.resolution = resolution
        self.count = 0
        self.ret = True
        self.on_end_loop = on_end_loop
        self.blending = blending

    def reset(self, products):
        if self.container != None:
            self.count = 0
            self.last_frame = None

    def _next_frame(self):
        """
        Adjusts the frame rate of the video to the desired fps and returns the next frame in the source.
        """

        if self.container:
            if self.count % self.fps_factor != 0:
                self.count += 1
                return self.last_frame

            if self.count >= self.total_frames and self.on_end_loop:
                self.count = 0
                self.last_frame = self.frames[0]
            elif self.count < self.total_frames:
                frame = self.frames[self.count]
                self.last_frame = frame

            self.count += 1
            self.last_frame = cv2.resize(self.last_frame, self.resolution)

        return self.last_frame

class ImageSlideshowSource(Source):

    """
    A class used to produce a left-moving slideshow between images.
    This class handles a list of local image paths and creates slideshow.
    It allows for setting the standby time for each image, the transition time between images, and the target frames per second.
    """

    def __init__(self, img_paths, dimensions=(550, 550), standby_time=3, transition_time=1, target_fps=60, left_bound_white=True, right_bound_white=False, min_time = 15, blending = None, on_end_loop = False):
        """
        The constructor for ImageSlideshowSource class.
        Parameters:
            img_paths (list): List of paths to local image files.
            dimensions (tuple): The desired dimensions to which the images are rescaled. Default is (550, 550).
            standby_time (int): The time each image is fully displayed in seconds. Default is 3.
            transition_time (int): The time for the transition between images in seconds. Default is 1.
            target_fps (int): The desired frames per second for the slideshow. Default is 60.
            left_bound_white (bool): If True, starts the slideshow with a white image. Default is True.
            right_bound_white (bool): If True, ends the slideshow with a white image. Default is False.
            min_time (int): The minimum time for the slideshow in seconds. Default is 15.
            blending (Blending): The strategy for blending the images into the background. Options are NONE, ALPHA and CHROMA_KEYING. Default is NONE.
        """
        super().__init__()
        self.blending = blending
        self.dimensions = dimensions
        self.min_time = min_time
        self.standby_time = standby_time
        self.transition_time = transition_time
        self.on_end_loop = on_end_loop
        self.target_fps = target_fps
        self.count = 0

        self.left_bound_white = left_bound_white
        self.right_bound_white = right_bound_white

        if img_paths == None:
            self.imgs = None
        else:
            self.reset(img_paths)

    def reset(self, products):
        self.imgs = [cv2.imread(path, cv2.IMREAD_UNCHANGED) for path in products]
        self.imgs = [cv2.resize(img, self.dimensions) for img in self.imgs]
        self.imgs = [(cv2.cvtColor(img, cv2.COLOR_BGR2BGRA) if img.shape[2] == 3 else img) for img in self.imgs]

        expected_imgs = 1 + int(self.min_time / (self.standby_time+self.transition_time))
        if not self.on_end_loop:
            expected_imgs = min(len(self.imgs), expected_imgs)

        self.imgs = [self.imgs[i % len(self.imgs)] for i in range(expected_imgs)]
        white_img = np.ones_like(self.imgs[0]) * 255

        if self.left_bound_white:
            self.imgs = [white_img] + self.imgs

        if self.right_bound_white:
            self.imgs = self.imgs + [white_img]

        self.is_transitioning = True
        self.state_count = 0
        self.next_img_idx = 0

    def _left_transition(img1, img2, alpha):
        """
            This function performs a left transition between two images.
            Parameters:
                img1 (numpy array): The first image.
                img2 (numpy array): The second image.
                alpha (float): The transition factor, float between 0 and 1. The higher the value, the more of the second image will be visible.
            Returns:
                numpy array: The resulting image after performing the left transition. Same as input shape of both images.
        """

        if img1.shape != img2.shape:
            raise ValueError("Input images must be of the same shape.")

        cut = int(alpha * img1.shape[1])
        res = np.zeros_like(img1)
        res[:, :img1.shape[1]-cut] = img1[:, cut:]
        res[:, img1.shape[1]-cut:] = img2[:, :cut]
        return res

    def _next_frame(self):
        """
        Returns the next frame in the slideshow.
        This method handles the transitions between images and the standby time for each image.
        """
        if self.imgs == None:
            raise ValueError("No Images Set")

        # Simple state machine to control the transition between images
        if self.is_transitioning and self.state_count == self.transition_time * self.target_fps:
            self.state_count = 0
            self.is_transitioning = False
            self.next_img_idx = min(self.next_img_idx + 1, len(self.imgs) - 1)


        if not self.is_transitioning and self.state_count == self.standby_time * self.target_fps:
            self.state_count = 0
            self.is_transitioning = True


        self.count += 1
        self.state_count += 1

        if self.is_transitioning and self.next_img_idx < len(self.imgs) - 1:
            alpha = self.state_count / (self.transition_time * self.target_fps)
            frame = ImageSlideshowSource._left_transition(self.imgs[self.next_img_idx], self.imgs[self.next_img_idx + 1], alpha)
        else:
            frame = self.imgs[self.next_img_idx]

        return frame
