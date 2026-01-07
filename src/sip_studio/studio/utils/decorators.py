"""Decorators for bridge services."""

import functools
import inspect

from .bridge_types import bridge_error


def require_brand(param_name: str = "brand_slug"):
    """Decorator: resolve brand slug or return error if none available.
    Respects explicit parameter if passed. Falls back to active brand.
    Works with both sync and async methods.
    Validates param_name exists in method signature at decoration time.
    """

    def decorator(method):
        # Unwrap for consistent async detection and signature binding
        unwrapped = inspect.unwrap(method)
        is_async = inspect.iscoroutinefunction(unwrapped)
        sig = inspect.signature(unwrapped)
        # Validate param_name at decoration time
        params = sig.parameters
        has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
        if param_name not in params and not has_var_kw:
            raise TypeError(
                f"@require_brand: method {method.__name__} has no '{param_name}' parameter"
            )
        # Find VAR_KEYWORD param name if exists
        var_kw_name = next(
            (n for n, p in params.items() if p.kind == inspect.Parameter.VAR_KEYWORD), None
        )

        @functools.wraps(method)
        def sync_wrapper(self, *args, **kwargs):
            bound = sig.bind_partial(self, *args, **kwargs)
            bound.apply_defaults()
            # Check if param_name is in bound.arguments directly or in VAR_KEYWORD dict
            slug = bound.arguments.get(param_name)
            if slug is None and var_kw_name and var_kw_name in bound.arguments:
                slug = bound.arguments[var_kw_name].get(param_name)
            if not slug:
                slug = self._state.get_active_slug()
                if not slug:
                    return bridge_error("No brand selected")
                # Set in VAR_KEYWORD dict if param not in signature, else in arguments
                if param_name not in params and var_kw_name:
                    if var_kw_name not in bound.arguments:
                        bound.arguments[var_kw_name] = {}
                    bound.arguments[var_kw_name][param_name] = slug
                else:
                    bound.arguments[param_name] = slug
            # Use bound.args/kwargs to avoid "multiple values" error when None passed positionally
            return method(*bound.args, **bound.kwargs)

        @functools.wraps(method)
        async def async_wrapper(self, *args, **kwargs):
            bound = sig.bind_partial(self, *args, **kwargs)
            bound.apply_defaults()
            # Check if param_name is in bound.arguments directly or in VAR_KEYWORD dict
            slug = bound.arguments.get(param_name)
            if slug is None and var_kw_name and var_kw_name in bound.arguments:
                slug = bound.arguments[var_kw_name].get(param_name)
            if not slug:
                slug = self._state.get_active_slug()
                if not slug:
                    return bridge_error("No brand selected")
                # Set in VAR_KEYWORD dict if param not in signature, else in arguments
                if param_name not in params and var_kw_name:
                    if var_kw_name not in bound.arguments:
                        bound.arguments[var_kw_name] = {}
                    bound.arguments[var_kw_name][param_name] = slug
                else:
                    bound.arguments[param_name] = slug
            # Use bound.args/kwargs to avoid "multiple values" error when None passed positionally
            return await method(*bound.args, **bound.kwargs)

        return async_wrapper if is_async else sync_wrapper

    return decorator
