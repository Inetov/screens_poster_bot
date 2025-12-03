import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)

def create_cropped_image(source_path: str, dest_path: str, debug_path: str | None = None):
    """Создаёт обрезанную картинку и сохраняет её в файл.

    Args:
        source_path (str): путь к исходному изображению
        dest_path (str): путь для сохранения результата
        debug_path (str, optional): путь для отладочного изображения
    """
    img = crop_sreenshot(cv2.imread(source_path), debug_path=debug_path)
    cv2.imwrite(dest_path, img)


# def create_debug_image(source_path: str, dest_path: str):
#     """Создаёт отладочное изображение с исходным и обрезанным вместе,
#     вся обрезанная часть заменяется на фиолетовый фон для наглядности

#     Args:
#         source_path (str): путь к исходному изображению
#         dest_path (str): путь для сохранения результата
#     """
#     img = cv2.imread(source_path)
#     crop = crop_sreenshot(img)
#     vis = combine_images(img, crop)
#     cv2.imwrite(dest_path, vis)


def crop_sreenshot(
    image: cv2.typing.MatLike,
    threshold=10,
    min_area_percentage=0.1,
    crop_bottom_percent=6,
    debug_path: str | None = None,
) -> cv2.typing.MatLike:
    """Обрезает изображение, отсекая чёрный фон и части, зависящие от параметров

    Args:
        image (cv2.typing.MatLike): исходное изображение
        threshold (int, optional): пороговое значение. Опытным путём найдено 10.
        min_area_percentage (float, optional): минимальная область (отключено).
        crop_bottom_percent (int, optional): обрезать процент изображения снизу.
         6 - соответствует кнопкам управления на моей прошивке.
        debug_path (str, optional): путь для отладочного изображения
         (не создаётся если None)

    Returns:
        cv2.typing.MatLike: _description_
    """

    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Применить порог
    _, thresholded = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

    # Найти контуры
    contours, hierarchy = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) == 0:
        logger.warning("Обработка изображения: не найдены контуры! Обрезка отменена.")
        return image

    # # минимальная область для сохранения
    # min_contour_area = min_area_percentage * \
    #     (thresholded.shape[0] * thresholded.shape[1])

    # # контуры, размер которых больше min_contour_area
    # large_contours = [contour for contour in contours if cv2.contourArea(
    #     contour) > min_contour_area]

    # Создать маску
    mask = np.zeros_like(thresholded)
    cv2.drawContours(mask, contours, -1, 255, thickness=cv2.FILLED)

    # Обрезать процент от маски снизу
    if crop_bottom_percent > 0:
        height = mask.shape[0]
        crop_pixels = int(height * (crop_bottom_percent / 100))
        if crop_pixels >= height:
            logger.error(
                "Обработка изображения: предлагается обрезать %s% от изображения. Обрезка отменена.",
                crop_bottom_percent,
            )
            return image

        if crop_pixels > 0:
            mask[-crop_pixels:, :] = 0

    # Bitwise AND the original image with the mask to keep only the white rectangles
    result = cv2.bitwise_and(image, image, mask=mask)

    # Найти ограничивающую рамку
    x, y, w, h = cv2.boundingRect(mask)

    # отладочное изображение
    if debug_path:
        debug_img = image.copy()
        # Отобразить bounding box на изображении
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.imwrite(debug_path, debug_img)

    # Обрезать
    cropped_image = result[y : y + h, x : x + w]

    return cropped_image


def get_mat_with_centred_image(shape, image, bg_color=(128, 0, 128)):
    """Возвращает изображение размером `shape`, фон: `bg_color`,
    в центре которого будет находится `image`"""

    height, width, _ = shape

    new_img = np.zeros((height, width, 3), dtype=np.uint8)
    new_img[:, :] = bg_color

    # Calculate the position to place the smaller image in the center
    x_offset = (width - image.shape[1]) // 2
    y_offset = (height - image.shape[0]) // 2

    # Paste the smaller image onto the purple background
    # fmt: off
    new_img[y_offset : y_offset + image.shape[0],
            x_offset : x_offset + image.shape[1]] = image
    # fmt: on

    return new_img


def combine_images(image1, image2, line_color=(0, 0, 255), line_thickness=5):
    h1, _, _ = image1.shape

    # изображение такого же размера как image1
    # right_image = np.zeros((h1, w1, 3), dtype=np.uint8)
    right_image = get_mat_with_centred_image(image1.shape, image2)

    line = cv2.line(
        np.zeros((h1, line_thickness, 3), dtype=np.uint8),
        (0, 0),
        (0, h1),
        line_color,
        line_thickness,
    )

    combined_image = np.hstack((image1, line, right_image))
    return combined_image


def image_resize(image, width=None, height=None, inter=cv2.INTER_AREA):
    dim = None
    (h, w) = image.shape[:2]

    if width is None and height is None:
        return image

    elif height:
        r = height / float(h)
        dim = (int(w * r), height)

    elif width:
        r = width / float(w)
        dim = (width, int(h * r))

    return cv2.resize(image, dim, interpolation=inter)


def image_show(image, title='arg "title"'):
    if image.shape[0] > 800:
        image = image_resize(image, height=800)
    cv2.imshow(title, image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
