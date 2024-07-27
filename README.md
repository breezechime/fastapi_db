# FastAPI DB

用于 fastapi 应用，可随时获取上下文，使用sqlalchemy，封装Base让模型类直接查询。
目前仅支持单数据库的应用，已封装CRUD模型，大幅度解放双手

## 对象说明

**FastAPIDBMiddleware**: 中间件通过add_middleware绑定，但需要运行到web才能触发

**FastAPIDB**：扩展应用，你可以传递FastAPI实例自动绑定事务中间件，不需要运行到web即可触发使用

**TransactionManager**: 事务管理器，用于创建会话，进入上下文，退出上下文等操作

**TransactionContext**: 事务上下文，sqlalchemy到会话也在里面，存放于ContextVar中

**local_transaction**： 局部上下文，你可以通过with创建局部事务上下文

**transactional**： 函数声明式事务，你可以使用它进行复杂的业务，而无需依次传递会话

**ctx**： 上下文代理器，你可以通过它随时访问session，但你要确保代码已经提前开启了事务

**CRUDModel**：增删改查模型，你一般情况不需要继承它，而是继承Model

## 示例代码

```python
import random
import uvicorn
from fastapi import FastAPI
from fastapi_db import FastAPIDBMiddleware, Model, ctx
from sqlalchemy import Column, String, create_engine, Integer

app = FastAPI()

engine = create_engine('sqlite:///test.db')
app.add_middleware(FastAPIDBMiddleware, engine=engine)


class Base(Model):
    __abstract__ = True


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), nullable=False, unique=True)


Base.metadata.create_all(engine)


@app.get('/user')
def get_list():
    users = User.query().all()
    return users


@app.get('/create')
def create_user(username: str = None):
    if username is None:
        username = str(random.randint(1, 99999))
    user = User(username=username)
    """你可以在接口的任意位置获取session并使用"""
    user.insert()
    """如果你需要返回自增id，注意请不要在业务层随意添加commit，这会导致你的程序不可控，添加flush可以解决很多问题"""
    ctx.session.flush()
    return user


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=9001)
```


## 如果你想在启动时查询数据

你需要注意的是每次local_transaction生产的事务都是不同的，你可以改变传播方式达到你想要的目的

```python
from fastapi import FastAPI
from fastapi_db import FastAPIDB, Model, ctx, local_transaction
from sqlalchemy import Column, String, create_engine, Integer

app = FastAPI()

engine = create_engine('sqlite:///test.db')
extension = FastAPIDB(app, engine=engine)


class Base(Model):
    __abstract__ = True


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), nullable=False, unique=True)
    
    def __repr__(self):
        return f"User(id={self.id}, username={self.username})"

Base.metadata.create_all(engine)

with local_transaction() as context:

    """你会得到是个事务上下文对象, sqlalchemy会话也在其中"""
    print(context)
    # TransactionContext(session=<sqlalchemy.orm.session.Session object at 0x1209ea690>,
    # propagation=Propagation.NEW, isolation=Isolation.DEFAULT, autocommit=True)

    """使用会话查询对象"""
    users = context.session.query(User).all()
    print(users)
    # > [User(id=1, username=asd), User(id=2, username=6891), User(id=3, username=55896), User(id=4, username=74272),
    # User(id=5, username=96389), User(id=6, username=91287), User(id=7, username=52207)]

    """使用代理器查询对象"""
    users = ctx.session.query(User).all()
    print(users)
    # > [User(id=1, username=asd), User(id=2, username=6891), User(id=3, username=55896), User(id=4, username=74272),
    # User(id=5, username=96389), User(id=6, username=91287), User(id=7, username=52207)]

    """使用模型查询"""
    users = User.select_all()
    print(users)
    # > [User(id=1, username=asd), User(id=2, username=6891), User(id=3, username=55896), User(id=4, username=74272),
    # User(id=5, username=96389), User(id=6, username=91287), User(id=7, username=52207)]
```


## 声明式事务

你需要注意的是声明式事务和其它开启事务方式的区别，声明式事务默认传播方式为查找上级事务，如果不存在则创建。声明式事务一旦创建则不会自动关闭。

```python
from fastapi import FastAPI
from sqlalchemy import Column, String, create_engine, Integer
from fastapi_db import Model, FastAPIDB, ctx, transactional, Propagation, local_transaction

app = FastAPI()

engine = create_engine('sqlite:///test.db')
FastAPIDB(app, engine=engine)


class Base(Model):
    __abstract__ = True


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), nullable=False, unique=True)

    def __repr__(self):
        return f"User(id={self.id}, username={self.username})"


Base.metadata.create_all(engine)


@transactional()
def test1():
    """transactional默认会使用父级会话，没有则创建"""
    print(ctx.session)
    # > <sqlalchemy.orm.session.Session object at 0x105a1ab50>


@transactional()
def test2():
    """transactional默认会使用父级会话，没有则创建，可以看到和test1的会话是同一个"""
    print(ctx.session)
    # > <sqlalchemy.orm.session.Session object at 0x105a1ab50>


@transactional(propagation=Propagation.NEW)
def test3():
    # 使用传播方式修改事务开启方式，这里无论上级是否存在事务都会创建
    print(ctx.session)
    # > <sqlalchemy.orm.session.Session object at 0x110727d90>


test1()
test2()
test3()
```


# 增删改查