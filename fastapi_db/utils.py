from enum import Enum
from typing import Any, Union, Type

from sqlalchemy.orm import Query

from .constants import _T
from .types import IPage


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


def _build_columns_query(cls, columns) -> tuple:
    if columns is None:
        return (cls,)
    elif isinstance(columns, tuple):
        return columns
    return (columns,)


def _build_order_by_query(query: Query, order_by) -> Query:
    return query.order_by(*order_by) if isinstance(order_by, tuple) else query.order_by(order_by)


def _build_pagination_query(query: Query, page: IPage) -> Query:
    page_size = min(page.get_page_size(), page.get_page_size_max())
    return query.offset((page.get_page() - 1) * page_size).limit(page_size)