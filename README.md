conda create -n faceweb python=3.10 -y

conda activate faceweb


pip install -r requirements.txt



#--------------------------------
backend: uvicorn app:app --host 0.0.0.0 --port 8000
frontend: ngrok http 8000 
