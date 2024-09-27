import csv
from os import listdir
from os.path import exists, isdir, isfile, join
from sys import argv
from combinator import MarginCombinator
from controller import Controller
from source import Blending, Source, SingleMediaSource, ImageSlideshowSource
from sink import Sink
from enum import Enum, StrEnum, IntEnum
from strobe import StrobeSource

fps = 60

class Video:
    class VType(StrEnum):
        OUTPUT = "OUTPUT",
        GRAPHICS = "GRAPHICS",
        SLIDESHOW = "SLIDESHOW"

    class HAlignment(StrEnum):
        LEFT = "LEFT",
        CENTERED = "CENTERED",
        RIGHT = "RIGHT"

    class VAlignment(StrEnum):
        TOP = "TOP",
        CENTERED = "CENTERED",
        BOTTOM = "BOTTOM"

    class Effect(StrEnum):
        ZOOM = "ZOOM"

    class Direction(IntEnum):
        IN = 1,
        OUT = -1

    class Size(float, Enum):
        FULL = 1.0,
        BIG = 0.95,
        MEDIUM = 0.85,
        SMALL = 0.60,
        VERY_SMALL = 0.45
        TINY = 0.30

    class Speed(float, Enum):
        VERY_FAST = 0.0020,
        FAST = 0.0015,
        AVERAGE = 0.0010,
        SLOW = 0.0005,
        VERY_SLOW = 0.0001

    def __init__(self, target_directory):
        self.audio = None
        self.background = None
        self.dimensions = (0,0)

        self.phases = dict()

        self.target_directory = target_directory
        self.template_directory = join(target_directory,'template')
        self.product_directory = join(target_directory,'products')
        self.output_directory = join(target_directory,'output')

        print(f"1. Generating Product List from \"{self.product_directory}\"")
        self.products = self._populateProducts()
        print(f"\tProducts found: {len(self.products)}")

        csv_filename = join(self.target_directory,'template.csv')
        if not exists(csv_filename):
            raise ValueError(f"Template file \"{csv_filename}\" does not exist")

        print(f"2. Parsing Template File: \"{csv_filename}\"")
        with open(csv_filename) as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=',')
            for row in csv_reader:
                self._parseRow(row)

    def create(self):
        base_source = None
        if 0 in self.phases and self.phases[0].source != None:
             base_source = self.phases[0].source

        print("3. Composing Phases")
        controller = Controller()

        # Cycle through phases guaranteeing the order of the sequence
        for i in range(1, len(self.phases)+1):
            phase = self.phases[i]
            source = phase['source'] if base_source == None else MarginCombinator(base_source, phase['source'])
            controller.add_phase(
                    source,
                    phase['duration'] * fps)
            print(f"\tPhase {i}: {phase['duration']}")

        print(f"4. Generating {len(self.products)} Videos")
        i = 1
        for product in self.products:
            print(f"\t{i}/{len(self.products)}: {product}")
            controller.reset(self.products[product])
            sink = Sink(
                    source = controller,
                    target_fps = fps,
                    time = int(controller.duration()/fps),
                    output_video_path=product)
            sink.create_video(self.audio)
            i += 1
        print("5. Done")

    def _parseRow(self, row):
        phase = self._parseInt(row, 'Phase')
        if phase == None:
            print("Empty phase. Skipping row")
            return
        vtype = self._parseType(row)
        source = row['Source']
        dimensions = self._parseXY(row, 'Width', 'Height')

        if vtype == self.VType.OUTPUT:
            self._parseOutput(phase, vtype, source, dimensions)
        else:
            margins = self._parseXY(row, 'H Margin', 'V Margin')
            alignment = self._parseAlignment(row)
            transparency = self._parseTransparency(row['Transparency'])
            duration = self._parseFloat(row, 'Duration', 0)
            loop = self._parseBool(row, 'Loop')

            if vtype == self.VType.GRAPHICS:
                self._parseGraphics(phase, source, dimensions, margins, duration, transparency, alignment, loop, row)
            elif vtype == self.VType.SLIDESHOW:
                self._parseSlideshow(phase, dimensions, margins, duration, transparency, alignment, loop, row)
                pass
            else:
                print(f"Unrecognized type: \"{vtype}\". Skiping")

    def _parseOutput(self, phase, vtype, source, dimensions):
        print(f"Phase {phase}: Parsing Output.")
        if int(phase) != 0:
            raise ValueError(f"Output can only be a part of phase 0. Received {phase}. Skipping")

        print(f"\tAudio Source: \"{self.audio}\".")
        self.audio = join(self.template_directory, source) if len(source) > 0 else None
        print(f"\tVideo Dimensions: {dimensions}.")
        self.dimensions = dimensions

    def _parseGraphics(self, phase, source, dimensions, margins, duration, transparency, alignment, loop, row):
        print(f"Phase {phase}: Added Graphics.")
        print(f"\tTransparency: {transparency}")
        print(f"\tLoop: {loop}")
        file = join(self.template_directory,source)
        if not exists(file):
            raise ValueError(f"File \"{file}\" does not exist")
        print(f"\tGraphics Source: \"{file}\".")

        dimensions = self._calculateDimensions(dimensions)
        source = SingleMediaSource(
                file,
                resolution = dimensions,
                on_end_loop = loop,
                blending = transparency
        )
        source = self._parseAndAddEffect(row, source)
        self._addToPhase(phase, source, dimensions, margins, duration, transparency, alignment, loop)

    def _parseSlideshow(self, phase, dimensions, margins, duration, transparency, alignment, loop, row):
        print(f"Phase {phase}: Added Product Slideshow.")

        dimensions = self._calculateDimensions(dimensions) 
        source = ImageSlideshowSource(None, dimensions, min_time=duration, on_end_loop=loop, blending=transparency)
        source = self._parseAndAddEffect(row, source)
        self._addToPhase(phase, source, dimensions, margins, duration, transparency, alignment, loop)

    def _addToPhase(self, phase, source, dimensions, margins, duration, transparency, alignment, loop):
        print(f"\tDuration (s): {'undetermined' if duration == 0 or duration == None else duration}.")
        print(f"\tDimensions: {dimensions}")
        if not phase in self.phases:
            self.phases[phase] = dict({"source": source, "duration": duration})
        else:
            margins = self._calculateMargins(alignment, margins, dimensions)
            self.phases[phase]["duration"] = max(self.phases[phase]["duration"], duration)

            self.phases[phase]["source"] = MarginCombinator(
                    bg_source = self.phases[phase]["source"],
                    fg_source = source,
                    margin_left = margins[0],
                    margin_top = margins[1]
            )
            print(f"\tMargin: {margins}.")

    def _parseType(self, row):
        return self.VType[row['Type'].upper()]

    def _parseInt(self, row, name, default=None):
        try:
            return int(row[name])
        except:
            return default

    def _parseFloat(self, row, name, default=None):
        try:
            return float(row[name])
        except:
            return default

    def _parseBool(self, row, name, default=None):
        if name not in row or len(row[name]) == 0:
            return default
        return True if row[name].strip().lower() in ("true", "yes") else False

    def _parseXY(self, row, nameX, nameY, default=(0,0)):
        try:
            valX = row[nameX].strip()
            valX = float(valX[:-1].rstrip())/100 if valX.endswith('%') else int(valX)
        except:
            valX = default[0]

        try:
            valY = row[nameY].strip()
            valY = float(valY[:-1].rstrip())/100 if valY.endswith('%') else int(valY)
        except:
            valY = default[1]

        return (valX, valY)

    def _parseAlignment(self, row):
        hvalue = row['H Alignment'].upper()
        hvalue = self.HAlignment[hvalue] if hvalue in self.HAlignment else self.HAlignment.LEFT
        vvalue = row['V Alignment'].upper()
        vvalue = self.VAlignment[vvalue] if vvalue in self.VAlignment else self.VAlignment.TOP
        return (hvalue, vvalue)

    def _parseTransparency(self, transparency):
        if len(transparency) == 0:
            return None
        if transparency == 'Solid':
            return None
        elif transparency == 'Alpha Blending':
            return Blending.ALPHA
        elif transparency == 'Chroma Keying':
            return Blending.CHROMA_KEYING
        else:
            print(f"Unrecognized transparency method: \"{transparency}\". Using Alpha Blending")
            return Blending.ALPHA

    def _parseAndAddEffect(self, row, source):
        effectValue = row['Effect'].lower().strip()
        if len(effectValue) == 0 or effectValue == 'none':
            return source
        elif effectValue == 'zoom':
            direction = self._parseEffectDirection(row)
            min_size = self._parseEffectSize(row, 'Min Size')
            start_size = self._parseEffectSize(row, 'Start Size')
            speed = self._parseEffectSpeed(row, 'Speed')
            #xalignment = self._parseXAlignment(self, )
            loop = self._parseBool(row, 'Effect Loop')
            print(f"\tEffect: Strobe")
            print(f"\t\tDirection: {direction}")
            print(f"\t\tMinimal Size: {min_size}")
            print(f"\t\tStarting Size: {start_size}")
            print(f"\t\tSpeed: {speed}")
            print(f"\t\tLoop: {loop}")

            return StrobeSource(source, min_size, start_size, speed, direction, True, loop)
        else:
            raise ValueError(f"Unknown effect \"{effectValue}\"")

    def _parseEffectDirection(self, row):
        name = 'Direction'
        value = row[name].strip()
        if value.lower() == 'out':
            return self.Direction.OUT
        return self.Direction.IN

    def _parseEffectSize(self, row, name):
        value = row[name].strip().lower()
        if value == 'full':
            return self.Size.FULL
        elif value == 'big':
            return self.Size.BIG
        elif value == 'medium':
            return self.Size.MEDIUM
        elif value == 'small':
            return self.Size.SMALL
        elif value == 'tiny':
            return self.Size.TINY
        raise ValueError("Unknown Size \"{value}\"")

    def _parseEffectSpeed(self, row, name):
        value = row[name].strip().lower()
        if value == 'very fast':
            return self.Speed.VERY_FAST
        if value == 'fast':
            return self.Speed.FAST
        if value == 'average':
            return self.Speed.AVERAGE
        if value == 'slow':
            return self.Speed.SLOW
        if value == 'very slow':
            return self.Speed.VERY_SLOW
        raise ValueError('Unknown Speed \"{value}\"')

    def _calculateDimensions(self, dimensions):
        return (
                dimensions[0] if type(dimensions[0]) == int else int(dimensions[0] * self.dimensions[0]),
                dimensions[1] if type(dimensions[1]) == int else int(dimensions[1] * self.dimensions[1])
        )

    def _calculateMargins(self, alignment, margins, size):
        # Calculate for Horizontal Centered (ignores Margins)
        if alignment[0] == self.HAlignment.CENTERED:
            valX = int((self.dimensions[0] - size[0]) / 2)

        else:
            # Calculate Left Margin for absolute values and percentages
            if type(margins[0]) == int:
                valX = margins[0]
            else:
                valX = int(float(margins[0] * self.dimensions[0]))

            # If it's a right margin, just subtract the margin and size from the total image size
            if alignment[0] == self.HAlignment.RIGHT:
                    valX = self.dimensions[0] - size[0] - valX

        # Calculate for Vertical Centered (ignores Margins)
        if alignment[1] == self.VAlignment.CENTERED:
            valY = int((self.dimensions[1] - size[1]) / 2)
        else:
            # Calculate Top Margin for absolute values and percentages
            if type(margins[1]) == int:
                valY = margins[1]
            else:
                valY = int(float(margins[1] * self.dimensions[1]))

            # If it's a Bottom Margin, just subtract the margin and size from the total image size
            if alignment[1] == self.VAlignment.BOTTOM:
                    valY = self.dimensions[1] - size[1] - valY

        return (valX, valY)

    def _populateProducts(self):
        if not exists(self.product_directory):
            raise ValueError(f"Product directory \"{self.product_directory}\" either does not exist")
        if not isdir(self.product_directory):
           raise ValueError(f"Product directory \"{self.product_directory}\" is not a directory")

        products = dict()
        dirs = listdir(self.product_directory)
        for product in dirs:
            output = join(self.output_directory, product + '.mp4')
            path = join(self.product_directory, product)
            if not isdir(path):
                print(f"\tIgnoring {product}: not a directory")
                continue

            files = listdir(join(self.product_directory,product))
            if len(files) > 0:
                for file in files:
                    f = join(path, file)
                    if file.startswith('.') or not isfile(f):
                        continue
                    if output in products:
                        products[output].append(f)
                    else:
                        products[output] = [f]
        return products


if __name__ == "__main__":
    # Test entry into program
    if len(argv) < 2:
        print(f"Usage: python {argv[0]} <target-directory>")
        exit()

    # Get target directory and validate it
    target_directory = argv[1]
    if not exists(target_directory):
        print(f"Directory \"{target_directory}\" does not exist")
        exit()
    elif not isdir(target_directory):
        print(f"Path \"{target_directory}\" is not a directory")
        exit()

    video = Video(target_directory)
    video.create()

