# -*- coding:utf-8 -*-
import enum


class Propagation(enum.Enum):
    """事务传播枚举类"""

    REQUIRED = 'required'
    """如果当前存在事务，则加入该事务；如果当前没有事务，则创建一个新的事务。"""

    NEW = 'new'
    """创建一个新的事务，如果当前存在事务，则把当前事务挂起。"""

    MANDATORY = 'mandatory'
    """如果当前存在事务，则加入该事务；如果当前没有事务，则抛出异常。"""


class Isolation(enum.Enum):
    """事务隔离级别枚举类"""

    DEFAULT = 'DEFAULT'
    """使用默认数据库全局事务"""

    READ_UNCOMMITTED = 'READ UNCOMMITTED'
    """读未提交"""

    READ_COMMITTED = 'READ COMMITTED'
    """读已提交(mysql默认)"""

    REPEATABLE_READ = 'REPEATABLE READ'
    """可重复读"""

    SERIALIZABLE = 'SERIALIZABLE'
    """串行化"""