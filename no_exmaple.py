from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine('sqlite:///test.db', echo=False)


Base = declarative_base()
Session = sessionmaker(bind=engine)


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), nullable=False, unique=True)

    def __repr__(self):
        return f"User(id={self.id}, username={self.username})"


Base.metadata.create_all(engine)


session1 = Session()
session2 = Session()

session2.query(User).filter_by(id=1).delete()
session2.flush()
users = session1.query(User).all()
print(users)