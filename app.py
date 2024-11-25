from src import create_app
from src.models import db

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {"db": db}
