from .app import app
from .routes.users import bp as users_bp
from .routes.roles import bp as roles_bp
from .routes.categorias import bp as categorias_bp
from .routes.projects import bp as projects_bp

# Register new blueprints
app.register_blueprint(users_bp)
app.register_blueprint(roles_bp)
app.register_blueprint(categorias_bp)
app.register_blueprint(projects_bp)

# Import legacy routes to maintain compatibility
from . import legacy

if __name__ == '__main__':
    app.run()
