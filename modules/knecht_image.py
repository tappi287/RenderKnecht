import imageio
import numpy as np
from PIL import Image
from pathlib import Path

base_path = Path(r'C:\Users\CADuser\Nextcloud\py\py_knecht\RenderKnecht\_TestDocs\img')

orig_img = base_path / 'input.hdr'
over_img = base_path / 'masked_input.hdr'
mask_img = base_path / 'DG_masked_view.png'
result_img = base_path / 'output.png'


def read_image(image_path: Path):
    """ Read an image using imageio and return as PIL Image object """
    # Read with imageio for format compatibility
    img = imageio.imread(image_path.as_posix())

    # Set type to numpy array
    img = np.array(img)

    if img.dtype != np.uint8:
        # Convert to integer and rescale to 0 - 255
        # original values are float 0.0 - 1.0
        img = np.uint8(img * 255)

    # Return as PIL Image
    return Image.fromarray(img)


def save_image(img: Image.Image, file_path: Path):
    with open(file_path, 'wb') as f:
        img.save(f)


if __name__ == '__main__':
    im = read_image(mask_img)
    save_image(im, result_img)
