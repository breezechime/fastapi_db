# -*- coding:utf-8 -*-
from typing import Optional, Union
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from .extensions import FastAPIDB


class FastAPIDBMiddleware(BaseHTTPMiddleware):

    def __init__(
        self,
        app: ASGIApp,
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

        self.extension = FastAPIDB(app, datasource_url, engine, engine_kwargs, session_kwargs, autocommit)