from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Document
from app.schemas import QuestionRequest, AnswerResponse
from app.services import process_pdf, answer_question

router = APIRouter()

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    db = SessionLocal()
    document_id, session_token = process_pdf(file, db)
    db.close()
    return JSONResponse(content={"document_id": document_id, "session_token": session_token})

@router.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest, session_token: str = Header(..., alias='session-token')):
    db = SessionLocal()
    print(session_token, request.question)
    document = db.query(Document).filter(Document.session_token == session_token).first()
    if not document:
        raise HTTPException(status_code=400, detail="Invalid session token")
    # print("document ", document.text_content)
    answer = answer_question(document, request.question, db)
    db.close()
    return AnswerResponse(answer=answer)
