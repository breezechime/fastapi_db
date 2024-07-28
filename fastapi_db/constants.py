from typing import TypeVar, Optional, Union, Tuple

from sqlalchemy.orm import InstrumentedAttribute

_T = TypeVar('_T')

ID = Optional[Union[int, str]]

_SESSION_MISSING_MESSAGE = '未找到上下文Session对象，请检查是否正确添加中间件，如非API获取Session请手动或在函数添加装饰器'

Columns = Optional[Union[Tuple[InstrumentedAttribute, ...], InstrumentedAttribute]]