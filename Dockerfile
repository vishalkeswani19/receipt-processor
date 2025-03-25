# Use official Python runtime as base image
FROM python:3.9-slim AS build

# Set working directory
WORKDIR /app

# Copy requirements file first
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Final stage
FROM python:3.9-slim

WORKDIR /app

# Copy only the necessary files from build stage
COPY --from=build /app /app

# Install runtime dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
CMD ["python", "app.py"]