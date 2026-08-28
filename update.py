import os
import subprocess
import sqlite3


def run_command(command: str, cwd: str = None) -> None:
    """Executes a shell command and prints the output."""
    print(f"\n---> Running: {command}")
    subprocess.run(command, shell=True, check=True, cwd=cwd)


def get_current_git_tag() -> str:
    """Retrieves the most recent Git tag before any updates."""
    try:
        tag = subprocess.check_output("git describe --tags --abbrev=0", shell=True, text=True).strip()
        return tag
    except subprocess.CalledProcessError:
        # Fallback if no tags exist in the repository yet
        return "v0.0.0"


def check_and_backup_database(old_tag: str) -> None:
    """Compares current DB schema with the new code schema and backs up if different."""
    db_path = os.path.join("backend", "skate_contest.db")
    temp_db_path = os.path.join("backend", "temp_schema_check.db")

    if not os.path.exists(db_path):
        print("\n---> No existing database found. Fresh start.")
        return

    # 1. Read the schema of the existing database
    conn_old = sqlite3.connect(db_path)
    cursor_old = conn_old.cursor()
    cursor_old.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    old_schema = cursor_old.fetchall()
    conn_old.close()

    # 2. Generate the new expected schema using the updated db_manager.py
    inline_script = f"""
import sys
sys.path.append('backend')
from db_manager import setup_database
setup_database('{os.path.basename(temp_db_path)}')
"""
    # Run the import in a subprocess to ensure it uses the newly pulled code
    subprocess.run(["python", "-c", inline_script], check=True, cwd="backend")

    # 3. Read the schema of the newly generated temp database
    conn_new = sqlite3.connect(temp_db_path)
    cursor_new = conn_new.cursor()
    cursor_new.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    new_schema = cursor_new.fetchall()
    conn_new.close()

    # 4. Clean up the temporary database
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)

    # 5. Compare schemas and rename if changes are detected
    if old_schema != new_schema:
        backup_name = f"skate_contest_{old_tag}.db"
        backup_path = os.path.join("backend", backup_name)
        print(f"\n---> [WARNING] Database structure changed!")
        print(f"---> Backing up old database to: {backup_name}")
        os.rename(db_path, backup_path)
    else:
        print("\n---> Database structure is identical. No backup needed.")


def main() -> None:
    print("=== SKATE CONTEST UPDATE SCRIPT ===")

    # Step 1: Capture the old tag BEFORE pulling new changes
    old_tag = get_current_git_tag()
    print(f"Current recorded version: {old_tag}")

    # Step 2: Git updates
    try:
        run_command("git fetch")
        run_command("git rebase")
    except subprocess.CalledProcessError:
        print("Git operation failed. Please check your working tree or network.")
        return

    # Step 3: Update and build Frontend
    if os.path.exists("frontend"):
        run_command("npm install", cwd="frontend")
        run_command("npm run build", cwd="frontend")
    else:
        print("Frontend directory not found. Skipping UI build.")

    # Step 4: Install/Update Python Backend dependencies
    if os.path.exists("backend"):
        run_command("python -m pip install fastapi uvicorn pydantic openpyxl python-multipart websockets fpdf2",
                    cwd="backend")
    else:
        print("Backend directory not found. Skipping pip install.")

    # Step 5: Check Database Schema and Backup if necessary
    if os.path.exists("backend"):
        check_and_backup_database(old_tag)

    print("\n=== UPDATE COMPLETE ===")
    print("You can now safely run the server.")


if __name__ == "__main__":
    main()
