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
    img = cv2.imread(source_path)

    logger.debug(
        "Обработка изображения с выдачей в '%s'", dest_path, extra={"debug_path": debug_path}
    )
    logger.debug("Попытка обрезать навигационную панель")

    img_without_nav_panel = _remove_navigation_bar(
        img,
        threshold=32,
        min_height_ratio=0.05,  # на моей текущей прошивке: 6% (0.06)
        max_height_ratio=0.09,
        dark_ratio_threshold=0.75,
        white_threshold=180,
        min_button_area=290,  # на текущей: ☐:438 ◯:444 ◁:312
        show_debug=False,
    )

    # сохраняем только обрезку нав.панели, чёрный фон далее и так удаляется без проблем
    if debug_path:
        _save_debug_img(img, (0, 0, *img_without_nav_panel.shape[:2]), debug_path)

    cropped = _crop_sreenshot_black_bg(img_without_nav_panel)

    cv2.imwrite(dest_path, cropped)


def _crop_sreenshot_black_bg(
    image: cv2.typing.MatLike, threshold=20, min_area_percentage=0.1
) -> cv2.typing.MatLike:
    """Обрезает изображение, отсекая чёрный фон и части, зависящие от параметров

    Args:
        image (cv2.typing.MatLike): исходное изображение
        threshold (int, optional): пороговое значение однородного цвета.
        min_area_percentage (float, optional): минимальная область (отключено).
        debug_path (str, optional): путь для отладочного изображения
         (не создаётся если None)

    Returns:
        cv2.typing.MatLike: изображение
    """

    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Применить порог
    _, thresholded = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

    # Найти контуры
    contours, hierarchy = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) == 0:
        logger.warning("Не найдены контуры! Обрезка отменена.")
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

    # Bitwise AND the original image with the mask to keep only the white rectangles
    result = cv2.bitwise_and(image, image, mask=mask)

    # Найти ограничивающую рамку
    x, y, w, h = cv2.boundingRect(mask)

    # Обрезать
    cropped_image = result[y : y + h, x : x + w]

    return cropped_image


def _count_navigation_buttons(
    region: np.ndarray, white_threshold: int, min_area: int, show_debug: bool = False
) -> int:
    """Подсчитывает количество светлых элементов (кнопок) в тёмной области.

    Args:
        region (np.ndarray): Область изображения для анализа (BGR)
        white_threshold (int, optional): Порог яркости для определения светлых элементов
        min_area (int, optional): Минимальная площадь элемента (условная, не пиксели)
        show_debug (bool, optional): Показать отладочную информацию

    Returns:
        int: Количество обнаруженных элементов
    """

    # Конвертируем в grayscale
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)

    # Бинаризация: находим светлые области
    _, binary = cv2.threshold(gray, white_threshold, 255, cv2.THRESH_BINARY)

    # Находим контуры
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Фильтруем контуры по площади
    valid_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area >= min_area:
            valid_contours.append(contour)
            if show_debug:
                x, y, w, h = cv2.boundingRect(contour)
                print(f"  Найден элемент: площадь={area:.0f}, размер={w}x{h}px, позиция=({x}, {y})")

    button_count = len(valid_contours)

    if show_debug:
        print(f"  Всего контуров: {len(contours)}, валидных: {button_count}")

    return button_count


