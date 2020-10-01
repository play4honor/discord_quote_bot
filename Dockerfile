FROM python:3.8-slim-buster

COPY ./requirements.txt ./
COPY ./setup.py ./

# Copy the latest version of the bot 
COPY ./src /src
COPY ./bin /bin

# Install dependenceis
RUN apt-get -y update && \
    pip install -r requirements.txt && \
    apt-get -y autoremove

# Load package
RUN pip install -e .

# Change to working directory
WORKDIR /

# Run the shell file
CMD ["python", "src/bot/discord_quote.py"]
