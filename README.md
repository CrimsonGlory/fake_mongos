If you have a sharded GridFS cluster on MongoDB, and for some reason all the mongo config containers explode, the information of which data chunks were in which shards is lost, and mongos (which handles the queries) won't work. But the data is still there, so you can query each shard seperately and merge the chunks and recover the data. (Tested with Mongo 3.2). The code has a small API to retrieve, and delete files. So you can have it working as a "mongos" container, but it is not, so it's a fake mongos.

Edit and move the secrets.py.bak to secrets.py.
