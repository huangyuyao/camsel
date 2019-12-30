import math
import numpy as np

class Lens:
    def __init__(self, focal_mm, f_number):
        self.focal_mm = focal_mm
        self.f_number = f_number

    def working_diameter(self):
        return self.focal_mm / self.f_number
        
        

class Sensor:
    def __init__(self, width_mm, height_mm, width_px, height_px):
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.width_px = width_px
        self.height_px = height_px

    def diagonal_mm(self):
        return math.sqrt(self.width_mm ** 2 + self.height_mm ** 2)
    #def sensor_format(pixel_size_um, width_px, height_px):
    #    return pixel_size_um * math.sqrt(width_px**2+height_px**2)/16000

class Camera:
    def __init__(self, sensor, lens):
        self.sensor = sensor
        self.lens = lens
        self.unmount()

    def equivalent_focal_mm(self):
        """ https://en.wikipedia.org/wiki/35_mm_equivalent_focal_length
        According to CIPA guidelines,[2] 35 mm equivalent focal length is to be calculated like this: "Converted focal length into 35mm camera" = (Diagonal distance of image area in the 35mm camera (43.27mm) / Diagonal distance of image area on the image sensor of the DSC) × focal length of the lens of the DSC.  
        """
        return self.lens.focal_mm / self.sensor.diagonal_mm() * 43.27
    
    def circle_of_confusion(self, coc_35mm = 0.030):
        """ http://www.dofmaster.com/digital_coc.html#coccalculator
        The circles of confusion above were calculated using the formula:
            CoC = (CoC for 35mm format) / (Digital camera lens focal length multiplier)
        The focal length multiplier for a camera is specified by the manufacturer, or is calculated using the formula:
            Multiplier = (35mm equivalent lens focal length) / (Actual lens focal length)
        """
        mult = self.equivalent_focal_mm() / self.lens.focal_mm
        coc = coc_35mm / mult
        return coc

    def unmount(self):
        self.pose = np.array([[1, 0, 0, 0],[0, 1, 0, 0],[0, 0, 1, 0]])

    def mount(self, pitch, height_mm):
        """
        pitch upward is positive in degree
        """
        pitch = pitch / 180 * math.pi
        translate = np.array([[1, 0, 0, 0],[0, 1, 0, height_mm],[0, 0, 1, 0], [0, 0, 0, 1]])
        rotate = np.array([[1, 0, 0, 0],[0, math.cos(pitch), math.sin(pitch), 0],[0, -math.sin(pitch), math.cos(pitch), 0]])
        self.pose = rotate @ translate
        self.pitch = pitch
        def ground_distance_at(angle): return height_mm / math.tan(-angle) if angle < -0.001 else 1e6
        self.center_view_distance = ground_distance_at(pitch)
        self.focus(self.center_view_distance)
        self.near_view_limit = ground_distance_at(pitch - self.vertical_half_aov)
        self.far_view_limit = ground_distance_at(pitch + self.vertical_half_aov)

    def focus(self, object_distance):
        """ http://www.dofmaster.com/equations.html
        """
        hyperfocal = self.lens.focal_mm ** 2 / self.lens.f_number / self.circle_of_confusion() + self.lens.focal_mm
        self.near_depth = object_distance * (hyperfocal - self.lens.focal_mm) / (hyperfocal + object_distance - 2 * self.lens.focal_mm)
        self.far_depth = object_distance * (hyperfocal - self.lens.focal_mm) / (hyperfocal - object_distance)
        extension = self.lens.focal_mm ** 2 / (object_distance - self.lens.focal_mm)
        image_distance_mm = self.lens.focal_mm + extension
        self.horizontal_half_aov = math.atan(self.sensor.width_mm / 2 / image_distance_mm)
        self.vertical_half_aov = math.atan(self.sensor.height_mm / 2 / image_distance_mm)
        self.object_distance = object_distance
        self.hyperfocal = hyperfocal
        self.extension = extension

    def report(self):
        print("vertical_half_aov", self.vertical_half_aov / math.pi * 180, 'deg')
        print("pitch", self.pitch / math.pi * 180, 'deg')
        print("object_distance", self.object_distance/1000, 'm')
        print("extension", self.extension, 'mm')
        print("near_view_limit", self.near_view_limit/1000, 'm')
        print("far_view_limit", self.far_view_limit/1000, 'm')
        print("near_depth", self.near_depth/1000, 'm')
        print("far_depth", self.far_depth/1000, 'm')
    
if __name__ == '__main__':
    camera = Camera(Sensor(11.3, 7.1, 1920, 1200), Lens(25, 1.8))
    camera.mount(-35, 1500)
    camera.report()
    # todo: estimate camera matrix and the meter per pixel value of the ground surface
