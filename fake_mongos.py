from gevent import monkey; monkey.patch_all()
import pymongo
import hashlib
import logging
from pymongo import MongoClient
from bottle import route, run, response
from secrets import *


class FakeMongosObjectReader():
    def __init__(self, doc, dbs_chunks):
        '''
        doc is a fs.files document:
        > db["fs.files"].find().limit(1)
        { "_id" : ObjectId("6272cec6ecd154d4c67ff9d6"),
        "uploadDate" : ISODate("2022-05-04T19:06:48.415Z"),
        "length" : NumberLong(50000000),
        "chunkSize" : 261120,
        "md5" : "b8059d369b4f691836d810b48901ed76" }
        '''
        self.doc = doc
        self.dbs_chunks = dbs_chunks
        self.filename = doc.get('filename')
        self.md5 = doc.get('md5')
        self._id = doc['_id']
        self.length = doc['length']
        self.chunk_size = doc['chunkSize']


    def delete(self):
        for db_chunk in self.dbs_chunks:
            cursor = db_chunk['fs.chunks'].delete_many({'files_id': self._id})


    def read(self):
        '''
        > db["fs.chunks"].find({"files_id": ObjectId("6272cec6ecd154d4c67ff9d6")},{"data": 0})
        { "_id" : ObjectId("6272cec8ecd154d4c67ffa91"),
        "n" : 186,
        "files_id" : ObjectId("6272cec6ecd154d4c67ff9d6") }
        (data key contains a mongo binary object)
        '''
        chunk_docs = []
        for db_chunk in self.dbs_chunks:
            cursor = db_chunk['fs.chunks'].find({'files_id': self._id})
            for doc in cursor:
                chunk_docs.append(doc)
        chunk_docs.sort(key=lambda x: x['n'])
        binary = bytes(b'')
        for chunk_doc in chunk_docs:
            binary += chunk_doc['data']
        assert hashlib.md5(binary).hexdigest() == self.md5
        # returns the binary
        return binary

class FakeMongos():
    def __init__(self, files_host, shards):
        '''
        files_host is a tuple (host, port) of the mongo
        host where DB_files's fs.files collection is.
        shards is an array of (host, port) elements.
        '''
        client_fs = MongoClient(files_host[0], files_host[1])
        self.db_files = client_fs['DB_files']
        self.dbs_chunks = []
        for shard in shards:
            tmp_client = MongoClient(shard[0], shard[1])
            self.dbs_chunks.append(tmp_client['DB_files'])

    def count_chunks(self):
        total = 0
        for db_chunk in self.dbs_chunks:
            tmp_count = db_chunk['fs.chunks'].estimated_document_count()
            logging.debug('tmp_count=%s' % tmp_count)
            total += tmp_count
        return total
    
    def count_files(self):
        return db_files['fs.files'].estimated_document_count()

    def put(self, data):
        raise NotImplemented

    def delete(self, params_to_search):
        if not isinstance(params_to_search, dict):
            raise ValueError("params_to_search not a dict. %s" % type(params_to_search))
        if params_to_search.get('md5') is None and params_to_search.get('filename') is None:
            raise ValueError("params_to_search invalid. %s" % params_to_search)
        if params_to_search.get('md5') is not None and len(params_to_search['md5']) != 32:
            raise ValueError("Invalid md5 in params_to_search")
        doc = self.db_files['fs.files'].find_one(params_to_search)
        if doc is None:
            return None
        fake_mongos_reader = FakeMongosObjectReader(doc, self.dbs_chunks)
        fake_mongos_reader.delete()
        self.db_files['fs.files'].delete_one({'_id': doc['_id']})

    def find_one(self, params_to_search):
        doc = self.db_files['fs.files'].find_one(params_to_search)
        if doc is None:
            return None
        fake_mongos_reader = FakeMongosObjectReader(doc, self.dbs_chunks)
        return fake_mongos_reader
        # should return an object with read() method


@route('/get/sha1/<sha1>')
def get_sha1(sha1):
    binary = fake_mongos.find_one({'filename': sha1})
    if binary is None:
        response.status = 404
        return ''
    else:
        binary = binary.read()
        assert hashlib.sha1(binary).hexdigest() == sha1
        return binary


if __name__ == '__main__':
    fake_mongos = FakeMongos(fs_files_db, chunk_shards)
    run(host='0.0.0.0', port=4321, server='gevent')
