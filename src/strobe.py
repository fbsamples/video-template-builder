#  Copyright (c) Meta Platforms, Inc. and affiliates.
#  All rights reserved.
#  This source code is licensed under the license found in the
#  LICENSE file in the root directory of this source tree.

from source import Blending,Source

import cv2
import numpy as np

class StrobeSource(Source):
    def __init__(self, source, min_scale, start_scale, start_speed, start_direction=-1, centered=True, on_end_loop=True):
        self.source = source
        if self.source.blending_strategy() != Blending.ALPHA and source.blending_strategy() != None:
            print("Strobing requires Alpha Blending")

        self.min_scale = max(0.01, min(min_scale, 1))
        self.scale = start_scale if start_scale >= 0 and start_scale < 1 else 1
        self.speed = max(0.001, min(abs(start_speed), 0.1))
        self.direction = -1 if start_direction < 0 else 1
        self.centered = centered
        self.on_end_loop = on_end_loop
        self.last_frame = None

    def blending_strategy(self):
        return Blending.ALPHA

    def next_frame(self):
        if self.direction == 0:
            return self.last_frame

        if (
                (self.direction == -1 and self.scale == self.min_scale) or
                (self.direction == 1 and self.scale == 1)
            ):
            self.direction = -self.direction if self.on_end_loop else 0

        self.scale = max(self.min_scale, min(self.scale + (self.direction * self.speed), 1))

        frame = self.source.next_frame()
        reduced = cv2.resize(frame, (0,0), fx=self.scale, fy=self.scale)

        margin = (0,0) if not self.centered else ((
                    int((frame.shape[0] - reduced.shape[0])/2),
                    int((frame.shape[1] - reduced.shape[1])/2)
                ))


        frame = np.zeros_like(frame)
        frame[margin[0]:margin[0]+reduced.shape[0],
              margin[1]:margin[1]+reduced.shape[1]] = reduced

        if self.direction == 0:
            self.last_frame = frame

        return frame
