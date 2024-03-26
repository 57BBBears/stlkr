from flask import Blueprint

bp = Blueprint('pages', __name__)
from src.pages import routes