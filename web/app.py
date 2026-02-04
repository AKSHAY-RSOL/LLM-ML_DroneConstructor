"""
DroneForge AI - Web Application
Flask-based web interface for drone design automation.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_cors import CORS
import threading
import queue
import uuid

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'droneforge-secret-key')
app.config['OUTPUT_DIR'] = os.environ.get('OUTPUT_DIR', './output')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Job storage
jobs = {}
job_queues = {}


class DesignJob:
    """Represents a design job"""
    def __init__(self, job_id: str, config: dict):
        self.id = job_id
        self.config = config
        self.status = "pending"
        self.progress = 0
        self.current_agent = ""
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.completed_at = None
        self.logs = []
    
    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "progress": self.progress,
            "current_agent": self.current_agent,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "logs": self.logs[-20:]  # Last 20 logs
        }


def run_design_job(job: DesignJob):
    """Run design job in background thread"""
    try:
        # Import here to avoid circular imports
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.core.workflow import DroneForgeWorkflow
        
        job.status = "running"
        job.progress = 5
        job.logs.append("Initializing workflow...")
        
        # Create workflow
        workflow = DroneForgeWorkflow(
            llm_provider=job.config.get("provider", "ollama"),
            model=job.config.get("model"),
            output_dir=job.config.get("output_dir", f"./output/{job.id}")
        )
        
        job.progress = 10
        job.logs.append(f"Using {job.config.get('provider')} provider")
        
        # Custom logging handler to capture agent progress
        class JobLogHandler(logging.Handler):
            def __init__(self, job_obj):
                super().__init__()
                self.job = job_obj
                self.agent_progress = {
                    "mission_analyzer": 10,
                    "frame_topology": 15,
                    "propulsion": 20,
                    "aerodynamics": 30,
                    "structural": 40,
                    "power": 50,
                    "electronics": 55,
                    "cog_analysis": 60,
                    "autonomy": 65,
                    "software": 70,
                    "wiring": 75,
                    "cad": 80,
                    "regulatory": 85,
                    "validator": 90,
                    "optimizer": 92,
                    "bom_generator": 95,
                    "documentation": 98
                }
            
            def emit(self, record):
                msg = record.getMessage()
                self.job.logs.append(msg)
                
                # Update progress based on agent
                for agent, progress in self.agent_progress.items():
                    if agent in msg.lower():
                        self.job.current_agent = agent
                        self.job.progress = progress
                        break
        
        # Add custom handler
        handler = JobLogHandler(job)
        logging.getLogger().addHandler(handler)
        
        # Run workflow
        result = workflow.run(
            mission=job.config.get("mission", ""),
            cad_detail=job.config.get("cad_detail", "basic"),
            jurisdictions=job.config.get("jurisdictions", ["india_dgca"]),
            output_dir=job.config.get("output_dir", f"./output/{job.id}")
        )
        
        # Remove handler
        logging.getLogger().removeHandler(handler)
        
        job.result = result
        job.status = "completed"
        job.progress = 100
        job.completed_at = datetime.now()
        job.logs.append("Design completed successfully!")
        
    except Exception as e:
        job.status = "failed"
        job.error = str(e)
        job.logs.append(f"Error: {str(e)}")
        logger.exception("Design job failed")


# ============================================================================
# Routes
# ============================================================================

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/providers')
def get_providers():
    """Get available LLM providers"""
    providers = [
        {
            "id": "ollama",
            "name": "Ollama (Local)",
            "description": "Free, runs locally",
            "models": ["llama3", "mistral", "codellama", "llama2"],
            "requires_key": False
        },
        {
            "id": "openai",
            "name": "OpenAI",
            "description": "GPT-4 and GPT-3.5",
            "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            "requires_key": True
        },
        {
            "id": "anthropic",
            "name": "Anthropic Claude",
            "description": "Claude 3 models",
            "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
            "requires_key": True
        },
        {
            "id": "google",
            "name": "Google Gemini",
            "description": "Gemini Pro models",
            "models": ["gemini-pro", "gemini-1.5-pro"],
            "requires_key": True
        }
    ]
    return jsonify(providers)


@app.route('/api/jurisdictions')
def get_jurisdictions():
    """Get supported jurisdictions"""
    jurisdictions = [
        {"id": "india_dgca", "name": "India - DGCA"},
        {"id": "usa_faa", "name": "USA - FAA"},
        {"id": "eu_easa", "name": "EU - EASA"}
    ]
    return jsonify(jurisdictions)


@app.route('/api/design', methods=['POST'])
def create_design():
    """Create a new design job"""
    data = request.json
    
    # Validate required fields
    if not data.get('mission'):
        return jsonify({"error": "Mission statement is required"}), 400
    
    # Create job
    job_id = str(uuid.uuid4())[:8]
    output_dir = f"./output/{job_id}"
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    config = {
        "mission": data.get('mission'),
        "provider": data.get('provider', 'ollama'),
        "model": data.get('model'),
        "cad_detail": data.get('cad_detail', 'basic'),
        "jurisdictions": data.get('jurisdictions', ['india_dgca']),
        "output_dir": output_dir
    }
    
    job = DesignJob(job_id, config)
    jobs[job_id] = job
    
    # Start background thread
    thread = threading.Thread(target=run_design_job, args=(job,))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "job_id": job_id,
        "status": "pending",
        "message": "Design job created"
    })


@app.route('/api/design/<job_id>')
def get_design_status(job_id):
    """Get design job status"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify(job.to_dict())


