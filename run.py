from app import create_app
import os
import subprocess
import atexit

app = create_app()

celery_app = app.extensions["celery"]
app.app_context().push()

worker_process = None
beat_process = None

def start_celery():
    global worker_process, beat_process
    
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("🚀 Starting Celery Worker and Beat in the background...")
        
        worker_process = subprocess.Popen(
            ['celery', '-A', 'run.celery_app', 'worker', '--loglevel=info', '-P', 'solo']
        )
        
        beat_process = subprocess.Popen(
            ['celery', '-A', 'run.celery_app', 'beat', '--loglevel=info']
        )

def cleanup():
    print("\n🛑 Shutting down Celery processes...")
    if worker_process:
        worker_process.terminate()
        worker_process.wait()
    if beat_process:
        beat_process.terminate()
        beat_process.wait()

atexit.register(cleanup)

if __name__ == "__main__":
    start_celery()
    app.run(debug=True)