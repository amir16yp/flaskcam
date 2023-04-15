# Base image
FROM python:3.9-slim-buster

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app code
COPY . .

# Set the username and password as environment variables
ENV FLASKCAM_USERNAME=""
ENV FLASKCAM_PASSWORD=""

# Expose the port used by Gunicorn
EXPOSE 8000

# Start Gunicorn to run the Flask app
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "flaskcamera:app"]
