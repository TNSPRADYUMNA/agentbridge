FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
CMD ["sh", "-c", "python fixture.py && exec python bridge.py"]
