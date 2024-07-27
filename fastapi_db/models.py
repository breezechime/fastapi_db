from typing import Type, Union, Dict, List, Optional, Any
from sqlalchemy.orm import Session, declarative_base, Query, InstrumentedAttribute, make_transient
from .constants import _T, ID
from .extensions import ctx
from .types import IPage
from .utils import _empty_primary

_Base = declarative_base()


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

    def out_session(self) -> None:
        """脱离会话"""
        make_transient(self)


class CRUDModel(DeclarativeModel):
    """CRUD模型类"""

    __abstract__ = True

    """新增"""

    def insert(self, flush: bool = True) -> None:
        """插入自身"""
        _empty_primary(self, self)
        self.session().add(self)
        if flush:
            self.session().flush()

    @classmethod
    def insert_by_obj(cls: Type[_T], object) -> _T:
        """插入任意对象"""
        _empty_primary(cls, object)
        return cls(**dict(object)).insert()

    @classmethod
    def insert_batch(cls, objects: List[Any]) -> List[_T]:
        """插入分批对象"""
        results = []
        for obj in objects:
            _empty_primary(cls, object)
            if isinstance(obj, cls):
                results.append(obj.insert(flush=False))
            else:
                results.append(cls(**dict(obj)).insert(flush=False))
        cls.session().flush()
        return results

    """更新"""

    @classmethod
    def update_by_dict(cls):
        pass

    """保存"""

    def save(self, flush: bool = True) -> None:
        """保存对象"""
        self.session().merge(self)
        if flush:
            self.session().flush()

    """读取"""

    @classmethod
    def get(cls, *expressions, **kwargs) -> _T:
        """根据表达式查询"""
        return cls.query().filter(*expressions).filter_by(**kwargs).first()

    @classmethod
    def get_by_id(cls, id: ID, *columns) -> _T:
        """根据ID查询"""
        return cls.query(*columns).filter(cls.primary_column() == id).first()

    @classmethod
    def get_by_dict(cls, values: Dict[str, Any]) -> _T:
        """根据 values 条件，查询记录"""
        return cls.query().filter_by(**values).first()

    @classmethod
    def get_count(cls, *expressions, **kwargs) -> int:
        """根据 filter 条件，查询总记录数"""
        return cls.query(cls.primary_column()).filter(*expressions).filter_by(**kwargs).count()

    """列表式"""

    @classmethod
    def select(
        cls,
        *expressions,
        __limit: Optional[int] = None,
        __offset: Optional[int] = None,
        __order_by=None,
        **kwargs
    ) -> _T:
        """根据条件查询"""
        query = cls.query().filter(*expressions).filter_by(**kwargs)
        if __order_by is not None:
            query = query.order_by(__order_by)
        if __limit is not None:
            query = query.limit(__limit)
        if __offset is not None:
            query = query.offset(__offset)
        return query.all()

    @classmethod
    def select_page(
        cls,
        page: IPage,
        *expressions,
        __order_by=None,
        **kwargs
    ) -> _T:
        """根据条件查询并分页"""
        query = cls.query().filter(*expressions).filter_by(**kwargs)
        if __order_by is not None:
            query = query.order_by(__order_by)
        return query.all()

    @classmethod
    def select_all(cls):
        """不加任何条件查询所有"""
        return cls.query().all()

    @classmethod
    def select_batch_ids(cls, ids: List[ID]) -> List[_T]:
        """查询（根据ID 批量查询）"""
        return cls.query().filter(cls.primary_column().in_(ids)).all()

    """删除"""

    @classmethod
    def delete(cls, *expressions, **kwargs) -> int:
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