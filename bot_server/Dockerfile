FROM python:3.9.16
WORKDIR /server
COPY requirements.txt /server
RUN pip3 install -r requirements.txt --no-cache-dir
COPY api.json /server
ENV GOOGLE_APPLICATION_CREDENTIALS="/server/api.json"
COPY stt.py /server
COPY BCP-47.txt /server
COPY greeting.txt /server
COPY server.py /server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "4222"]