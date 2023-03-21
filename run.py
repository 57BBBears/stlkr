from app import create_app, db
from app.core.models import Check, DataFrame

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Check': Check, 'DataFrame': DataFrame}

