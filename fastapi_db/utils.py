from enum import Enum
from typing import Any, Union, Type

from .constants import _T


def _empty_primary(cls, object: Any) -> bool:
    from .models import DeclarativeModel
    cls: DeclarativeModel

    try:
        if hasattr(object, cls.primary_column().key):
            setattr(object, cls.primary_column().key, None)
        elif cls.primary_column().key in object:
            object[cls.primary_column().key] = None
        return True
    except (KeyError, AttributeError):
        return False


def _deserialize_enum(target: Type[_T], value: Union[Enum, str]):
    if isinstance(value, str):
        return target(value)
    return value