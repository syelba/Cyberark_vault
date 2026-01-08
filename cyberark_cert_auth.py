import os
import ssl
import json
import urllib.parse
import sys
import asyncio
from dotenv import load_dotenv
import time

load_dotenv()


async def get_password(object_name, semaphore, **kwargs):
    """Get password from CyberArk for specified object name with semaphore control."""
    import http.client
    
    async with semaphore:
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
        
        # Make API call in thread to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: _make_request(host, api_path, context))
        
        return object_name, result


def _make_request(host, api_path, context):
    """Blocking HTTP request in separate thread."""
    import http.client
    conn = http.client.HTTPSConnection(host, context=context)
    conn.request('GET', api_path)
    response = conn.getresponse()
    data = json.loads(response.read().decode())
    conn.close()
    return data.get('Content')


async def get_passwords_async(object_names, max_concurrent=10, **kwargs):
    """Get multiple passwords asynchronously with semaphore control."""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    tasks = [
        get_password(obj_name, semaphore, **kwargs)
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
    
    # Get all passwords asynchronously with semaphore (max 10 concurrent)
    password_list = asyncio.run(get_passwords_async(object_names))
    
    print(password_list)
    print(f"Execution time: {time.time() - start_time:.2f} seconds")
    