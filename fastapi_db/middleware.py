# -*- coding:utf-8 -*-
from typing import Optional, Union

from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.requests import Request
from .extensions import FastAPIDB, local_transaction, get_transaction_context


class FastAPIDBMiddleware(BaseHTTPMiddleware):
    """
    FastAPIDB 是一个集成了 SQLAlchemy 和 FastAPI 的 Python 库，旨在帮助开发者用简单的方法操作数据库并管理事务从而快速构建高效可维护的应用。

    特点：
        数据库操作简化：可直接从代理器ctx.session访问到当前上下文获取sqlalchemy会话查询和操作，也可直接通过Model.query()操作对应数据，
            它们最终的结果都是一样的。

        集成CRUD API：提供了丰富的CRUD API，允许开发者通过简单的函数调用即可实现数据的创建、读取、更新和删除、
            大大减少了重复代码和潜在的错误。

        声明式事务管理：使得事务的控制变得简单而清晰。开发者可以通过装饰器或上下文管理器来声明事务的边界，
            FastAPIDB 会自动处理事务的提交或回滚，确保数据的一致性和完整性。


    使用：
        这是一个简单的例子，但这种方式无法在启动时被初始化。
        ```python
        from fastapi import FastAPI
        from fastapi_db import FastAPIDBMiddleware
        from sqlalchemy import create_engine

        app = FastAPI()

        engine = create_engine('sqlite:///test.db')
        app.add_middleware(FastAPIDBMiddleware, engine=engine)
        ```

        第二种方式，推荐第二种
        ```python
        from fastapi import FastAPI
        from fastapi_db import FastAPIDB
        from sqlalchemy import create_engine

        app = FastAPI()

        engine = create_engine('sqlite:///test.db')
        extension = FastAPIDB(app, engine=engine)
        ```
    """

    def __init__(
        self,
        app: ExceptionMiddleware,
        datasource_url: Optional[Union[str, URL]] = None,
        engine: Optional[Engine] = None,
        engine_kwargs: dict = None,
        session_kwargs: dict = None,
        autocommit: bool = True
    ):
        super().__init__(app)
        self.autocommit = autocommit
        self.engine_kwargs = engine_kwargs or {}
        self.session_kwargs = session_kwargs or {}

        self.extension = FastAPIDB(
            datasource_url=datasource_url,
            engine=engine,
            engine_kwargs=engine_kwargs,
            session_kwargs=session_kwargs,
            autocommit=autocommit
        )

        fastapi_app = app.app.dependency_overrides_provider  # type: ignore
        fastapi_app.fastapi_db = self.extension

    async def dispatch(self, request: Request, call_next):
        with local_transaction(autocommit=self.autocommit):
            get_transaction_context().source = 'request'
            return await call_next(request)