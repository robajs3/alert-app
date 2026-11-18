FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY static ./static
RUN useradd -m app
USER app
EXPOSE 8023
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8023", "--proxy-headers"]
