from contextvars import ContextVar
from functools import wraps
from typing import Optional, Union, Callable, Any

from fastapi import FastAPI
from fastapi.requests import Request
from sqlalchemy import Engine, URL, create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from .constants import _SESSION_MISSING_MESSAGE
from .exceptions import SessionInitError, SessionContextError
from .transaction_enums import Propagation, Isolation
from .utils import _deserialize_enum

"""
声明式事务线程并且支持局部上下文 | 参考了decimal的源代码实现
decimal: https://github.com/python/cpython/blob/af2b8f6845e31dd6ab3bb0bac41b19a0e023fd61/Lib/_pydecimal.py

作者：KYZ ZDLAY
邮箱：chinadlay@163.com
"""

_extensions: Optional['FastAPIDB'] = None
_transaction_context: ContextVar['TransactionContext'] = ContextVar('fastapi_db')


def _check_init():
    if _extensions is None:
        from .middleware import FastAPIDBMiddleware
        raise SessionInitError(f'请先添加 `{FastAPIDBMiddleware.__name__}` 中间件'
                               f'或初始化 `{FastAPIDB.__name__}` 扩展')


class FastAPIDB:
    """FastAPI数据库扩展"""

    engine: Optional[Engine] = None
    session_factory: Optional[sessionmaker] = None

    def __init__(
         self,
         app: Optional[FastAPI] = None,
         datasource_url: Optional[Union[str, URL]] = None,
         engine: Optional[Engine] = None,
         engine_kwargs: dict = None,
         session_kwargs: dict = None,
         autocommit: bool = True
    ) -> None:
        self.app = app
        self.datasource_url = datasource_url
        self.engine = engine
        self.autocommit = autocommit
        self.engine_kwargs = engine_kwargs or {}
        self.session_kwargs = session_kwargs or {}

        if not datasource_url and not engine:
            raise RuntimeError('您需要传递一个datasource_url或一个引擎参数。')

        if not engine:
            self.engine = create_engine(datasource_url, **self.engine_kwargs)
        else:
            self.engine = engine

        self.session_factory = sessionmaker(bind=self.engine, **self.session_kwargs)
        global _extensions
        _extensions = self

        if app is not None:
            self.init_app(app)

    def init_app(self, app: FastAPI) -> None:
        self.app = app

        @app.middleware('http')
        async def db_session_middleware(request: Request, call_next):
            with local_transaction(autocommit=self.autocommit):
                get_transaction_context().source = 'request'
                return await call_next(request)


class FastAPIDBProxy:
    """FastAPIDB代理器（可随时访问）"""

    @property
    def app(self) -> FastAPIDB:
        _check_init()
        return _extensions

    @property
    def session(self) -> Session:
        transaction_context = get_transaction_context()
        return transaction_context.session

    @property
    def context(self) -> 'TransactionContext':
        transaction_context = get_transaction_context()
        return transaction_context


class TransactionContext:
    """事务上下文"""

    propagation: Propagation
    isolation: Isolation
    session: Session
    autocommit: bool
    rollback_callback: Optional[Callable]
    exception_callback: Optional[Callable]
    is_active_isolation: bool
    is_super: bool
    _token: Any

    def __init__(
        self,
        session: Session,
        propagation: Propagation = Propagation.NEW,
        isolation: Isolation = Isolation.DEFAULT,
        autocommit: bool = True,
        rollback_callback: Optional[Callable] = None,
        exception_callback: Optional[Callable] = None
    ):
        self._token = None
        self.propagation = propagation
        self.isolation = isolation
        self.session = session
        self.autocommit = autocommit
        self.is_super = False
        self.source = 'normal'
        self.rollback_callback = rollback_callback
        self.exception_callback = exception_callback
        self.is_active_isolation = self.active_isolation(self.isolation)

    def active_isolation(self, isolation: Isolation) -> bool:
        """激活"""
        if isolation == Isolation.DEFAULT or self.active_isolation:
            self.is_active_isolation = True
            return True
        self.session.execute(text(f"SET SESSION TRANSACTION ISOLATION LEVEL {isolation.value}"))
        self.is_active_isolation = True
        return True

    def __repr__(self):
        return (f"{self.__class__.__name__}("
                f"session={self.session}, propagation={self.propagation}, "
                f"isolation={self.isolation}, autocommit={self.autocommit}, "
                f"is_super={self.is_super})")


