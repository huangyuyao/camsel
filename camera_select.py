import math
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib._color_data as mcd


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
        self.ratio_focal_x = width_px / width_mm
        self.ratio_focal_y = height_px / height_mm

    def diagonal_mm(self):
        return math.sqrt(self.width_mm ** 2 + self.height_mm ** 2)
    #def sensor_format(pixel_size_um, width_px, height_px):
    #    return pixel_size_um * math.sqrt(width_px**2+height_px**2)/16000


class Camera:
    def __init__(self, name, sensor, lens):
        self.name = name
        self.sensor = sensor
        self.lens = lens
        self.unmount()
        self.focus(1e6)

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
        #self.pose = np.array([[1, 0, 0, 0],[0, 1, 0, 0],[0, 0, 1, 0]])
        self.mount(0, 0)

    def mount(self, pitch, height_mm):
        """
        pitch upward is positive in degree
        """
        pitch = pitch / 180 * math.pi
        translate = np.array([[1, 0, 0, 0], [0, 1, 0, height_mm], [0, 0, 1, 0], [0, 0, 0, 1]])
        rotate = np.array([[1, 0, 0, 0], [0, math.cos(pitch), math.sin(pitch), 0], [0, -math.sin(pitch), math.cos(pitch), 0]])
        self.pose = rotate @ translate
        self.pitch = pitch
        def ground_distance_at(angle): return height_mm / math.tan(-angle) if angle < -0.001 else 1e6
        self.center_view_distance = ground_distance_at(pitch)
        self.focus(self.center_view_distance)
        self.near_view_limit = ground_distance_at(pitch - self.vertical_half_aov)
        self.far_view_limit = ground_distance_at(pitch + self.vertical_half_aov)
        return self

    def focus(self, object_distance):
        """ http://www.dofmaster.com/equations.html
        """
        hyperfocal = self.lens.focal_mm ** 2 / self.lens.f_number / self.circle_of_confusion() + self.lens.focal_mm
        self.near_depth = object_distance * (hyperfocal - self.lens.focal_mm) / (hyperfocal + object_distance - 2 * self.lens.focal_mm)
        self.far_depth = object_distance * (hyperfocal - self.lens.focal_mm) / (hyperfocal - object_distance)
        if self.far_depth < 0: self.far_depth = 1e6
        extension = self.lens.focal_mm ** 2 / (object_distance - self.lens.focal_mm)
        image_distance_mm = self.lens.focal_mm + extension
        self.horizontal_half_aov = math.atan(self.sensor.width_mm / 2 / image_distance_mm)
        self.vertical_half_aov = math.atan(self.sensor.height_mm / 2 / image_distance_mm)
        self.object_distance = object_distance
        self.hyperfocal = hyperfocal
        self.extension = extension
        self.K = np.array([[image_distance_mm * self.sensor.ratio_focal_x, 0, self.sensor.width_px / 2 ],
                           [0, image_distance_mm * self.sensor.ratio_focal_y, self.sensor.height_px / 2]])
        return self

    def project(self, point_world):
        assert isinstance(point_world, np.ndarray) and point_world.shape == (4, 1)
        point_camera = self.pose @ point_world
        point_camera = point_camera / point_camera[2, 0]
        point_image = self.K @ point_camera
        return point_image

    def resolution_on_ground_per_10cm(self, ground_distance):
        y = self.project(np.array([[0],[0],[ground_distance],[1]]))[1, 0]
        delta_y = y - self.project(np.array([[0],[0],[ground_distance + 100],[1]]))[1, 0]
        return delta_y

    COLORS = [v.upper() for k, v in mcd.XKCD_COLORS.items()]
    PLOT_COLOR_COUNTER = 0
    LEGENDS = []
    RESOLUTION_THRESHOLD_PX = 1
    def report(self, ax1):
        print("vertical_half_aov", self.vertical_half_aov / math.pi * 180, 'deg')
        print("pitch", self.pitch / math.pi * 180, 'deg')
        print("object_distance", self.object_distance/1000, 'm')
        print("extension", self.extension, 'mm')
        print("near_view_limit", self.near_view_limit/1000, 'm')
        print("far_view_limit", self.far_view_limit/1000, 'm')
        print("near_depth", self.near_depth/1000, 'm')
        print("far_depth", self.far_depth/1000, 'm')
        print("near_pixel_delta_y", self.resolution_on_ground_per_10cm(self.near_view_limit), " px / 10cm")
        print("near_pixel_delta_y", self.resolution_on_ground_per_10cm(self.far_view_limit), " px / 10cm")
        color = self.COLORS[Camera.PLOT_COLOR_COUNTER]
        Camera.PLOT_COLOR_COUNTER = (Camera.PLOT_COLOR_COUNTER + 5) % len(Camera.COLORS)
        ground_distances = np.linspace(1 * 1000, 200 * 1000, num=20000)
        delta_ys = np.vectorize(self.resolution_on_ground_per_10cm)(ground_distances)
        ax1.plot(ground_distances / 1000, delta_ys, color)
        ax1.fill_between(ground_distances / 1000, 1.0 * Camera.RESOLUTION_THRESHOLD_PX, 1.5 * Camera.RESOLUTION_THRESHOLD_PX,
                where=np.logical_and(self.near_view_limit<ground_distances, ground_distances<self.far_view_limit),
                facecolor=color, alpha=0.6)
        ax1.fill_between(ground_distances / 1000, 1.5 * Camera.RESOLUTION_THRESHOLD_PX, 2.0 * Camera.RESOLUTION_THRESHOLD_PX,
                where=np.logical_and(self.near_depth<ground_distances, ground_distances<self.far_depth),
                facecolor=color, alpha=0.6)
        ax1.fill_between(ground_distances / 1000, 1.0 * Camera.RESOLUTION_THRESHOLD_PX, 3.0 * Camera.RESOLUTION_THRESHOLD_PX,
                where=delta_ys<Camera.RESOLUTION_THRESHOLD_PX,
                facecolor='white', alpha=0.6)
        near_distance = max(self.near_view_limit, self.near_depth) /1000
        far_distance = min(self.far_view_limit, self.far_depth, ground_distances[delta_ys>Camera.RESOLUTION_THRESHOLD_PX][-1])/1000
        ax1.scatter(np.array([near_distance, far_distance]), np.array([Camera.RESOLUTION_THRESHOLD_PX, Camera.RESOLUTION_THRESHOLD_PX]), c=color)
        ax1.text(x=near_distance, y=0.95*Camera.RESOLUTION_THRESHOLD_PX, s=('%.2f' % near_distance), fontsize=10,
                horizontalalignment='center', verticalalignment='center', color=color)
        ax1.text(x=far_distance, y=0.95*Camera.RESOLUTION_THRESHOLD_PX, s=('%.2f' % far_distance), fontsize=10,
                horizontalalignment='center', verticalalignment='center', color=color)
        self.near_distance = near_distance
        self.far_distance = far_distance
        Camera.LEGENDS.append(self.name)
        return self

