# Use an official Python
FROM python:3.9-slim

# Set the working directory the on the container 
WORKDIR /app 

# Copy the requirements file first
COPY src/blackjack-app/requirements.txt /app/

RUN pip install --upgrade pip

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# install packages to run the app
RUN apt-get update -y && \
    apt-get install -y curl && \
    apt-get install -y iputils-ping && \
    apt install net-tools -y 
    
# Copy the rest of the application files
COPY src/blackjack-app /app
 
# Make port 80 available to the world outside this container
EXPOSE 80

# copy the file main.py
COPY src/blackjack-app/main.py /app

# Run app.py when the container launches
CMD ["python" , "main.py"]