class TransactionManager:
    """事务管理器"""

    def __init__(
        self,
        propagation: Propagation = Propagation.NEW,
        isolation: Isolation = Isolation.DEFAULT,
        autocommit: bool = None,
        rollback_callback: Optional[Callable] = None,
        exception_callback: Optional[Callable] = None,
    ):
        self._token = None
        self.extension: Optional[FastAPIDB] = None
        self.propagation = propagation
        self.isolation = isolation
        self.autocommit = autocommit
        self.rollback_callback = rollback_callback
        self.exception_callback = exception_callback

    def __enter__(self) -> TransactionContext:
        _check_init()
        self.extension = _extensions
        self.autocommit = self.extension.autocommit if self.autocommit is None else self.autocommit
        session = self.build_session(propagation=self.propagation)
        context = TransactionContext(
            session,
            propagation=self.propagation,
            isolation=self.isolation,
            autocommit=self.autocommit,
            rollback_callback=self.rollback_callback,
            exception_callback=self.exception_callback
        )
        try:
            if self.propagation == Propagation.NEW:
                context.is_super = True
            else:
                get_transaction_context()
                context.is_super = False
        except (RuntimeError, SessionContextError):
            context.is_super = True
        self._token = set_transaction_context(context=context)
        context._token = self._token
        return context

    def __exit__(self, exc_type, exc_val, exc_tb):
        transaction_context = get_transaction_context()

        """顶级事务才能移除否则下层会有问题"""
        if transaction_context.is_super:

            """如果有错误自动回滚"""
            if exc_type is not None:
                rollback = None
                if transaction_context.exception_callback is not None:
                    rollback = transaction_context.exception_callback(exc_val)
                if rollback is False:
                    transaction_context.session.rollback()
                if transaction_context.rollback_callback is not None:
                    transaction_context.rollback_callback(exc_val)

            """提交可能也会导致错误"""
            try:
                if transaction_context.autocommit:
                    transaction_context.session.commit()
            except Exception as e:
                if transaction_context.exception_callback is not None:
                    transaction_context.exception_callback(exc_val)
                transaction_context.session.rollback()
                if transaction_context.rollback_callback is not None:
                    transaction_context.rollback_callback(exc_val)
                raise e

            transaction_pop(autocommit=False)

    def build_session(self, propagation: Propagation):
        """构建会话"""
        try:
            old_transaction: Optional[TransactionContext] = get_transaction_context()
        except (RuntimeError, SessionContextError):
            old_transaction: Optional[TransactionContext] = None

        if propagation == Propagation.MANDATORY:
            """强制上级事务"""
            if old_transaction is None:
                raise SessionContextError('标记为强制查找上级事务，但从未发现上级事务')
            return old_transaction.session
        elif propagation == Propagation.NEW:
            """创建新会话"""
            return self.extension.session_factory()
        elif propagation == Propagation.REQUIRED:
            """使用上级事务"""
            if old_transaction is None:
                return self.extension.session_factory()
            return old_transaction.session

        raise RuntimeError('未知的事务传播方式')


def local_transaction(
    propagation: Propagation = Propagation.NEW,
    isolation: Isolation = Isolation.DEFAULT,
    autocommit: bool = None,
    rollback_callback: Optional[Callable] = None,
    exception_callback: Optional[Callable] = None,
) -> TransactionManager:
    """局部事务"""
    return TransactionManager(
        propagation=propagation,
        isolation=isolation,
        autocommit=autocommit,
        rollback_callback=rollback_callback,
        exception_callback=exception_callback
    )


def get_transaction_context() -> TransactionContext:
    """获取事务上下文"""
    _check_init()
    try:
        return _transaction_context.get()
    except LookupError:
        raise SessionContextError(_SESSION_MISSING_MESSAGE)


def set_transaction_context(context: TransactionContext):
    """设置事务上下文"""
    _check_init()
    return _transaction_context.set(context)


def transactional(
    propagation: Union[Propagation, str] = Propagation.REQUIRED,
    isolation: Union[Isolation, str] = Isolation.DEFAULT,
    autocommit: bool = None,
    rollback_callback: Callable = None,
    exception_callback: Callable = None,
    cover_request_transaction: bool = True
):
    """
    事务装饰器 transactional decorator
    :param propagation: 事务传播级别 Transaction propagation level
    :param isolation: 事务隔离级别 Transaction isolation level
    :param autocommit: 是否自动提交事务 Whether to automatically commit the transaction
    :param rollback_callback: 回滚回调函数 Rollback callback function
    :param exception_callback: 异常回调函数 Exception callback function
    :param cover_request_transaction: 覆盖请求事务
    """

    propagation = _deserialize_enum(Propagation, propagation)
    isolation = _deserialize_enum(Isolation, isolation)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _autocommit = ctx.app.autocommit if autocommit is None else autocommit
            try:
                transaction_context = get_transaction_context()
                if cover_request_transaction and transaction_context.source == 'request':
                    transaction_context.propagation = propagation
                    transaction_context.isolation = isolation
                    transaction_context.autocommit = _autocommit
                    transaction_context.rollback_callback = rollback_callback
                    transaction_context.exception_callback = exception_callback
                    transaction_context.active_isolation(transaction_context.isolation)
            except (RuntimeError, SessionContextError):
                pass
            with local_transaction(
                propagation=propagation,
                isolation=isolation,
                autocommit=autocommit,
                rollback_callback=rollback_callback,
                exception_callback=exception_callback
            ):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def transaction_pop(autocommit: Optional[bool] = None):
    """移除事务"""
    try:
        transaction_context = get_transaction_context()
    except (RuntimeError, SessionContextError):
        return None

    autocommit = transaction_context.autocommit if autocommit is None else autocommit
    if autocommit:
        transaction_context.session.commit()

    transaction_context.session.close()
    del transaction_context.session
    _transaction_context.reset(transaction_context._token)


ctx: FastAPIDBProxy = FastAPIDBProxy()