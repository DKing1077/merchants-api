def get_created_at(db, table, id):
    created_at = db.query(table.created_at).filter(table.id == id).scalar()
    return created_at


def get_updated_at(db, table, id):
    updated_at = db.query(table.updated_at).filter(table.id == id).scalar()
    return updated_at


