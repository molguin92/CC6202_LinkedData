from flask import Flask
from flask import render_template
from flask_restful import Api

app = Flask(__name__)
api = Api(app)

from wikidataviz.views.gview import GraphView, InfoView

api.add_resource(GraphView, '/entity')
api.add_resource(InfoView, '/info')


@app.route('/<string:qid>')
def index(qid):
    return render_template('index.html', data=qid)


if __name__ == '__main__':
    app.run()
