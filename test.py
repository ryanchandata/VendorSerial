from barcode.writer import ImageWriter

try:
    writer = ImageWriter()
    print("ImageWriter created successfully.")
except Exception as e:
    print(f"Error creating ImageWriter: {e}")
