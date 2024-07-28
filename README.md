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

## 安装

```shell
pip install fastapi_db
```

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
    # 插入数据 会自动flush让数据库返回自增ID，你也可以通过flush参数控制是否返回自增ID
    user.insert()
    print(user.id)
    # > 1
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

## 接口使用事务

默认情况下请求会自动开启事务，你可以使用transactional声明式事务覆盖请求事务，可以改变传播方式，自动提交，隔离级别，异常处理等

```python
import uvicorn
from fastapi import FastAPI
from sqlalchemy import Column, String, create_engine, Integer

from fastapi_db import Model, FastAPIDB, transactional

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


@app.get('/user')
@transactional(autocommit=False)
def get_list():
    # 你可以禁止该接口自动提交，隔离级别或其它参数
    users = User.query().all()
    return users


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=9000)
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

## 异常和回滚捕捉

在默认情况下，如果使用事务过程中发生异常会导致事务自动回滚，你可能需要在回滚前后做点事情，
rollback_callback参数是回滚后会调用的方法，exception_callback是回滚前调用的方法，你可以返回False禁止自动回滚

```python
from sqlalchemy import Column, String, Integer
from fastapi_db import transactional, Model

class Base(Model):
    __abstract__ = True


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), nullable=False, unique=True)

    def __repr__(self):
        return f"User(id={self.id}, username={self.username})"
    
def handle_rollback_error(err):
    # 在这里处理事务回滚后的操作
    print('异常实例', err)
    # > test rollback


@transactional(rollback_callback=handle_rollback_error)
def service2():
    User.delete_by_id(1)

    raise RuntimeError('test rollback')


service2()
```


## 增删改查

本示例使用User作为模型。涉及ID等字段需要模型设置好主键。

如果你想限制字段查询，一般通过_columns参数
如果你想使用order_by查询，一般通过_order_by参数
如果你想限制数量查询，一般通过_limit参数
如果你想使用offset查询，一般通过_offset参数

```python
from sqlalchemy import Column, String, Integer
from fastapi_db import Model, ctx, Page

class Base(Model):
    __abstract__ = True


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), nullable=False, unique=True)

    def __repr__(self):
        return f"User(id={self.id}, username={self.username})"

"""查询操作"""

# 通过ID查询一条记录
User.get_by_id(1)
# 通过表达式条件查询一条记录，等同 select_one，get_one
User.get(id=1)
# 也可以 User.get(User.id == 1)

# 通过表达式条件查询所有记录，可以限制数量，偏移和排序查询
User.select(User.id.in_([1, 2, 3, 4]), _order_by=User.id.desc(), _limit=10, _offset=0)
# 不通过任何条件查询所有记录
User.select_all()
# 通过表达式条件查询并翻页
User.select_page(Page(1, 20), id=1)
# 通过表达式条件查询并翻页和返回总记录数
count, users = User.select_page_with_count(Page(1, 20), id=1)
# 通过ID列表查询所有记录
User.select_batch_ids([1, 2, 3, 4])


"""写入操作"""

# 插入数据
user = User(username='fastapi_db')
user.insert()

# 注意insert操作会导致数据库flush返回自增ID，如果你不需要，可以通过flush参数控制

# 保存数据

user = User(id=1, username='fastapi_db')
user.save()

# save操作会根据主键查询对象的数据并决定是插入还是更新

# 更新操作

# id为1的数据将被更新
User.update(id=1, values={
    User.username: 'app'
})

"""删除"""


# 删除，但是多了查询，你可以直接delete_by_id
user = User.get_by_id(1)
user.delete()

# 通过ID删除，删除成功会返回1
User.delete_by_id(1)

# 通过ID列表删除
User.delete_batch_ids([1, 2, 3, 4, 5])

# 通过表达式删除
User.delete_by_expressions(id=1)

"""基本操作"""

# 数据脱敏（不会再修改到数据库）
user = User.get_by_id(1)
user.expunge()
user.username = '****'


```

## 数据脱敏

```python
# 数据脱敏（不会再修改到数据库）
user = User.get_by_id(1)
user.expunge()
user.username = '****'
```