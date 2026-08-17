# Use the official Python 3.12 image as the base.
# "slim" is a smaller version with fewer preinstalled OS packages.
FROM python:3.12-slim

# Prevent Python from creating .pyc bytecode files.
# This keeps the container filesystem a little cleaner.
ENV PYTHONDONTWRITEBYTECODE=1

# Force Python to output logs directly without buffering.
# Helpful in Docker so logs appear immediately in the terminal.
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container to /app.
# Future commands like COPY, RUN, and CMD will use this directory.
WORKDIR /app

# Update Debian package lists, install build tools, then clean up.
# build-essential includes tools like gcc and make, which some Python
# packages need in order to compile native extensions during pip install.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements.txt first.
# This helps Docker cache dependency installation so rebuilds are faster
# when application code changes but dependencies do not.
COPY requirements.txt .

# Upgrade pip, then install Python dependencies from requirements.txt.
# --no-cache-dir avoids storing pip's download cache, which keeps the image smaller.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container.
COPY . .

# Document that the container listens on port 8000.
# This does not publish the port by itself; Docker Compose or docker run -p does that.
EXPOSE 8000

# Default command to start the FastAPI app with Uvicorn.
# app.main:app means:
# - look in the app/ package
# - find main.py
# - use the FastAPI instance named "app"
# 0.0.0.0 makes the app reachable from outside the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]