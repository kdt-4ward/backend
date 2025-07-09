# Fetching the latest python image
FROM python:3.12-slim

# Declaring env
# ENV NODE_ENV production

# Setting up the work directory
WORKDIR /backend

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copying all the files in our project
COPY . .

# Expose the port on which the app will be running (3000 is the default that `serve` uses)
EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]