from flask import Blueprint

bp = Blueprint('core', __name__, template_folder='templates', static_folder='static')
from src.core import routes
