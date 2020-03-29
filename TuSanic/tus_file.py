import uuid
from pony.orm import Database, Optional, Required, PrimaryKey, db_session, Json

db = Database()


class TusFile(db.Entity):
    fid = PrimaryKey(uuid.UUID, default=uuid.uuid4)
    filename = Required(str)
    file_size = Required(int)
    offset = Required(int, default=0)
    metadata = Required(Json, default='{}')


db.bind("sqlite", ":memory:", create_db=True)
db.generate_mapping(create_tables=True)
