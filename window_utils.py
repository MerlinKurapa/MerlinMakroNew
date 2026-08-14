import ctypes


def center_position(width, height):
    user32 = ctypes.windll.user32
    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)
    return max(0, (sw - width) // 2), max(0, (sh - height) // 2)
