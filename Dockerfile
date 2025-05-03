FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "skolmaten:create_app()"]
