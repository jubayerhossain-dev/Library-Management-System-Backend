from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

SQL_DATABASE_URL = 'sqlite:///./DataCenterHome.db'

engine = create_engine(SQL_DATABASE_URL, connect_args={'check_same_thread': False})
sessionlocal = sessionmaker(autoflush= False, autocommit= False, bind=engine)
Base = declarative_base()