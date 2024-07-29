from typing import Type, Union, Dict, List, Optional, Any, Tuple, TypeVar
from sqlalchemy.orm import Session, declarative_base, Query, InstrumentedAttribute, make_transient
from .constants import ID, Columns
from .extensions import ctx
from .types import IPage
from .utils import _empty_primary, _build_order_by_query, _build_columns_query, _build_pagination_query

_Base = declarative_base()
_T = TypeVar("_T", bound='DeclarativeModel')


class DeclarativeModel(_Base):
    """基础模型类，提供了查询和会话的封装"""
    __abstract__ = True

    @classmethod
    def query(cls: Type[_T], *columns):
        """查询构造器"""
        query = cls.session().query(*columns if columns else (cls,))  # type: Query[Type[_T]]
        return query

    @classmethod
    def session(cls) -> Session:
        """获取会话"""
        return ctx.session

    @classmethod
    def columns(cls) -> Dict[str, InstrumentedAttribute]:
        """获取模型列"""
        return cls.__table__.columns if getattr(cls, '__table__', None) is not None else []  # type: ignore

    @classmethod
    def column_list(cls) -> List[InstrumentedAttribute]:
        """获取模型字段列表"""
        return list(cls.columns().values())

    @classmethod
    def primary_column(cls) -> Union[InstrumentedAttribute[Union[ID]], ID, Any]:
        """主键列"""
        if hasattr(cls, 'id') and cls.id.primary_key:
            return cls.id
        primary_column: Optional[InstrumentedAttribute[Union[int, str]]] = None
        for column in cls.column_list():
            if column.primary_key:
                primary_column = column
                break
        if primary_column is None:
            raise RuntimeError(f'找不到主键 {cls.__name__}')
        return primary_column

    def expunge(self) -> None:
        """脱离会话"""
        make_transient(self)


