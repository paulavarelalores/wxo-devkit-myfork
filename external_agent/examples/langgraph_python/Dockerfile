FROM python:3.11-slim

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your FastAPI app & code
COPY . .

# Launch Uvicorn on port 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
