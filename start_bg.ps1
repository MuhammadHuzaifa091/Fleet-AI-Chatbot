$dir = "C:\Users\Administrator\Downloads\RAG BASED CHATBOT\Fleet-AI-Chatbot"
$env:PYTHONPATH = $dir
Set-Location $dir
python -m uvicorn app.main:app --host 0.0.0.0 --port 3000 --workers 1
