
from risk_framework.web_api.core import app
from risk_framework.web_api.models import PriorityManagementActionsPolygonsDB

db = list(app.get_db())[0]
id = "03bf9d7f-e58e-430d-aa2b-53c260c00047"
query = db.query(PriorityManagementActionsPolygonsDB).filter(PriorityManagementActionsPolygonsDB.id == id)
existing_record = query.first()

db.delete(existing_record)
db.commit()