class CRUDModel(DeclarativeModel):
    """CRUD模型类"""

    __abstract__ = True

    """新增"""

    def insert(self, flush: bool = True) -> None:
        """
        插入自身

        ```python

        user = User(username=1)
        user.insert()
        ```
        """
        self.expunge()
        self.session().add(self)
        if flush:
            self.session().flush()

    @classmethod
    def insert_by_obj(cls: Type[_T], object) -> _T:
        """插入任意对象"""
        return cls(**dict(object)).insert()

    @classmethod
    def insert_batch(cls, objects: List[Any]) -> List[_T]:
        """插入分批对象"""
        results: List[_T] = []
        for obj in objects:
            _empty_primary(cls, object)
            if isinstance(obj, cls):
                target = obj
            else:
                target = cls(**dict(obj))
            target.insert(flush=False)
            results.append(target)
        cls.session().flush()
        return results

    """更新"""

    @classmethod
    def update_by_id(cls, id: ID, values: dict) -> int:
        """
        根据ID条件更新

        Args:
            id: 主键ID
            values: 需要更新的数据以字典的形式

        Returns:
            int 更新条数

        Example:
            User.update_by_id(1, {
                User.nickname: '张三'
            })
        """
        return cls.query().filter(cls.primary_column() == id).update(values)

    @classmethod
    def update_batch_ids(cls, ids: List[ID], values: dict) -> int:
        """
        根据ID列表条件更新

        Args:
            ids: 主键ID列表
            values: 需要更新的数据以字典的形式

        Returns:
            int 更新条数

        Example:
            User.update_batch_ids([1, 2, 3], {
                User.nickname: '张三'
            })
        """
        return cls.query().filter(cls.primary_column().in_(ids)).update(values)

    @classmethod
    def update(cls, *expressions, values: dict, **kwargs) -> int:
        """
        根据复杂条件更新

        Args:
            expressions: where表达式以元祖的形式传递
            values: 需要更新的数据以字典的形式
            kwargs: where筛选条件以字典形式传递

        Returns:
            int 更新条数

        Example:
            User.update(User.id == 1, id=1, values={
                User.nickname: '张三'
            })
        """
        return cls.query().filter(*expressions).filter_by(**kwargs).update(values)

    """保存"""

    def save(self, flush: bool = True) -> None:
        """保存对象"""
        self.session().merge(self)
        if flush:
            self.session().flush()

    """读取"""

    @classmethod
    def get_by_id(cls: Type[_T], id: ID, *columns) -> _T:
        """
        根据ID查询一条记录

        Args:
            id: 主键ID
            columns: 查询字段列表一旦添加返回类型为Row且不可变

        Returns:
            T 模型对象 | Row 行数据 | None

        Example:
            User.get_by_id(1, User.id, User.nickname)
        """
        return cls.query(*columns).filter(cls.primary_column() == id).first()

    @classmethod
    def select_one(cls: Type[_T], *expressions, _columns: Columns = None, _order_by=None, **kwargs) -> _T:
        """
        根据组合条件查询一条记录，等同于get_one，get

        Args:
            expressions: where表达式以元祖的形式传递
            _columns: 查询字段列表一旦添加返回类型为Row且不可变
            _order_by: 排序字段，支持元祖类型传递
            kwargs： where筛选条件以字典形式传递

        Returns:
            T 模型对象 | Row 行数据 | None

        Example:
            User.select_one(User.id == 1, id=1, _columns=User.id, _order_by=User.id.desc())
        """
        return cls.get(*expressions, _columns=_columns, _order_by=_order_by, **kwargs)

    @classmethod
    def get_one(cls: Type[_T], *expressions, _columns: Columns = None, _order_by=None, **kwargs) -> _T:
        """根据组合条件查询一条记录，等同于select_one，get

        Args:
            expressions: where表达式以元祖的形式传递
            _columns: 查询字段列表一旦添加返回类型为Row且不可变
            _order_by: 排序字段，支持元祖类型传递
            kwargs： where筛选条件以字典形式传递

        Returns:
            T 模型对象 | Row 行数据 | None

        Example:
            User.select_one(User.id == 1, id=1, _columns=User.id, _order_by=User.id.desc())
        """
        return cls.get(*expressions, _columns=_columns, _order_by=_order_by, **kwargs)

    @classmethod
    def get(cls: Type[_T], *expressions, _columns: Columns = None, _order_by=None, **kwargs) -> _T:
        """根据组合条件查询一条记录，等同于select_one，get_one

        Args:
            expressions: where表达式以元祖的形式传递
            _columns: 查询字段列表一旦添加返回类型为Row且不可变
            _order_by: 排序字段，支持元祖类型传递
            kwargs： where筛选条件以字典形式传递

        Returns:
            T 模型对象 | Row 行数据 | None

        Example:
            User.select_one(User.id == 1, id=1, _columns=User.id, _order_by=User.id.desc())
        """
        query = cls.query(*_build_columns_query(cls, _columns)).filter(*expressions).filter_by(**kwargs)
        if _order_by is not None:
            query = _build_order_by_query(query, _order_by)
        return query.first()

    @classmethod
    def get_by_dict(cls: Type[_T], values: Dict[str, Any]) -> _T:
        """
        根据 values 条件，查询一条记录

        Args:
            values: where条件以字典形式传递

        Returns:
            T 模型对象 | Row 行数据 | None
        """
        return cls.query().filter_by(**values).first()

    """列表式"""

    @classmethod
    def select(
        cls: Type[_T],
        *expressions,
        _columns: Columns = None,
        _limit: Optional[int] = None,
        _offset: Optional[int] = None,
        _order_by=None,
        **kwargs
    ) -> List[_T]:
        """
        根据复杂条件查询所有记录

        Args:
            expressions: where表达式以元祖的形式传递
            _columns: 查询字段列表一旦添加返回类型为Row且不可变
            _limit: 限制数量，设置该字段将最多返回设置的数量
            _offset: 偏移量，设置该字段将跳过对应数量
            _order_by: 排序字段，支持元祖类型传递
            kwargs: where条件以字典形式传递

        Returns:
            List[T] 列表[模型对象] | List[Row] 列表[行数据] | []

        Example:
            User.select(User.id == 1, id=1, _columns=User.id, _order_by=User.id.desc(), _limit=1, _offset=1)
        """
        query = cls.query(*_build_columns_query(cls, _columns)).filter(*expressions).filter_by(**kwargs)
        if _order_by is not None:
            query = _build_order_by_query(query, _order_by)
        if _limit is not None:
            query = query.limit(_limit)
        if _offset is not None:
            query = query.offset(_offset)
        return query.all()

    @classmethod
    def select_page(
        cls: Type[_T],
        page: IPage,
        *expressions,
        _columns: Columns = None,
        _order_by=None,
        **kwargs
    ) -> List[_T]:
        """
        根据复杂条件查询所有记录并分页

        Args:
            page: IPage子类你可以集成IPage并实现它所需的方法，FastAPIDB就能识别你的分页载荷。
            expressions: where表达式以元祖的形式传递
            _columns: 查询字段列表一旦添加返回类型为Row且不可变
            _order_by: 排序字段，支持元祖类型传递
            kwargs: where条件以字典形式传递

        Returns:
            List[T] 列表[模型对象] | List[Row] 列表[行数据] | []

        Example:
            User.select_page(Page(1, 20), User.id == 1, id=1, _columns=User.id, _order_by=User.id.desc())
        """
        query = cls.query(*_build_columns_query(cls, _columns)).filter(*expressions).filter_by(**kwargs)
        if _order_by is not None:
            query = _build_order_by_query(query, _order_by)
        query = _build_pagination_query(query, page)
        return query.all()

    @classmethod
    def select_page_with_count(
        cls: Type[_T],
        page: IPage,
        *expressions,
        _columns: Columns = None,
        _order_by=None,
        **kwargs
    ) -> Tuple[int, List[_T]]:
        """
        根据复杂条件查询所有记录并查询总记录数量和分页

        Args:
            page: IPage子类你可以集成IPage并实现它所需的方法，FastAPIDB就能识别你的分页载荷。
            expressions: where表达式以元祖的形式传递
            _columns: 查询字段列表一旦添加返回类型为Row且不可变
            _order_by: 排序字段，支持元祖类型传递
            kwargs: where条件以字典形式传递

        Returns:
            Tuple[int, List[T]] | Tuple[int, List[Row]] | 0, []

        Example:
            count, users = User.select_page_with_count(
                                Page(1, 20),
                                id=1,
                                _columns=User.id,
                                _order_by=User.id.desc()
                            )
        """
        query = cls.query(*_build_columns_query(cls, _columns)).filter(*expressions).filter_by(**kwargs)
        if _order_by is not None:
            query = _build_order_by_query(query, _order_by)
        count = query.count()
        query = _build_pagination_query(query, page)
        return count, query.all()

    @classmethod
    def select_all(cls: Type[_T]) -> List[_T]:
        """不加任何条件查询所有"""
        return cls.query().all()

    @classmethod
    def select_batch_ids(cls: Type[_T], ids: List[ID]) -> List[_T]:
        """查询（根据ID 批量查询）"""
        return cls.query().filter(cls.primary_column().in_(ids)).all()

    @classmethod
    def select_count(cls: Type[_T], *expressions, **kwargs) -> int:
        """根据条件，查询记录数"""
        return cls.query().filter(*expressions).filter_by(**kwargs).count()

    """删除"""

    def delete(self, flush: bool = True) -> None:
        """删除自身"""
        self.session().delete(self)
        if flush:
            self.session().flush()

    @classmethod
    def delete_by_expressions(cls, *expressions, **kwargs) -> int:
        """根据表达式删除"""
        return cls.query().filter(*expressions).filter_by(**kwargs).delete()

    @classmethod
    def delete_by_id(cls, rid: ID) -> int:
        """根据 ID 删除"""
        return cls.query().filter(cls.primary_column() == rid).delete()

    @classmethod
    def delete_by_dict(cls, values: Dict[str, Any]) -> int:
        """根据 values 条件，删除记录"""
        return cls.query().filter_by(**values).delete()

    @classmethod
    def delete_batch_ids(cls, ids: List[ID]) -> int:
        """删除（根据ID 批量删除）"""
        return cls.query().filter(cls.primary_column().in_(ids)).delete()

    """扩展"""

    @classmethod
    def exist(cls, *expressions, **kwargs) -> bool:
        return cls.query().filter(*expressions).filter_by(**kwargs).count() > 0

    @classmethod
    def exit_by_id(cls, id: ID) -> bool:
        return cls.query().filter(cls.primary_column() == id).count() > 0


class Model(CRUDModel):
    """基础模型"""
    __abstract__ = True