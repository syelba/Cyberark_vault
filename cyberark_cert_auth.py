import os
import ssl
import json
import urllib.parse
import sys
import asyncio
import concurrent.futures
from dotenv import load_dotenv
import time

load_dotenv()


def get_password(object_name, **kwargs):
    """Get password from CyberArk for specified object name."""
    import http.client
    
    # Config from env or kwargs
    app_id = kwargs.get('app_id') or os.getenv('AAM_APP_ID')
    safe_name = kwargs.get('safe_name') or os.getenv('AAM_SAFE')
    host = kwargs.get('host') or os.getenv('AAM_BASE_URI', 'https://passwordvault.intel.com')
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
    
    return object_name, data.get('Content')


async def get_passwords_async(object_names, **kwargs):
    """Get multiple passwords asynchronously."""
    loop = asyncio.get_event_loop()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        tasks = [
            loop.run_in_executor(executor, lambda obj=obj_name: get_password(obj, **kwargs))
            for obj_name in object_names
        ]
        results = await asyncio.gather(*tasks)
    
    return dict(results)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python cyberark_cert_auth.py <object_name1> [object_name2] ...")
        sys.exit(1)
    
    start_time = time.time()
    object_names = sys.argv[1:]
    
    # Get all passwords asynchronously
    password_list = asyncio.run(get_passwords_async(object_names))
    
    print(password_list)
    print(f"Execution time: {time.time() - start_time} seconds")