@app.route('/api/design/<job_id>/result')
def get_design_result(job_id):
    """Get design result"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    if job.status != "completed":
        return jsonify({"error": "Job not completed"}), 400
    
    # Load result files
    output_dir = Path(job.config.get('output_dir', f'./output/{job_id}'))
    
    result = {
        "job_id": job_id,
        "status": "completed"
    }
    
    # Load BOM
    bom_path = output_dir / "bom.json"
    if bom_path.exists():
        with open(bom_path) as f:
            result["bom"] = json.load(f)
    
    # Load build guide
    guide_path = output_dir / "build_guide.md"
    if guide_path.exists():
        with open(guide_path) as f:
            result["build_guide"] = f.read()
    
    # Load design state
    state_path = output_dir / "design_state.json"
    if state_path.exists():
        with open(state_path) as f:
            result["design_state"] = json.load(f)
    
    return jsonify(result)


@app.route('/api/design/<job_id>/download/<file_type>')
def download_file(job_id, file_type):
    """Download result file"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    output_dir = Path(job.config.get('output_dir', f'./output/{job_id}'))
    
    file_map = {
        "bom": "bom.json",
        "guide": "build_guide.md",
        "state": "design_state.json"
    }
    
    filename = file_map.get(file_type)
    if not filename:
        return jsonify({"error": "Invalid file type"}), 400
    
    file_path = output_dir / filename
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    
    return send_file(file_path, as_attachment=True)


@app.route('/api/design/<job_id>/stream')
def stream_logs(job_id):
    """Stream job logs via Server-Sent Events"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    def generate():
        last_log_count = 0
        while job.status in ["pending", "running"]:
            if len(job.logs) > last_log_count:
                for log in job.logs[last_log_count:]:
                    yield f"data: {json.dumps({'log': log, 'progress': job.progress, 'agent': job.current_agent})}\n\n"
                last_log_count = len(job.logs)
            import time
            time.sleep(0.5)
        
        # Final status
        yield f"data: {json.dumps({'status': job.status, 'progress': 100})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/jobs')
def list_jobs():
    """List all jobs"""
    job_list = [job.to_dict() for job in jobs.values()]
    job_list.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify(job_list[:50])  # Last 50 jobs


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# Main
# ============================================================================

def create_app():
    """Create and configure the Flask app"""
    return app


def run_server(host='0.0.0.0', port=5000, debug=False):
    """Run the web server"""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║             DroneForge AI - Web Interface                   ║
║                                                              ║
║   Server running at: http://{host}:{port}                     ║
║                                                              ║
║   Open your browser to start designing drones!              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)
