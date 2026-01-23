# src/utils/decorators.py

import time
import functools
from typing import Callable, Any
from src.utils.logger import Log 

def measure_time(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        # Log.performance 사용
        Log.performance(f"'{func.__name__}' took {elapsed:.4f} seconds")
        return result
    return wrapper

def log_lifecycle(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        class_name = ""
        if args and hasattr(args[0], '__class__'):
            class_name = f"{args[0].__class__.__name__}."
            
        # Log.trace 사용
        Log.trace(f"Starting: {class_name}{func.__name__}")
        result = func(*args, **kwargs)
        Log.trace(f"Finished: {class_name}{func.__name__}")
        return result
    return wrapper