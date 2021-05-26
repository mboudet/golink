from flask import (Blueprint, current_app, render_template)


view = Blueprint('view', __name__, url_prefix='/')


@view.route('/', defaults={'path': ''})
@view.route('/<path:path>')
def home(path):
    """Render the html
    """
    proxy_path = "/"
    try:
        proxy_path = current_app.config.get('PROXY_PREFIX', '/')
    except Exception:
        pass

    return render_template('index.html', proxy_path=proxy_path)
