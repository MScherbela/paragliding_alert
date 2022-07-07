WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def remove_short_windows(x, min_window_length):
    y = []
    window_length = 0
    for i, x_ in enumerate(x):
        if x_:
            window_length += 1
        else:
            if window_length >= min_window_length:
                y = y + [True] * window_length
            else:
                y = y + [False] * window_length
            window_length = 0
            y.append(False)
    return y