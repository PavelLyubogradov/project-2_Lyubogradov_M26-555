"""Decorators for error handling, confirmation and timing, plus a closure cache."""

import time

import prompt

from primitive_db.constants import CONFIRM_YES, TIME_PRECISION


def copy_function_info(wrapper, func) -> None:
    """Copy the original function's name and docstring onto the wrapper.

    Args:
        wrapper: Wrapper function from a decorator.
        func: Original function.
    """
    wrapper.__name__ = func.__name__
    wrapper.__qualname__ = func.__qualname__
    wrapper.__doc__ = func.__doc__
    wrapper.__module__ = func.__module__
    wrapper.__wrapped__ = func


def handle_db_errors(func):
    """Catch database errors and print user-friendly messages.

    Args:
        func: Function to decorate.

    Returns:
        Wrapper that returns None if the function raised an error.
    """

    def wrapper(*args, **kwargs):
        """Call the function and print a message if it raised an error."""
        try:
            return func(*args, **kwargs)
        except FileNotFoundError:
            print(
                "Ошибка: Файл данных не найден. "
                "Возможно, база данных не инициализирована."
            )
        except KeyError as error:
            print(f"Ошибка: Таблица или столбец {error} не найден.")
        except ValueError as error:
            print(f"Ошибка валидации: {error}")
        except Exception as error:
            print(f"Произошла непредвиденная ошибка: {error}")
        return None

    copy_function_info(wrapper, func)
    return wrapper


def confirm_action(action_name: str):
    """Create a decorator that asks for confirmation of a dangerous operation.

    Args:
        action_name: Name of the action shown in the question to the user.

    Returns:
        Decorator that runs the function only after the answer "y".
    """

    def decorator(func):
        """Wrap the function with a confirmation prompt."""

        def wrapper(*args, **kwargs):
            """Run the function only if the user answered "y"."""
            answer = prompt.string(
                f'Вы уверены, что хотите выполнить "{action_name}"? [y/n]: '
            )
            if answer.strip().lower() != CONFIRM_YES:
                print("Операция отменена.")
                return None
            return func(*args, **kwargs)

        copy_function_info(wrapper, func)
        return wrapper

    return decorator


def log_time(func):
    """Measure and print the function's execution time.

    Args:
        func: Function to decorate.

    Returns:
        Wrapper that prints the execution time in seconds.
    """

    def wrapper(*args, **kwargs):
        """Call the function and print its execution time."""
        start = time.monotonic()
        result = func(*args, **kwargs)
        elapsed = time.monotonic() - start
        print(
            f"Функция {func.__name__} выполнилась за "
            f"{elapsed:.{TIME_PRECISION}f} секунд"
        )
        return result

    copy_function_info(wrapper, func)
    return wrapper


def create_cacher():
    """Create a caching function that keeps its cache in a closure.

    Returns:
        Function cache_result(key, value_func) that returns the cached value
        or computes it via value_func and stores it.
    """
    cache = {}

    def cache_result(key, value_func):
        """Return the cached value or compute and store it.

        Args:
            key: Cache key.
            value_func: Zero-argument function that produces the value.

        Returns:
            The cached or freshly computed value.
        """
        if key not in cache:
            cache[key] = value_func()
        return cache[key]

    return cache_result
