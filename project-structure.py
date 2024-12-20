import os

# Define the directory structure
project_structure = {
    "app": [
        "main.py",
        "config.py",
        "database.py",
        "dependencies.py",
        {
            "models": ["__init__.py", "user.py", "quiz.py"],
            "schemas": ["__init__.py", "user.py", "quiz.py"],
            "routers": ["__init__.py", "auth.py", "quiz.py"],
            "services": ["__init__.py", "auth_service.py", "quiz_service.py"],
            "utils": ["__init__.py", "hashing.py", "token.py"],
        },
    ],
    "tests": ["__init__.py", "test_auth.py", "test_quiz.py"],
    "alembic": ["env.py", "README", "script.py.mako", {"versions": []}],
    "": ["requirements.txt", ".env", "Dockerfile", "docker-compose.yml", "README.md"],
}

# Function to create the directory structure
def create_structure(base_dir, structure):
    for key, value in (structure.items() if isinstance(structure, dict) else enumerate(structure)):
        path = os.path.join(base_dir, key if isinstance(key, str) else value)
        if isinstance(value, dict):
            os.makedirs(path, exist_ok=True)
            create_structure(path, value)
        elif isinstance(value, list):
            os.makedirs(path, exist_ok=True)
            for file in value:
                if isinstance(file, str):
                    with open(os.path.join(path, file), "w") as f:
                        f.write("")
                elif isinstance(file, dict):
                    create_structure(path, file)
        else:
            with open(path, "w") as f:
                f.write("")

# Base directory for the project
base_dir = "."

# Create the project structure
create_structure(base_dir, project_structure)

print(f"Project structure created in '{base_dir}'.")
