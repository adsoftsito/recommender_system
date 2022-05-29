FROM python:3.7.4-alpine3.10
COPY . /app
WORKDIR /app
RUN pip3 install -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host=0.0.0.0", "--port=8000", "--reload"]
