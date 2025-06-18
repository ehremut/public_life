import unittest
import tempfile
from PIL import Image
from threexui.qr_utils import generate_qr

class QRUtilsTests(unittest.TestCase):
    def test_generate_qr_with_logo(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            Image.new("RGB", (20, 20), color="red").save(tmp.name)
            buf = generate_qr("test", logo_path=tmp.name)
            img = Image.open(buf)
            center = img.getpixel((img.width // 2, img.height // 2))
            # logo is red so the red channel should dominate
            self.assertGreaterEqual(center[0], 200)
            half_logo = 10
            border = max(4, (img.width // 4) // 15)
            left_px = img.getpixel((img.width // 2 - half_logo - border, img.height // 2))
            self.assertEqual(left_px, (255, 255, 255, 255))

if __name__ == "__main__":
    unittest.main()
