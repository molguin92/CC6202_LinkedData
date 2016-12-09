import threading

import networkx
import rdflib
from flask_restful import Resource
from flask_restful.reqparse import RequestParser
from networkx.readwrite.json_graph import node_link_data
from networkx import set_node_attributes
from rdflib import Namespace, RDF
from rdflib.exceptions import UniquenessError
import requests

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
        """
        This functions populates the network graph for a specific RDF entity in
        a recursive manner.

        :param vg: The NetworkX graph to populate.
        :param uriref: The rdf entity which is to be considered as the root for
        this level.
        :param depth: How many recursive steps to perform.
        :return:
        """

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
                    if depth - 1 > 0:
                        t = threading.Thread(
                            target=self.populate_network_graph,
                            args=(vg, value, depth - 1))
                        t.start()
                        threads.append(t)
                    else:
                        with self.lock:
                            vg.add_node(value)

                    with self.lock:
                        vg.add_edge(uriref, value)

            except UniquenessError:
                for s, p, value in g.triples((uriref, dclaim, None)):

                    if value in g.subjects(RDF.type, wikibase.Item):
                        if depth - 1 > 0:
                            t = threading.Thread(
                                target=self.populate_network_graph,
                                args=(vg, value, depth - 1))
                            t.start()
                            threads.append(t)
                        else:
                            with self.lock:
                                vg.add_node(value)

                        with self.lock:
                            vg.add_edge(uriref, value)

        for t in threads:
            t.join()

    def get_label(self, node, label_dict):
        q_id = node.split('/')[-1]
        rv = requests.get(node, headers={'Accept': 'application/json'})
        info = rv.json()
        label = info.get('entities', {}) \
            .get(q_id, {}).get('labels', {}) \
            .get('en', {}).get('value', None)

        with self.lock:
            label_dict[node] = label

    def get_node_labels(self, vgraph):

        nodes = vgraph.nodes()
        nodes_labels = {}
        threads = []

        for node in nodes:
            t = threading.Thread(target=self.get_label, args=(node, nodes_labels))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        set_node_attributes(vgraph, 'label', nodes_labels)

    def get(self):
        args = self.parser.parse_args()
        id = args['id']

        vgraph = networkx.Graph()
        self.populate_network_graph(vgraph, wd[id])
        self.get_node_labels(vgraph)

        return node_link_data(vgraph)


class InfoView(Resource):
    def __init__(self):
        self.parser = RequestParser()
        self.parser.add_argument('url', type=str, required=True)

    def get(self):
        args = self.parser.parse_args()
        url = args['url']

        us = url.split('/')
        id = us[len(us) - 1]

        rv = requests.get(url, headers={'Accept': 'application/json'})
        info = rv.json()

        return info.get('entities', {}).get(id, {}).get('labels', {}).get('en',
                                                                          {}).get(
            'value', None)
