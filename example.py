import random
import uvicorn
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
    ctx.session.add(user)
    """如果你需要返回自增id，注意请不要在业务层随意添加commit，这会导致你的程序不可控，添加flush可以解决很多问题"""
    ctx.session.flush()
    return user


# if __name__ == '__main__':
#     uvicorn.run(app, host='0.0.0.0', port=9001)
