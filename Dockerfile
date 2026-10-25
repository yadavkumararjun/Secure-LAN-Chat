FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing .pyc and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOST="0.0.0.0"
ENV PORT=8000

# Install dependencies
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend application, pre-built frontend distribution, and server runner
COPY backend/ /app/backend/
COPY frontend/dist/ /app/frontend/dist/
COPY run_server.py /app/

# Ensure storage directories exist
RUN mkdir -p /app/backend/storage/uploads

EXPOSE 8000

CMD ["python", "run_server.py"]
