from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
import shutil
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pydantic import BaseModel
from io import BytesIO
import fitz
import spacy
import re
from qdrant_client import QdrantClient
from langchain_core.prompts import ChatPromptTemplate
from langchain.llms import Ollama
from qdrant_client.http.models import VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import os
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import json
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("QDRANT_API_KEY")
url = os.getenv("QDRANT_URL")

genRouter = APIRouter()

qdrant_client = QdrantClient(api_key=api_key, url=url)

# Create a collection in Qdrant
COLLECTION_NAME = "new_collection"
qdrant_client.recreate_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=384, distance="Cosine")  # Updated vector dimension to match model output
)

# Load SpaCy model and embedding model globally
nlp = spacy.load("en_core_web_sm")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


def extract_text_from_pdf(pdf_path):
    # Open the file in binary mode and read its contents
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    # Use fitz to process the binary data
    pdf_file = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    text = ""
    for page in pdf_file:
        text += page.get_text()
    
    pdf_file.close()
    return text

def extract_youtube_subtitles(video_url, language='en'):
    try:
        # Extract video ID from URL
        video_id = video_url.split("v=")[-1].split("&")[0]

        # Fetch transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])

        # Format the transcript into plain text
        formatter = TextFormatter()
        subtitles_text = formatter.format_transcript(transcript)

        return subtitles_text
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

def extract_math_questions(text: str) -> List[str]:
    """Extracts possible math questions based on keywords and patterns."""
    question_keywords = [
        "what", "find", "solve", "determine", "prove", "calculate",
        "derive", "evaluate", "how", "show", "if", "why"
    ]
    questions = []
    doc = nlp(text)
    for sent in doc.sents:
        sentence = sent.text.strip()
        if sentence.endswith("?") or any(word in sentence.lower() for word in question_keywords):
            questions.append(sentence)
        elif re.search(r"(find|solve|show|determine|calculate|derive|evaluate).*", sentence, re.IGNORECASE):
            questions.append(sentence)
    return questions


def chunk_text(text: str, chunk_size=500):
    """Divides the text into manageable chunks."""
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i:i + chunk_size])


def store_text_in_qdrant(text, collection_name):
    """Stores text chunks in Qdrant."""
    from sentence_transformers import SentenceTransformer

    # Load a pre-trained model for embeddings
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Ensure embedding dimension matches Qdrant collection
    assert model.get_sentence_embedding_dimension() == 384, "Embedding dimension mismatch!"

    # Split the text into chunks
    chunks = list(chunk_text(text))

    points = []
    for i, chunk in enumerate(chunks):
        if chunk.strip():
            embedding = model.encode(chunk.strip()).tolist()
            points.append(
                PointStruct(
                    id=i,
                    vector=embedding,
                    payload={"text": chunk.strip()}
                )
            )

    # Upload to Qdrant in smaller batches to avoid timeouts
    batch_size = 100
    for j in range(0, len(points), batch_size):
        qdrant_client.upsert(collection_name=collection_name, points=points[j:j + batch_size])

def retrieve_text_from_qdrant(query, collection_name):
    """Retrieves relevant text from Qdrant based on the query."""
    from sentence_transformers import SentenceTransformer

    # Load the same embedding model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    query_vector = model.encode(query).tolist()

    # Perform search in Qdrant
    search_result = qdrant_client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=5
    )
    # Extract text from payloads
    results = [hit.payload['text'] for hit in search_result]
    return " ".join(results)

def clean_json(response: str):
    # Remove unnecessary newline characters and extra spaces from the entire response.
    cleaned_response = response.replace("\n", "").strip()
    
    # Replace non-breaking spaces (\xa0) with regular spaces
    cleaned_response = cleaned_response.replace("\xa0", " ")
    
    # Attempt to parse multiple JSON objects by splitting them using '}' and '{' markers
    json_objects = []
    try:
        # Split based on the pattern and start decoding individual JSON objects
        start_index = 0
        while start_index < len(cleaned_response):
            # Find the next closing brace
            end_index = cleaned_response.find('}', start_index)
            if end_index != -1:
                # Extract one full JSON object and store it
                json_object = cleaned_response[start_index:end_index + 1].strip()
                # Skip empty or invalid blocks
                if json_object.startswith("{") and json_object.endswith("}"):
                    json_objects.append(json.loads(json_object))
                # Move the start index for the next search
                start_index = end_index + 1
            else:
                break
    except json.JSONDecodeError as e:
        print("Error parsing JSON:", e)
    
    return transform_questions(json_objects)

