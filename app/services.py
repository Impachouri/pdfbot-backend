import os
import uuid
from PyPDF2 import PdfReader
from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.models import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

def process_pdf(file: UploadFile, db: Session) -> (int, str):
    # Save the uploaded file to a temporary location
    file_path = f"temp/{file.filename}"  # Assuming 'temp' is a writable directory
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as temp_file:
        temp_file.write(file.file.read())

    # Read PDF content
    pdf_reader = PdfReader(file_path)
    text_content = ""
    for page in pdf_reader.pages:
        text_content += page.extract_text()

    # Generate session token
    session_token = str(uuid.uuid4())

    # Store document metadata in the database
    db_document = Document(filename=file.filename, text_content=text_content, session_token=session_token)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    # Clean up temporary file
    os.remove(file_path)

    return db_document.id, session_token


def get_text_chunks(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = splitter.split_text(text)
    return chunks  # list of strings


# Function to create vector store from text chunks
def get_vector_store(chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")

# Function to initialize conversational chain for question answering
def get_conversational_chain():
    prompt_template = """
    Answer the question as detailed as possible from the provided context, make sure to provide all the details, if the answer is not in
    provided context just say, "answer is not available in the context", don't provide the wrong answer\n\n
    Context:\n {context}?\n
    Question: \n{question}\n

    Answer:
    """
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", client=None, temperature=0.3)  
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(llm=model, chain_type="stuff", prompt=prompt)
    return chain


def user_input(user_question):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True) 
    docs = new_db.similarity_search(user_question)
    chain = get_conversational_chain()
    response = chain.invoke({"input_documents": docs, "question": user_question}, return_only_outputs=True)
    return response



from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate

def answer_question(document: Document, question: str, db: Session) -> str:
    if not document:
        return "Document not found or invalid session token"

    text_chunks = get_text_chunks(document.text_content)
    get_vector_store(text_chunks)

    response = user_input(question)
    return response['output_text']