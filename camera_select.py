import math

class Lens:
	def __init__(self):
		
		
class Chip:
	def __init__(self, resolution, pixel_size):
		self.w, self.h = resolution
		self.px, self.py = pixel_size

def sensor_format(pixel_size_um, width_mm, height_mm):
	return pixel_size_um * math.sqrt(width_mm**2+height_mm**2)/16000

if __name__ == '__main__':
	print(sensor_format(5.6, 658, 492))
	