def generate_math_questions(context,q):
    """Generates math questions based on the given context."""
    prompt = ChatPromptTemplate.from_template("""

    <context>
    {context}
    </context>

    You are a Question answering machine. You will just respond with questions and nothing else. I want you to generate {q} Maths questions based only on the provided context. 
    If there are any questions in the context ,complete them with your creativity and reframe them in a proper way and give me the questions with answer. 
    Also, if you are generating questions then try to generate questions similar to the questions provided in the context.
    Give the response in following format - 
    {{
      "question": "question statement",
      "options":[a,b,c,d] // give all the options based on the question in a array of strings. Make sure that answer is one of them. 
      "answer": "answer", // the answer should only be the correct option , no need to give any kind of explanation or anything.
      "toughness": toughness value ranging from 1 to 10 for elementary level topics, 11 to 20 for secondary level topics,21 to 30 for high school level topics, 31 to 40 for graduate level topics
      "topic": "topic name", // the topic name should only be strictly only one of these Set Theory and Relations, Logic and Proofs, Number Theory, Algebra, Linear Algebra, Calculus, Differential Equations, Real Analysis, Probability and Statistics, Discrete Mathematics, Vector Calculus, Multivariable Calculus, Fourier and Laplace Transforms, Mathematical Optimization.
    }}
    .
    .
    .
    in this way
    Just give strictly according to structure, don't write anything else , as I want to copy that directly and give it to another agent.
    please stick to the defined structure, don't write anything else which will distort the structure.
    Dont give me latex format give me in json only.


    """)

    # Generate questions using Ollama
    llm = Ollama(model="llama3.2")
    response = llm(prompt.format(context=context, q=q))
    return response

UPLOAD_DIR = Path("uploaded_files")
UPLOAD_DIR.mkdir(exist_ok=True)

