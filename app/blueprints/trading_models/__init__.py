from flask import Blueprint

bp = Blueprint('trading_models', __name__,
               template_folder='../../templates/models',  # FIXED: Changed from trading_models to models
               url_prefix='/trading-models')

from . import routes