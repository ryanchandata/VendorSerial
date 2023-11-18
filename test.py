
from barcode import get_barcode_class
from barcode.writer import ImageWriter

barcode_class = get_barcode_class('code128')
barcode_instance = barcode_class('1234567890123', writer=ImageWriter())
print("Barcode Instance: ", barcode_instance)