# Utility function to save the file
def save_file(file: UploadFile, save_path: str):
    try:
        with open(save_path, "wb") as buffer:
            buffer.write(file.file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

@genRouter.post("/rag")
async def upload_files(files: list[UploadFile],q: int = Form(...)):
    print(files)
    saved_files = []
    for file in files:
        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(str(file_path))

    # Call the processing function with the file path
    text=extract_text_from_pdf(file_path)
    possible_questions=extract_math_questions(text)
    questions = generate_math_questions(possible_questions,q)
    clean_questions = clean_json(questions)
    store_text_in_qdrant(questions,COLLECTION_NAME)
    output_file_path = Path("adaptive_quiz\q.json")
    output_file_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    
    # Save clean_questions to the JSON file
    try:
        with output_file_path.open("w", encoding="utf-8") as file:
            json.dump(clean_questions, file, indent=4)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving to JSON file: {str(e)}")
    return {

        "message": "Questions generated succesfully",
        "processing_result": clean_questions,
    }


# @genRouter.post("/api/v1/quiz/rag")
# async def upload_files(files: list[UploadFile],q: int = Form(...)):
    
#     return {
        
#         "message": "Questions generated succesfully",
#         "processing_result": [
#     {
#         "id": 1,
#         "question": "Let S = {1, 2, 3,...,10}. Suppose M is the set of all the subsets of S, then the relation R = {(A, B) : A ∩ B ≠ φ ; A, B ∈ M} is :",
#         "options": [
#             "D. symmetric only",
#             "994",
#             "7",
#             "198"
#         ],
#         "answer": "D. symmetric only",
#         "toughness": 34.56
#     },
#     {
#         "id": 2,
#         "question": "Let R be a relation on Z × Z defined by (a, b) R (c, d) if and only if ad - bc is divisible by 5 . Then R is",
#         "options": [
#             "203",
#             "196",
#             "708",
#             "A. Reflexive and symmetric but not transitive"
#         ],
#         "answer": "A. Reflexive and symmetric but not transitive",
#         "toughness": 45.22
#     },
#     {
#         "id": 3,
#         "question": "If R is the smallest equivalence relation on the set {1, 2, 3, 4} such that {(1, 2), (1, 3)} ⊂ R, then the number of elements in R is",
#         "options": [
#             "A. 10",
#             "141",
#             "575",
#             "265"
#         ],
#         "answer": "A. 10",
#         "toughness": 42.78
#     },
#     {
#         "id": 4,
#         "question": "A group of 40 students appeared in an examination of 3 subjects - Mathematics, Physics & Chemistry. It was found that all students passed in at least one of the subjects, 20 students passed in Mathematics, 25 students passed in Physics, 16 students passed in Chemistry, at most 11 students passed in both Mathematics and Physics, at most 15 students passed in both Physics and Chemistry, at most 15 students passed in both Mathematics and Chemistry. The maximum number of students passed in all the three subjects is__",
#         "options": [
#             "216",
#             "10",
#             "355",
#             "707"
#         ],
#         "answer": "10",
#         "toughness": 46.11
#     },
#     {
#         "id": 5,
#         "question": "The number of symmetric relations defined on the set {1, 2, 3, 4} which are not reflexive is__",
#         "options": [
#             "960",
#             "869",
#             "974",
#             "438"
#         ],
#         "answer": "960",
#         "toughness": 57.35
#     }]
#     }

    

@genRouter.post("/yt")
async def getlink(link:str = Form(...),q: int = Form(...)):
    text=extract_youtube_subtitles(link)
    possible_questions=extract_math_questions(text)
    questions = generate_math_questions(possible_questions,q)
    clean_questions = clean_json(questions)
    store_text_in_qdrant(questions,COLLECTION_NAME)
    output_file_path = Path("adaptive_quiz\q.json")
    output_file_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    
    # Save clean_questions to the JSON file
    try:
        with output_file_path.open("w", encoding="utf-8") as file:
            json.dump(clean_questions, file, indent=4)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving to JSON file: {str(e)}")

    return {
        "message": "subtitles extracted succesfully",
        "processing_result": clean_questions,
    }
    
    
def transform_questions(questions):
    """
    Transform the questions into the desired format, including generating options.
    """
    a=0
    transformed_questions = []
    for question in questions:
        correct_answer = question["answer"]

        transformed_questions.append({
            "id": a,
            "question": question["question"],
            "options": question["options"],
            "answer": question["answer"],
            "toughness": question["toughness"]
        })
        a+=1

    return transformed_questions


@genRouter.post("/text")
async def gettext(text:str = Form(...),q: int = Form(...)):
    possible_questions=extract_math_questions(text)
    questions = generate_math_questions(possible_questions,q)
    clean_questions = clean_json(questions)
        # Define the file path for saving the JSON
    output_file_path = Path("adaptive_quiz\q.json")
    output_file_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    
    # Save clean_questions to the JSON file
    try:
        with output_file_path.open("w", encoding="utf-8") as file:
            json.dump(clean_questions, file, indent=4)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving to JSON file: {str(e)}")
    return {
        "message": "questions fetched succesfully",
        "processing_result": clean_questions,
    }



class ChatRequest(BaseModel):
    message: str
    
def chat(text):
    prompt = ChatPromptTemplate.from_template(
        """
        {text}
        """
    )
    llm = Ollama(model="llama3.2")
    response = llm(prompt.format(text=text))
    return response

@genRouter.post("/chat")
async def get_text(request: ChatRequest):
    response = chat(request.message)
    return {
        "reply": response
    }
    

def generate_flashcards(context,q):
    """Generates flash cards content based on the given context."""
    prompt = ChatPromptTemplate.from_template("""

    <context>
    {context}
    </context>

    You are a flashcard generator machine. You will just generate {q} questions and answer pairs, which will be useful for revising content of the context.
    give the response in the following format - 
    {{
      "question": "question statement",
      "answer": "answer", 
      "question": "question statement"
      "answer": "answer"
      .
      .
      .

    }}
    .
    .
    .
    in this way.
    As you are just a machine for flashcard generation,  just give strictly according to structure, don't write anything else, as I want to copy that directly and give it to another agent.
    please stick to the defined structure, don't write anything else which will distort the structure.
    Also, generate generate {q} questions , neither more than that nor less than that.
    Dont give me latex format give me in json only.


    """)

    # Generate questions using Ollama
    llm = Ollama(model="llama3.2")
    response = llm(prompt.format(context=context, q=q))
    return response

@genRouter.post("/flashcard")
async def upload_files(files:list[UploadFile],q:int=Form(...)):
    saved_files = []
    for file in files:
        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(str(file_path))
    text=extract_text_from_pdf(file_path)
    content=generate_flashcards(text,q)
    return {
        "message": "content generated succesfully",
        "processing_result": content,
    }
