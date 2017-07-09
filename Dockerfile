FROM python:3.6-slim

COPY ./requirements.txt ./

# Install dependenceis
RUN apt-get -y update && \
    apt-get -y install gcc groff && \
    pip install -r requirements.txt && \
    apt-get -y purge gcc && \
    apt-get -y autoremove

# Make the shell script executable
COPY ./run.sh ./
RUN chmod u+rwx run.sh

# Add the current version of discord_quote_bot
COPY ./discord_quote ./discord_quote

# Run the shell file
CMD ["./run.sh"]
