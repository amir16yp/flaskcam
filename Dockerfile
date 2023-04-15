# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Set the environment variable for Gunicorn to use
ENV APP_MODULE=flaskcamera:app

# Expose port 8000 for the application
EXPOSE 8000

# Run the command to start Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "flaskcamera:app"]
