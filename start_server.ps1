$env:PYTHONPATH="C:\Users\Administrator\Downloads\RAG BASED CHATBOT\Fleet-AI-Chatbot"
Set-Location "C:\Users\Administrator\Downloads\RAG BASED CHATBOT\Fleet-AI-Chatbot"
Start-Process python -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port","3001","--workers","1"
