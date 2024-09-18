#  Copyright (c) Meta Platforms, Inc. and affiliates.
#  All rights reserved.
#  This source code is licensed under the license found in the
#  LICENSE file in the root directory of this source tree.

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
            self.cap = None
            self.source_fps = target_fps
            self.target_fpa = target_fps
            self.fps_factor = 1
            self.last_frame = cv2.imread(video_path, cv2.IMREAD_UNCHANGED)
            self.last_frame = cv2.resize(self.last_frame, resolution)
        else:
            self.cap = cv2.VideoCapture(video_path)
            self.source_fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.target_fps = target_fps
            self.fps_factor = 1 if target_fps is None else int(self.target_fps / self.source_fps)
            self.last_frame = None

        self.resolution = resolution
        self.count = 0
        self.ret = True
        self.on_end_loop = on_end_loop
        self.blending = blending

    def _next_frame(self):
        """
        Adjusts the frame rate of the video to the desired fps and returns the next frame in the source.
        """

        if self.cap:
            if self.count % self.fps_factor != 0:
                self.count += 1
                return self.last_frame

            ret, frame = self.cap.read()

            if ret:
                self.last_frame = frame
            elif self.cap.get(cv2.CAP_PROP_FRAME_COUNT) > 1 and self.on_end_loop:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                _, self.last_frame = self.cap.read()

            self.count += 1
            self.last_frame = cv2.resize(self.last_frame, self.resolution)

        return self.last_frame

class ImageSlideshowSource(Source):

    """
    A class used to produce a left-moving slideshow between images.
    This class handles a list of local image paths and creates slideshow.
    It allows for setting the standby time for each image, the transition time between images, and the target frames per second.
    """

    def __init__(self, img_paths, dimensions=(550, 550), standby_time=3, transition_time=1, target_fps=60, left_bound_white=True, right_bound_white=False, min_time = 15, blending = None):
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
        self.imgs = [cv2.imread(path, cv2.IMREAD_UNCHANGED) for path in img_paths]
        self.imgs = [cv2.resize(img, dimensions) for img in self.imgs]

        expected_imgs = 1 + int(min_time / (standby_time+transition_time))

        self.imgs = [self.imgs[i % len(self.imgs)] for i in range(expected_imgs)]

        self.blending = blending
        self.standby_time = standby_time
        self.transition_time = transition_time
        self.target_fps = target_fps
        self.count = 0
        self.next_img_idx = 0

        white_img = np.ones_like(self.imgs[0]) * 255

        if left_bound_white:
            self.imgs = [white_img] + self.imgs

        if right_bound_white:
            self.imgs = self.imgs + [white_img]

        self.is_transitioning = True
        self.state_count = 0


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
