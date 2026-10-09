FROM python:3.10-slim

WORKDIR /app

# Nuqul ka samee requirements.txt oo rakib libraries-ka
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Nuqul ka samee dhammaan faylasha kale
COPY . .

# Port-ka u beddel 8000 (waa kan Koyeb caadiga u ah)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
