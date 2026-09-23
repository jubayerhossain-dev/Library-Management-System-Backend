from fastapi import FastAPI, Depends, HTTPException
import model
from model import Books, Reservation, Issuerecord
from sqlalchemy.orm import Session
from database import engine, sessionlocal
from typing import Annotated, Optional
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from router import admin, auth
from router.auth import token_decode



app = FastAPI()

model.Base.metadata.create_all(bind=engine) 
app.include_router(auth.router)
app.include_router(admin.router)


def open_database():
    db = sessionlocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(open_database)]
user_dependency = Annotated[dict, Depends(token_decode)]


@app.get('/book/all')
def ShowAllBook(db: db_dependency):
    book = db.query(Books).all()
    return book


@app.get('/book/{id}')
def SearchBookID(db: db_dependency, user: user_dependency, id: int):

    if user is None:
        raise HTTPException(status_code=404, detail='Faild Authentication')

    search_book = db.query(Books).filter(Books.id == id).first()
    if search_book is None:
        raise HTTPException(status_code=404, detail='Book Not Found')
    return search_book

@app.post('/reserve/{book_id}')
def ReserveBook(db: db_dependency, user: user_dependency, book_id : int):
    
    if user is None:
        raise HTTPException(status_code=404, detail='Faild Authentication')
        
    reserve_book = db.query(Books).filter(Books.id == book_id).first()
    
    if reserve_book is None:
        raise HTTPException(status_code=404, detail='ID NOT FOUND') 
    
    reservation_model = Reservation(
        book_id = book_id,
        user_id = user.get("id")
    )
    
    db.add(reservation_model)
    db.commit()
    return JSONResponse(status_code=201, content='Book Reserved Succesful')


@app.get('/reserve/all')
def ReserveBook(db: db_dependency, user: user_dependency):
    
    if user is None:
        raise HTTPException(status_code=404, detail='Faild Authentication')
          
    book_reserve = db.query(Reservation).filter(Reservation.user_id == user.get('id')).all()
    
    return book_reserve


@app.delete('/reserve/cancel/{reserve_id}')
def reserve_cancel(db : db_dependency, user: user_dependency, reserve_id : int):
    
    if user is None:
        raise HTTPException(status_code=404, detail='Faild Authentication')
    
    cancel_reserve = db.query(Reservation).filter(Reservation.id == reserve_id).first()
    
    cancel_reserve.status = "Cancelled"
    
    db.commit()
    
    return JSONResponse(status_code=201, content='Cancel Successfully')



@app.get('/reserve/issue')
def reserve_issue(db : db_dependency, user: user_dependency):
    
    if user is None:
        raise HTTPException(status_code=404, detail='Faild Authentication')
    
    return  db.query(Issuerecord).filter(Issuerecord.user_id == user.get('id')).all()