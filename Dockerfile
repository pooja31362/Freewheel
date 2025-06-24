# Use official Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies
RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends \
    gcc \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 5000

# Run Django app
# CMD ["python", "manage.py", "runserver", "0.0.0.0:5000"]
CMD ["gunicorn", "Support_Portal.wsgi:application", "--bind", "0.0.0.0:5000"]
# CMD ["gunicorn", "Support_Portal.wsgi:application", "--bind", "127.0.0.1:5000"]
