import threading

from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from rdflib import Namespace, RDF, RDFS, term
from rdflib.exceptions import UniquenessError
import networkx
import rdflib
from networkx.readwrite.json_graph import node_link_data

wikibase = Namespace('http://wikiba.se/ontology-beta#')
wd = Namespace('http://www.wikidata.org/entity/')
schema = Namespace('http://schema.org/')
wdata = Namespace('https://www.wikidata.org/wiki/Special:EntityData/')


def extract_literal_value(node):
    t, l = node
    return l.value


class GraphView(Resource):
    def __init__(self):
        self.parser = RequestParser()
        self.parser.add_argument('id', type=str, required=True)
        self.lock = threading.RLock()

    def populate_network_graph(self, vg, uriref, depth=2):

        with self.lock:
            vg.add_node(uriref)

        if depth < 1:
            return

        threads = []

        g = rdflib.Graph()
        g.load(uriref)

        for prop, p, o in g.triples((None, RDF.type, wikibase.Property)):
            dclaim = g.value(subject=prop, predicate=wikibase.directClaim)

            try:
                value = g.value(subject=uriref, predicate=dclaim, any=False)
                if not value:
                    continue

                if value in g.subjects(RDF.type, wikibase.Item):
                    t = threading.Thread(target=self.populate_network_graph,
                                         args=(vg, value, depth - 1))
                    t.start()
                    threads.append(t)

                    # vg.add_node(value)
                    with self.lock:
                        vg.add_edge(uriref, value)

            except UniquenessError:
                for s, p, value in g.triples((uriref, dclaim, None)):

                    if value in g.subjects(RDF.type, wikibase.Item):
                        t = threading.Thread(
                            target=self.populate_network_graph,
                            args=(vg, value, depth - 1))
                        t.start()
                        threads.append(t)

                        # vg.add_node(value)
                        with self.lock:
                            vg.add_edge(uriref, value)

        for t in threads:
            t.join()

    def get(self):
        args = self.parser.parse_args()
        id = args['id']

        vgraph = networkx.Graph()
        self.populate_network_graph(vgraph, wd[id])

        return node_link_data(vgraph)
