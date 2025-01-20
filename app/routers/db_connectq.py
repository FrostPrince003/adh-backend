import mysql.connector
import json
import random


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "rcasdksK@1",
    "database": "math_quiz_db",
    "port" : 3306
}

def create_connection():
    """
    Create a database connection.
    """
    return mysql.connector.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"]
    )

def fetch_questions_by_topics(topics):
    """
    Fetch questions from the database for the provided topics.
    """
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT q.id, q.question, q.answer, q.toughness, GROUP_CONCAT(t.name) AS topics
        FROM questions q
        INNER JOIN question_topics qt ON q.id = qt.question_id
        INNER JOIN topics t ON qt.topic_id = t.id
        WHERE t.name IN (%s)
        GROUP BY q.id
    """
    placeholders = ', '.join(['%s'] * len(topics))
    query = query % placeholders

    cursor.execute(query, topics)
    results = cursor.fetchall()

    conn.close()
    return results


def generate_random_options(correct_answer):
    """
    Generate three random incorrect options while ensuring no duplicates.
    """
    incorrect_answers = set()
    while len(incorrect_answers) < 3:
        rand_int = random.randint(1, 1000)
        if str(rand_int) != str(correct_answer):
            incorrect_answers.add(str(rand_int))
    return list(incorrect_answers)


def transform_questions(questions):
    """
    Transform the questions into the desired format, including generating options.
    """
    transformed_questions = []
    for question in questions:
        correct_answer = question["answer"]

        # Generate incorrect options
        incorrect_answers = generate_random_options(correct_answer)

        # Combine and shuffle options
        options = incorrect_answers + [str(correct_answer)]
        random.shuffle(options)

        # Add the question in the required format
        transformed_questions.append({
            "id": question["id"],
            "question": question["question"],
            "options": options,
            "answer": str(correct_answer),
            "toughness": float(question["toughness"])
        })

    return transformed_questions


def save_questions_to_json(questions, file_path):
    """
    Save the transformed questions to a JSON file.
    """
    with open(file_path, "w") as file:
        json.dump(questions, file,ensure_ascii=False, indent=4)


def fetch_and_transform_questions(topics, file_path):
    """
    Fetch questions, transform them, and dump to a JSON file.
    """
    questions = fetch_questions_by_topics(topics)

    if not questions:
        return []

    transformed_questions = transform_questions(questions)

    save_questions_to_json(transformed_questions, file_path)

    return transformed_questions