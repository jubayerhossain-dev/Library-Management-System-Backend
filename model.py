from database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Float
from datetime import datetime

class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    firstname = Column(String(50))
    lastname = Column(String(50))
    email = Column(String(100), unique=True, index=True)
    password = Column(String(100))
    is_active = Column(Boolean, default=True)
    role = Column(String)


class Books(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100))
    author = Column(String(100))
    category = Column(String)
    description = Column(String)
    price = Column(Integer)
    total_copy = Column(Integer)
    avalaible_copy = Column(Integer)
    cover_image = Column(String, nullable=True)
    created_at = Column(DateTime, default= datetime.now())
    
    
    
class Reservation(Base):
    __tablename__ = "reserve"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    Reserve_date = Column(DateTime, default= datetime.now())
    status = Column(String, default='Pending')
    
class Issuerecord(Base):
    
    __tablename__ = "issue_records"
    
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    issue_date = Column(DateTime, default=datetime.now)
    due_date = Column(DateTime)
    return_date = Column(DateTime, nullable=True)
    status = Column(String, default='Issued') #issued / returned
    fine_amount = Column(Float, default=0.0)
    fine_paid = Column(Boolean, default=False)
    
    