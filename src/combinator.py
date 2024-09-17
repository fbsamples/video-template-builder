#  Copyright (c) Meta Platforms, Inc. and affiliates.
#  All rights reserved.
#  This source code is licensed under the license found in the
#  LICENSE file in the root directory of this source tree.

from source import Source


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

        bg_image[j:j+ fg_image.shape[0], i:i+fg_image.shape[1]] = fg_image
        return bg_image

    def next_frame(self):
        bg_image = self.bg_source.next_frame()
        fg_image = self.fg_source.next_frame()
        return self.combine(bg_image, fg_image)
