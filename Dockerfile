FROM python:3.6-slim

ADD ./* ./
ADD ../discord_quote ./

RUN apt-get -y update && \
    apt-get -y install gcc groff && \
    pip install -r requirements.txt && \
    apt-get -y purge gcc && \
    apt-get -y autoremove

RUN chmod u+rwx run.sh

CMD ["./run.sh"]
