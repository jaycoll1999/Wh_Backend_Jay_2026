import requests
import sys, os
sys.path.append(os.getcwd())
from core.security import create_access_token

token = create_access_token(data={"sub": "dbccae19-12de-457f-a2f3-22c5ca01080b", "role": "reseller"})
res = requests.get('http://localhost:8000/api/busi_users/reseller/dbccae19-12de-457f-a2f3-22c5ca01080b', headers={"Authorization": f"Bearer {token}"})
print(res.json())
