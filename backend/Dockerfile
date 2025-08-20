# Dockerfile for Video Subtitle Scraper Backend

# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend source code into the container
COPY src/ ./src/

# Set the environment variable for Flask or FastAPI
# Uncomment the appropriate line based on the framework used
# ENV FLASK_APP=src/app.py
# ENV FASTAPI_APP=src/app.py

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
# Uncomment the appropriate line based on the framework used
# CMD ["flask", "run", "--host=0.0.0.0"]
# CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]