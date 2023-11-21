import board
import neopixel

# neopixel setup
pixel_pin = board.D18
num_pixels = 5
ORDER = neopixel.GRB
pixels = neopixel.NeoPixel(
    pixel_pin, num_pixels, brightness=0.5, auto_write=False, pixel_order=ORDER
)

# turn neopixel on
def leds_on():
    pixels.fill((255, 255, 255))
    pixels.show()
    return 'Lights are turned on!'

# turn neopixel off
def leds_off():
    pixels.fill((0,0,0))
    pixels.show()
    return 'Lights have been turned off!'
