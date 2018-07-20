import imageio
import numpy as np
from PIL import Image
from pathlib import Path

base_path = Path(r'C:\Users\CADuser\Nextcloud\py\py_knecht\RenderKnecht\_TestDocs\img')

orig_img_path = base_path / 'input.hdr'
over_img_path = base_path / 'masked_input.hdr'
mask_img_path = base_path / 'DG_masked_view.png'
result_img_path = base_path / 'output.png'


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


def composite_image(orig: Path, over: Path, mask: Path):
    orig_image = read_image(orig)
    over_image = read_image(over)
    mask_image = read_image(mask)

    # Convert mask to gray scale image
    mask_image = mask_image.convert('L')

    return Image.composite(orig_image, over_image, mask_image)


def convert_to_black_white_mask(img: Image.Image):
    """
        Convert an RGB image to a black white mask.
        Setting every pixel that is not white(255) to black(0)
    """
    return Image.eval(img, lambda px: 0 if px <= 254 else px)


if __name__ == '__main__':
    im = composite_image(orig_img_path, over_img_path, mask_img_path)
    save_image(im, result_img_path)
