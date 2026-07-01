import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_cors import CORS
from api.routes import api_bp
from api.auth_routes import auth_bp
from api.strategy_routes import strategy_bp
from api.backtest_v2_routes import backtest_v2_bp
from api.subscription_routes import subscription_bp
from api.paper_trading_routes import paper_bp
from api.journal_routes import journal_bp
from api.notification_routes import notification_bp
from api.alerts_routes import alerts_bp
from api.marketplace_routes import marketplace_bp
from api.optimizer_routes import optimizer_bp
from api.forward_test_routes import forward_bp
from core.db_storage import init_data_files
from core.database import init_db
from dotenv import load_dotenv

load_dotenv()


def create_app() -> Flask:
    init_db()
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(strategy_bp, url_prefix='/api/strategies')
    app.register_blueprint(backtest_v2_bp, url_prefix='/api/v2')
    app.register_blueprint(subscription_bp,  url_prefix='/api/subscriptions')
    app.register_blueprint(paper_bp,         url_prefix='/api/paper')
    app.register_blueprint(journal_bp,       url_prefix='/api/journal')
    app.register_blueprint(notification_bp,  url_prefix='/api/notifications')
    app.register_blueprint(alerts_bp,        url_prefix='/api/alerts')
    app.register_blueprint(marketplace_bp,   url_prefix='/api/marketplace')
    app.register_blueprint(optimizer_bp,     url_prefix='/api/optimizer')
    app.register_blueprint(forward_bp,       url_prefix='/api/forward')

    @app.errorhandler(404)
    def not_found(e):
        from flask import jsonify
        return jsonify({'error': 'Endpoint not found'}), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import jsonify
        return jsonify({'error': 'Internal server error'}), 500

    return app


if __name__ == '__main__':
    init_data_files()
    init_db()
    app = create_app()
    port = int(os.getenv('FLASK_PORT', 8001))
    print(f"[API] Flask server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
