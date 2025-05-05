## Create flat file:

python create_docs.py

## start/stop

source venv/bin/activate
gunicorn --workers 3 --bind 0.0.0.0:8899 --timeout 600 app:app

## logs
sudo journalctl -u transcription.service -n 100 --no-pager