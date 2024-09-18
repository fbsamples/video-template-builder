#  Copyright (c) Meta Platforms, Inc. and affiliates.
#  All rights reserved.
#  This source code is licensed under the license found in the
#  LICENSE file in the root directory of this source tree.

import cv2
import numpy as np
from source import Source, Blending

class MarginCombinator(Source):
    """
    This class handles the combination of two sources (background and product) with specified margins.
    """

    def __init__(self, bg_source, fg_source, margin_top = 0, margin_left = 0):
        """
        The constructor for MarginCombinator class.

        Parameters:
            bg_source (Source): The Source from which the background image is pulled.
            fg_source (Source): The Source from which the product image is pulled.
            margin_top (int): The top margin. Default is 0.
            margin_left (int): The left margin. Default is 0.

        Raises:
            ValueError: If the margin would exceed the size of the background image.
        """
        self.bg_source = bg_source
        self.fg_source = fg_source
        self.margin_top = margin_top
        self.margin_left = margin_left
        self.blending = self.fg_source.blending_strategy()

    def combine(self, bg_image, fg_image):
        """
        Combines the background and product images with the specified margins.

        Parameters:
            bg_img (numpy array): The background image.
            product_img (numpy array): The product image.

        Returns:
            numpy array: The combined image.
        """
        bg_shape = bg_image.shape
        fg_shape = fg_image.shape

        i = self.margin_left
        j = self.margin_top

        if bg_shape[0] < fg_shape[0] + j or bg_shape[1] < fg_shape[1] + i:
            raise ValueError("Margin would exceed the size of the background image.")

        if self.blending == Blending.ALPHA:
            fg_alpha = fg_image[:,:,3]

            bg = bg_image[j:j+ fg_image.shape[0], i:i+fg_image.shape[1]]
            bg = bg.astype(float)

            fg_alpha = fg_alpha.astype(float)/256
            fg = fg_image.astype(float)

            for l in range(3):
                fg[:,:,l] = cv2.multiply(fg_alpha, fg[:,:,l])
                bg[:,:,l] = cv2.multiply(1 - fg_alpha, bg[:,:,l])


            fg = fg.astype('uint8')
            bg = bg.astype('uint8')

            bg_image[j:j+ fg_image.shape[0], i:i+fg_image.shape[1]] = cv2.add(bg, fg)
        elif self.blending == Blending.CHROMA_KEYING:
            hsv = cv2.cvtColor(fg_image, cv2.COLOR_BGR2HSV)
            h,s,v = cv2.split(hsv)

            unique_colors, counts = np.unique(s, return_counts=True)

            chroma_color = None
            most_common = -1
            for a in range(len(unique_colors)):
                if counts[a] > most_common:
                    most_common = counts[a]
                    chroma_color = int(unique_colors[a])

            margin = 10
            mask = cv2.inRange(s, chroma_color - margin, chroma_color + margin)

            kernel = np.ones((3,3), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations = 1)
            mask = cv2.medianBlur(mask, 5)
            mask = cv2.bitwise_not(mask)

            bg_image[j:j+fg_image.shape[0], i:i+fg_image.shape[1]][mask==255] = fg_image[mask==255]
        else:
            bg_image[j:j+ fg_image.shape[0], i:i+fg_image.shape[1]] = fg_image
        return bg_image

    def next_frame(self):
        bg_image = self.bg_source.next_frame().copy()
        fg_image = self.fg_source.next_frame()
        return self.combine(bg_image, fg_image)
