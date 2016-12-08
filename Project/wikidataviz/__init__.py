from flask import Flask
from flask_restful import Api

app = Flask(__name__)
api = Api(app)

from wikidataviz.views.gview import GraphView
api.add_resource(GraphView, '/')

if __name__ == '__main__':
    app.run()
