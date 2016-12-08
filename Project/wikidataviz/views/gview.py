from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from rdflib import Namespace, RDF, RDFS, term
from rdflib.exceptions import UniquenessError
import networkx
import rdflib

wikibase = Namespace('http://wikiba.se/ontology-beta#')
wd = Namespace('https://www.wikidata.org/entity/')
schema = Namespace('http://schema.org/')
wdata = Namespace('https://www.wikidata.org/wiki/Special:EntityData/')


def extract_literal_value(node):
    t, l = node
    return l.value


class GraphView(Resource):
    def __init__(self):
        self.parser = RequestParser()
        self.parser.add_argument('id', type=str, required=True)

    @staticmethod
    def gen_model(wkid):
        g = rdflib.Graph()
        g.load('https://www.wikidata.org/entity/' + wkid)

        vg = networkx.Graph()

        ret = ''

        entity = g.value(subject=wdata[wkid], predicate=schema.about)
        label = g.preferredLabel(entity, lang='en',
                                 labelProperties=(RDFS.label,))
        label = extract_literal_value(label[0])
        ret += 'RDF document about {}\n'.format(label)

        vg.add_node(label)

        for prop, p, o in g.triples((None, RDF.type, wikibase.Property)):
            dclaim = g.value(subject=prop, predicate=wikibase.directClaim)
            label_p = g.preferredLabel(prop, lang='en',
                                       labelProperties=(RDFS.label,))

            try:
                value = g.value(subject=entity, predicate=dclaim, any=False)

                if not value:
                    continue

                if type(value) != term.Literal:
                    label_v = g.preferredLabel(value, lang='en',
                                               labelProperties=(RDFS.label,))

                    if len(label_v) > 0:
                        label_v = extract_literal_value(label_v[0])
                    else:
                        label_v = None
                else:
                    label_v = str(value)

                vg.add_node(label_v)
                vg.add_edge(label, label_v)

                ret += '{} {}\n'.format(label_p, label_v)

            except UniquenessError:
                for s, p, value in g.triples((entity, dclaim, None)):

                    if type(value) != term.Literal:
                        label_v = g.preferredLabel(value, lang='en',
                                                   labelProperties=(
                                                       RDFS.label,))

                        if len(label_v) > 0:
                            label_v = extract_literal_value(label_v[0])
                        else:
                            label_v = None
                    else:
                        label_v = str(value)

                    vg.add_node(label_v)
                    vg.add_edge(label, label_v)

                    ret += '{} {}\n'.format(label_p, label_v)

        return ret

    def get(self):
        args = self.parser.parse_args()
        id = args['id']
        return GraphView.gen_model(id)
