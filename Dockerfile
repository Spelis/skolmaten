FROM python:3.13-slim

ENV TZ=Europe/Stockholm
# Create non-root user early and set permissions properly
RUN adduser --disabled-password --gecos "" pyuser

# Set working directory and permissions
WORKDIR /app
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code after installing deps
COPY . .

# Set ownership last for caching efficiency
RUN chown -R pyuser:pyuser /app

USER pyuser

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "skolmaten:create_app()"]

