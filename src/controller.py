#  Copyright (c) Meta Platforms, Inc. and affiliates.
#  All rights reserved.
#  This source code is licensed under the license found in the
#  LICENSE file in the root directory of this source tree.

from source import Source
from functools import reduce

class Controller(Source):
    """
    This class is used to string several different sources in sequence
    """
    class Phase:
        def __init__(self, source, duration):
            """
            The descriptor for each phase of the video

            Parameters:
                source (Source): The media source for this phase
                duration (int): The amount of frames this image should be shown for
            """
            self.source = source
            self.duration = duration

    def __init__(self, phases):
        """
        The constructor for Controller class.

        Parameters:
            phases (list of Phase): A list of all objects that should be connected in sequence and their duration
        """
        self.phases = phases

        self.iterator = iter(self.phases)
        self.current = next(self.iterator)
        self.current_count = 0
        self.current_end = self.current.duration

        self.last_frame = None

        self.frame_count = 0
        self.frame_total = reduce(lambda a, b: a.duration + b.duration, self.phases)

    def next_frame(self):
        if self.frame_count == self.frame_total:
            return self.last_frame

        if self.current_count == self.current.duration:
            self.current = next(self.iterator)
            self.current_count = 0
            self.current_end = self.current.duration
        else:
            self.current_count = self.current_count + 1

        self.frame_count = self.frame_count + 1

        self.last_frame = self.current.source.next_frame()
        return self.last_frame
