FROM python:3.13-slim

# install git
RUN apt-get update && apt-get install -y git

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

CMD ["python", "bot.py"]
