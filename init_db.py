from app1 import app, db
import time


MAX_RETRIES = 10
RETRY_DELAY_SECONDS = 5

with app.app_context():
    for i in range(MAX_RETRIES):
        try:
            print(f"Attempt {i+1}/{MAX_RETRIES}: Creating database tables...")
            db.create_all()
            print("Database tables created successfully.")
            break  
        except Exception as e:
            print(f"Error creating tables: {e}. Retrying in {RETRY_DELAY_SECONDS} seconds...")
            time.sleep(RETRY_DELAY_SECONDS)
    else:
        print("Failed to create database tables after multiple retries. Exiting.")
        exit(1) 