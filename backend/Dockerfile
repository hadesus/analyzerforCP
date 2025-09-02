# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir: Disables the cache which is useful in image builds to keep the layer size down
# --trusted-host pypi.python.org: Can help in some network environments
RUN pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt

# Copy the rest of the application's code to the working directory
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable to ensure python prints things without buffering
ENV PYTHONUNBUFFERED 1

# Run uvicorn server
# The host 0.0.0.0 is specified to accept connections from any IP address (necessary for Docker)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
