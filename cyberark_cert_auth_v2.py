import os
import ssl
import json
import http.client
import urllib.parse
import sys
from dotenv import load_dotenv

load_dotenv()


def get_password(object_name, **kwargs):
    """Get password from CyberArk for specified object name."""
    
    # Config from env or kwargs
    app_id = kwargs.get('app_id') or os.getenv('AAM_APP_ID')
    safe_name = kwargs.get('safe_name') or os.getenv('AAM_SAFE')
    host = kwargs.get('host') or os.getenv('AAM_BASE_URI')
    cert_path = kwargs.get('cert_path') or os.getenv('AAM_DEMO_PATH')
    cert_password = kwargs.get('cert_password') or os.getenv('AAM_PASSPHRASE')
    
    host = host.replace('https://', '')
    
    # Build query and API path
    query = urllib.parse.quote(f"Safe={safe_name};Object={object_name}")
    api_path = f"/AIMWebService/api/Accounts?AppID={app_id}&Query={query}"
    
    # SSL context with password-protected cert
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain(certfile=cert_path, password=cert_password)
    
    # Make API call
    conn = http.client.HTTPSConnection(host, context=context)
    conn.request('GET', api_path)
    response = conn.getresponse()
    data = json.loads(response.read().decode())
    conn.close()
    
    return data.get('Content')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python cyberark_cert_auth.py <object_name1> [object_name2] ...")
        sys.exit(1)
    
    # Get passwords for all object names from command line
    object_names = sys.argv[1:]
    
    for obj_name in object_names:
        password = get_password(obj_name)
