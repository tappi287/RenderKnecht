import imageio
import numpy as np
from PIL import Image
from pathlib import Path

from modules.knecht_log import init_logging

LOGGER = init_logging(__name__)
base_path = Path(r'C:\Users\CADuser\Nextcloud\py\py_knecht\RenderKnecht\_TestDocs\img')

orig_img_path = base_path / 'input.hdr'
over_img_path = base_path / 'masked_input.hdr'
mask_img_path = base_path / 'DG_masked_view.png'
result_img_path = base_path / 'output.png'


def read_to_pil_image(image_path: Path):
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
    orig_image = read_to_pil_image(orig)
    over_image = read_to_pil_image(over)
    mask_image = read_to_pil_image(mask)

    # Convert mask to gray scale image
    mask_image = mask_image.convert('L')

    return Image.composite(orig_image, over_image, mask_image)


def convert_to_black_white_mask(img: Image.Image):
    """
        Convert an RGB image to a black white mask.
        Setting every pixel that is not white(255) to black(0)
    """
    # Does not work correctly
    return Image.eval(img, lambda px: 0 if px <= 254 else px)


def create_png_images(img_list, contains_render_preset_dir=False, converted_dir_name='non_converted_render_output'):
    return_msg = '\nErstelle PNG Bildaten:\n'

    for img_file_path in img_list:
        # Skip if target is of target format
        if str(img_file_path.suffix).casefold() == '.png':
            continue

        # Read image
        try:
            img_hdr = imageio.imread(str(img_file_path))
        except ValueError or OSError as exception_message:
            # Image may not be completly written yet
            LOGGER.error('Could not open image: %s, %s', img_file_path, exception_message)
            return_msg += '\nBild konnte nicht gelesen werden: '\
                          + img_file_path.name + '\n' + str(exception_message) + '\n'
            # Skip image
            continue

        # Set target png file
        img_png = img_file_path.parent / Path(img_file_path.stem).with_suffix('.png')

        # Convert image file
        try:
            imageio.imwrite(str(img_png), img_hdr)
            return_msg += str(img_png.name) + '\n'
        except Exception as e:
            LOGGER.error('Could not write png image: %s\n%s', img_png, e)
            return_msg += 'Konnte Bild nicht schreiben: ' + str(img_png) + '\n'

        # Move source file to 'converted' directory
        if contains_render_preset_dir:
            new_img_hdr = img_file_path.parent.parent / converted_dir_name / img_file_path.name
        else:
            new_img_hdr = img_file_path.parent / converted_dir_name / img_file_path.name

        # Create converted directory
        if not new_img_hdr.parent.exists():
            new_img_hdr.parent.mkdir()

        # Move the file
        try:
            img_file_path.replace(new_img_hdr)
        except FileNotFoundError or FileExistsError:
            pass

    return return_msg


if __name__ == '__main__':
    im = composite_image(orig_img_path, over_img_path, mask_img_path)
    save_image(im, result_img_path)

