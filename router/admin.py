from fastapi import FastAPI, Depends, HTTPException, APIRouter, UploadFile, File
import model
from model import Books, Reservation, Users, Issuerecord
from sqlalchemy.orm import Session
from database import engine, sessionlocal
from typing import Annotated, Optional
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from router import admin, auth
from router.auth import token_decode
from datetime import datetime, timedelta


router = APIRouter()

def open_database():
    db = sessionlocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(open_database)]
user_dependency = Annotated[dict, Depends(token_decode)]

#-----------------------------Create Book--------------------------------------#
class BookCreate(BaseModel):

    title: str = Field(..., min_length=2, max_length=100)
    author: str = Field(..., min_length=2, max_length=100)
    category: str
    description: str
    price: int = Field(..., gt=0)
    total_copy: int = Field(default=1)
    # cover_image: UploadFile = File(None)
    cover_image: Optional[str] = None
    

@router.post('/admin/create_book')
def create_book(db: db_dependency, user: user_dependency, new_book: BookCreate):
    
    if user is None or user.get('role') != 'librarian':
        raise HTTPException(status_code=404, detail='Faild Authentication')
    
    book_model = Books(**new_book.model_dump(), avalaible_copy = new_book.total_copy)
    
    db.add(book_model)
    db.commit()
    db.refresh(book_model)  
    
    return JSONResponse(status_code=201, content="Book Add Successful")


#-----------------------------Update Book--------------------------------------#
class BookUpdate(BaseModel):

    title: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    total_copy: Optional[int] = None
    avalaible_copy: Optional[int] = None
    cover_image: Optional[str] = None
   

@router.put('/admin/updatebook/{book_id}')
def update_book(db: db_dependency, user: user_dependency, update_book: BookUpdate, book_id: int):
    
    if user is None or user.get('role') != 'librarian':
        raise HTTPException(status_code=404, detail='Faild Authentication')
    
    book_model = db.query(Books).filter(Books.id == book_id).first()
    
    if book_model is None:
        raise HTTPException(status_code=404, detail='Book Not Found')
    
    update_data = update_book.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(book_model, key, value)
    
    db.commit()
    
    return JSONResponse(status_code=201, content="Book Update Successful")

#-----------------------------Delete--------------------------------------#
@router.delete('/admin/deletebook/{book_id}')
def delete_book(db: db_dependency, user: user_dependency, book_id: int):
    
    if user is None or user.get('role') != 'librarian':
        raise HTTPException(status_code=403, detail='Faild Authentication')
    
    book_model = db.query(Books).filter(Books.id == book_id).first()
    
    if book_model is None:
        raise HTTPException(status_code=404, detail='Book Not Found')
    
    db.delete(book_model)
    db.commit()
    
    return JSONResponse(status_code=201, content="Book Update Successful")


class IssueCreate(BaseModel):
    book_id: Optional[int] = None
    user_id: Optional[int] = None


@router.post('/admin/issue_create')
def create_issue(db: db_dependency,user: user_dependency, issue_record: IssueCreate):

    if user is None or user.get('role') != 'librarian':
        raise HTTPException(status_code=404,detail='Failed Authentication')

    book = db.query(Books).filter(Books.id == issue_record.book_id).first()

    if book is None:
        raise HTTPException(status_code=404,detail='Book Not Found')
        
    member = db.query(Users).filter(Users.id == issue_record.user_id).first()

    if member is None:
        raise HTTPException(status_code=404,detail='Member Not Found')

    # Issue date and due date
    load_days = 10

    issue_date = datetime.now()

    due_date = issue_date + timedelta(days=load_days)

    # Database model
    issuecollect = Issuerecord(
        book_id=issue_record.book_id,
        user_id=issue_record.user_id,
        issue_date=issue_date,
        due_date=due_date
    )

    # Decrease available copy
    book.avalaible_copy -= 1

    # Check reservation
    reservation = db.query(Reservation).filter(
        Reservation.book_id == issue_record.book_id,
        Reservation.user_id == issue_record.user_id,
        Reservation.status == 'Pending'
    ).first()

    if reservation is not None:
        reservation.status = 'approved'

    db.add(issuecollect)

    db.commit()

    return JSONResponse(
        status_code=201,
        content="Issued Collected"
    )
    
    
    
fine_amount = 20 
def calculate_fine(due_date: datetime, return_date: datetime):
    overdue_days = (return_date.date() - due_date.date()).days
    
    if overdue_days > 0:
        return round(float(overdue_days * fine_amount), 2)
    else:
        return 0.0
    
@router.put('/admin/return_book/{issue_id}')
def return_book(db: db_dependency,user: user_dependency, issue_id: int):

    if user is None or user.get('role') != 'librarian':
        raise HTTPException(status_code=404,detail='Failed Authentication')

    issue = db.query(Issuerecord).filter(Issuerecord.id == issue_id).first()

    if issue is None:
        raise HTTPException(status_code=404,detail='Issue Not Found')
        
    return_date = datetime.now()
    fine = calculate_fine(issue.due_date, return_date)
    
    issue.return_date = return_date
    issue.status = 'returned'
    issue.fine_amount = fine
    
    book = db.query(Books).filter(Books.id == issue.book_id).first()
    book.avalaible_copy += 1
    
    db.commit()
    
    return JSONResponse(status_code=201, content="Book Return Successfully..")


@router.put('/admin/fine_paid/{issue_id}')
def fine_paid(db: db_dependency,user: user_dependency, issue_id: int):

    if user is None or user.get('role') != 'librarian':
        raise HTTPException(status_code=404,detail='Failed Authentication')

    issue = db.query(Issuerecord).filter(Issuerecord.id == issue_id).first()

    if issue is None:
        raise HTTPException(status_code=404,detail='Issue Not Found')
    
    issue.fine_paid = True
    
    db.commit()
    
    return JSONResponse(status_code=201, content="Fine Paid Successfully..")



@router.get("/reserve/all_book")
def get_all_reserve_book(user: user_dependency, db: db_dependency):

    if user or user.get('role') == 'librarian':
        all_reserve = db.query(Reservation).all()
        return all_reserve