from contextlib import contextmanager

@contextmanager
def prepare_canvas():
    fig1, ax1 = plt.subplots()
    ax1.set_xscale('log')
    ax1.set_xticks([1, 2, 5, 10, 20, 50, 100, 200])
    ax1.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax1.set_ylim(top=3.0*Camera.RESOLUTION_THRESHOLD_PX, bottom=0)
    ax1.set_xlim(left=1, right=200)
    yield ax1
    plt.legend(Camera.LEGENDS)
    ax1.axhline(Camera.RESOLUTION_THRESHOLD_PX, color='red', lw=1, alpha=0.5)
    plt.text(x=205, y=1.125*Camera.RESOLUTION_THRESHOLD_PX, s='view\nrange', fontsize=10, verticalalignment='center')
    plt.text(x=205, y=1.625*Camera.RESOLUTION_THRESHOLD_PX, s='depth\nrange', fontsize=10, verticalalignment='center')
    plt.text(x=205, y=0.95*Camera.RESOLUTION_THRESHOLD_PX, s='resolution\nline', fontsize=9, verticalalignment='center')
    plt.show()


if __name__ == '__main__':
    with prepare_canvas() as ax:
        cam_lamp_near = Camera('cam_lamp_near', Sensor(11.3, 7.1, 1920, 1200), Lens(6, 1.4)).mount(5, 1500).report(ax)
        cam_ground_near = Camera('cam_gnd_near', Sensor(11.3, 7.1, 1920, 1200), Lens(6, 1.4)).mount(-10, 1500).report(ax)