def _remove_navigation_bar(
    src_image: cv2.typing.MatLike,
    threshold: int = 32,
    min_height_ratio: float = 0.03,
    max_height_ratio: float = 0.15,
    dark_ratio_threshold: float = 0.75,
    white_threshold: int = 180,
    min_button_area: int = 290,
    show_debug: bool = False,
) -> cv2.typing.MatLike:
    """Обнаруживает и обрезает навигационную панель Android внизу скриншота.

    Args:
        src_image (cv2.typing.MatLike): исходное изображение
        threshold (int, optional): порог яркости для определения тёмного фона (0-255)
        min_height_ratio (float, optional): минимальная высота панели относительно изображения (%/100)
        max_height_ratio (float, optional): максимальная высота анализируемой области (%/100)
        dark_ratio_threshold (float, optional): минимальная доля тёмных пикселей в строке (0-1)
        white_threshold (int, optional): порог яркости для определения светлых элементов (кнопок)
        min_button_area (int, optional): минимальная площадь кнопки (относительная, не понятно в чём)
        show_debug (bool, optional): печатать отладочную информацию

    Returns:
        cv2.typing.MatLike: обрезанное изображение
    """

    # Загружаем изображение
    img = src_image.copy()

    height, width = img.shape[:2]

    # Вычисляем диапазон анализа
    min_bar_height = int(height * min_height_ratio)
    max_bar_height = int(height * max_height_ratio)

    # Берём нижнюю часть изображения для анализа
    bottom_region = img[height - max_bar_height :, :]
    gray_bottom = cv2.cvtColor(bottom_region, cv2.COLOR_BGR2GRAY)

    # Анализируем каждую строку снизу вверх
    is_dark = np.zeros(gray_bottom.shape[0], dtype=bool)

    for i in range(gray_bottom.shape[0]):
        row = gray_bottom[i, :]

        # Подсчитываем процент тёмных пикселей
        dark_pixels = np.sum(row <= threshold)
        dark_ratio = dark_pixels / width

        # Также проверяем среднюю яркость строки
        mean_brightness = np.mean(row)

        # Строка считается тёмной, если выполняется одно из условий:
        # 1. Большинство пикселей тёмные
        # 2. Средняя яркость очень низкая
        is_dark[i] = (dark_ratio >= dark_ratio_threshold) or (mean_brightness <= threshold * 0.8)

    if show_debug:
        print("Анализ строк (снизу вверх):")
        for i in range(len(is_dark) - 1, max(len(is_dark) - 20, -1), -1):
            status = "ТЁМНАЯ" if is_dark[i] else "светлая"
            mean_val = np.mean(gray_bottom[i, :])
            print(f"  Строка {i}: {status} (средняя яркость: {mean_val:.1f})")

    # Ищем непрерывную тёмную область снизу
    # Идём снизу вверх и находим, где заканчивается тёмная область
    crop_at = None
    consecutive_dark = 0

    for i in range(len(is_dark) - 1, -1, -1):
        if is_dark[i]:
            consecutive_dark += 1
        else:
            # Нашли светлую строку
            # Если перед ней была достаточно высокая тёмная область - это наша граница
            if consecutive_dark >= min_bar_height:
                crop_at = i + 1  # Обрезаем после светлой строки
                break
            else:
                # Тёмная область слишком маленькая, сбрасываем счётчик
                consecutive_dark = 0

    # Если вся нижняя область тёмная и достаточно высокая
    if crop_at is None and consecutive_dark >= min_bar_height:
        crop_at = 0

    # Обрезаем изображение
    if crop_at is not None:
        # Конвертируем локальную координату в глобальную
        crop_line = height - max_bar_height + crop_at

        # Дополнительная проверка: убедимся, что обрезаемая область действительно тёмная
        bar_region = gray_bottom[crop_at:, :]
        mean_bar_brightness = np.mean(bar_region)

        if mean_bar_brightness <= threshold * 1.2:
            # Проверка наличия навигационных кнопок
            button_region = bottom_region[crop_at:, :]
            button_count = _count_navigation_buttons(
                button_region, white_threshold, min_button_area, show_debug
            )

            # Ожидаем 3-4 кнопки (или 1 для жест-навигации)
            if button_count in [1, 3, 4]:
                result_img = img[:crop_line, :]
                cropped_pixels = height - crop_line
                print(f"✓ Обнаружена навигационная панель с {button_count} кнопками")
                print(
                    f"  Обрезано: {cropped_pixels} пикселей ({cropped_pixels / height * 100:.1f}%)"
                )
                print(f"  Средняя яркость панели: {mean_bar_brightness:.1f}")
            else:
                result_img = img
                print(
                    f"✗ Панель не обрезана: обнаружено {button_count} элементов (ожидается 1, 3 или 4)"
                )
                print("  Возможно, это текст или другой контент, а не навигационные кнопки")
        else:
            result_img = img
            print(
                f"✗ Панель не обнаружена (область недостаточно тёмная: {mean_bar_brightness:.1f})"
            )
    else:
        result_img = img
        print("✗ Навигационная панель не обнаружена")

    return result_img


def _save_debug_img(source_img: cv2.typing.MatLike, rect: tuple[int, int, int, int], path: str):
    """Сохраняет отладочное изображение с выделенной областью

    Args:
        source_img (cv2.typing.MatLike): исходное изображение (не будет изменено)
        rect (tuple): x, y, h, w - области (в этом порядке!)
        path (str): путь для сохранения изображения
    """
    debug_img = source_img.copy()
    x, y, h, w = rect
    # Отобразить bounding box на изображении
    cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.imwrite(path, debug_img)
