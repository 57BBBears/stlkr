from src import create_app, db
from src.models import Dataframe, Check

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Check': Check, 'DataFrame': Dataframe}

