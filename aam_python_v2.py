import http.client  
import json  
import mimetypes  
import ssl  
import urllib.parse
import os
from dotenv import load_dotenv

load_dotenv()

class CCPPasswordREST(object):  
  
    # Runs on Initialization  
    def __init__(self, verifyService = True, base_uri = os.getenv('AAM_BASE_URI')):
        # Declare Init Variables  
        self._base_uri = base_uri.rstrip('/').replace('https://','')  
        self._context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self._headers = {'Content-Type': 'application/json'}  
        self._verify = verifyService
        self._certificatesLoaded = False
  
    def load_cert_from_local_path(self, pubKeyPath, keyringService, keyringUser, privKeyPath = None):
        # See instructions for installation of keyring module https://pypi.org/project/keyring/#installation-instructions
        try:
            import keyring
        except ImportError:
            raise Exception('Keyring is not installed. Please run pip install keyring --user --proxy http://proxy-chain.intel.com:911')
        # Get cert secret from keyring (you need to store your secret in a keyring)
        # i.e. keyring.set_password("system", "username", "password")
        passphrase = keyring.get_password(keyringService, keyringUser)
        if passphrase is None:
            raise Exception('ERROR: Unable to retrieve passphrase from keyring. Service: {}, User: {}'.format(keyringService, keyringUser)) 
            
        ## Pass in cert file and secret
        if privKeyPath is not None:
            self._context.load_cert_chain(certfile=pubKeyPath, keyfile=privKeyPath, password=passphrase)
        else:
            self._context.load_cert_chain(certfile=pubKeyPath, password=passphrase)
        self._certificatesLoaded = True
            
    def load_cert_from_env_path(self, certPathEnvVarName, passphraseEnvVarName, privKeyPathEnvVarName = None):
        passphrase = os.getenv(passphraseEnvVarName)
        certificatePath = os.getenv(certPathEnvVarName)
        privKeyPath = None
        if privKeyPathEnvVarName is not None:
            privKeyPath = os.getenv(privKeyPathEnvVarName)
            if privKeyPath is None:
                raise Exception('ERROR: Unable to retrieve private key from environment variable {}'.format(privKeyPathEnvVarName)) 

        if passphrase is None:
            raise Exception('ERROR: Unable to retrieve passphrase from environment variable {}'.format(passphraseEnvVarName)) 

        if certificatePath is None:
            raise Exception('ERROR: Unable to retrieve public key from environment variable {}'.format(certPathEnvVarName)) 
        

        if privKeyPath is not None:
            self._context.load_cert_chain(certfile=certificatePath, keyfile=privKeyPath, password=passphrase)
        else:
            self._context.load_cert_chain(certfile=certificatePath, password=passphrase)
        self._certificatesLoaded = True
    
    def load_cert_from_env(self, certEnvVarName, passphraseEnvVarName, privKeyEnvVarName = None):
        passphrase = os.getenv(passphraseEnvVarName)
        certificate = os.getenv(certEnvVarName)
        privKey = None
        if privKeyEnvVarName is not None:
            privKey = os.getenv(privKeyEnvVarName)
            if privKey is None:
                raise Exception('ERROR: Unable to retrieve private key from environment variable {}'.format(privKeyEnvVarName)) 

        if passphrase is None:
            raise Exception('ERROR: Unable to retrieve passphrase from environment variable {}'.format(passphraseEnvVarName)) 

        if certificate is None:
            raise Exception('ERROR: Unable to retrieve public key from environment variable {}'.format(certificate)) 
        
        # SSLContext requires a path to a file, so we can't just simply feed the string itself into load_cert_chain
        with open('pubkey.pem', 'w') as file:
            file.write(certificate)

        if privKey is not None:
            with open('privkey.pem', 'w') as file:
                file.write(privKey)
            self._context.load_cert_chain(certfile='pubkey.pem', keyfile='privkey.pem', password=passphrase)
            os.remove('privkey.pem')
        else:
            self._context.load_cert_chain(certfile='pubkey.pem', password=passphrase)
        os.remove('pubkey.pem')
        self._certificatesLoaded = True

    # Checks that the AAM Web Service is available  
    def _check_service(self):  
        try:  
            url = '/AIMWebService/v1.1/aim.asmx'  
            conn = http.client.HTTPSConnection(self._base_uri, context=self._context)  
            conn.request("GET", url, headers=self._headers)  
            res = conn.getresponse()  
            status_code = res.status  
            conn.close()  
  
            if status_code != 200:  
                raise Exception('ERROR: AIMWebService Not Found.')  
  
        except Exception as e:  
            raise Exception(e)
  
        return status_code  
  
    # Retrieve Account Object Properties using AAM Web Service  
    def get_password(self, appid=None, safe=None, folder=None, objectName=None, username=None, address=None, database=None, policyid=None, reason=None, query_format=None, dual_accounts=False):

        if not self._certificatesLoaded:
            raise Exception('ERROR: Certificates have not been loaded into the SSL context. Please call one of load_cert_from_local_path, load_cert_from_env_path, or load_cert_from_env')

        if self._verify:
            service_status = self._check_service()

        # Check for username or virtual username (dual accounts)  
        if dual_accounts:  
            var_dict = {'query': 'VirtualUsername={}'.format(username)}  
        else:  
            var_dict = {'username': username}  
         
        # Create a dict of potential URL parameters for CCP  
        var_dict['appid'] = appid  
        var_dict['safe'] = safe  
        var_dict['folder'] = folder  
        var_dict['object'] = objectName  
        var_dict['address'] = address  
        var_dict['database'] = database  
        var_dict['policyid'] = policyid  
        var_dict['reason'] = reason  
        var_dict['query_format'] = query_format
         
        # Filter out None values from dict  
        var_filtered = dict(filter(lambda x:x[1], var_dict.items()))  
  
        # Check that appid and safe have values (required)  
        # Check that either object or username has a value (required)  
        if 'appid' not in var_filtered:  
            raise Exception('ERROR: appid is a required parameter.')  
        elif 'safe' not in var_filtered:  
            raise Exception('ERROR: safe is a required parameter.')  
        elif 'username' not in var_filtered and 'query' not in var_filtered and 'object' not in var_filtered:  
            raise Exception('ERROR: either username or object requires a value or dual accounts should be true.')  
         
  
        # Urlify parameters for GET Request  
        params = urllib.parse.urlencode(var_filtered)  
        # Build URL for GET Request  
        url = '/AIMWebService/api/Accounts?{}'.format(params)  
  
        try:  
            conn = http.client.HTTPSConnection(self._base_uri, context=self._context)  
            conn.request("GET", url, headers=self._headers)  
            res = conn.getresponse()  
            data = res.read()  
            conn.close()  
  
        # Capture Any Exceptions that Occur  
        except Exception as e:  
            # Print Exception Details and Exit  
            raise Exception(e)
         
        # Deal with Python dict for return variable  
        ret_response = json.loads(data.decode('UTF-8'))  
        # Return Proper Response  
        return ret_response  
##############################################################################################################  

# Load environment variables from .env file
load_dotenv()

# Establish new session  
base_uri = os.getenv('AAM_BASE_URI')
aimccp = CCPPasswordREST(base_uri=base_uri)

# Load certificate based on available environment variables
# Priority: Method 2 (file paths) > Method 3 (certificate content)
if os.getenv('AAM_DEMO_PATH') and os.getenv('AAM_PASSPHRASE'):
    # Method 2: Load from file paths in environment variables
    cert_path = os.getenv('AAM_DEMO_PATH')
    passphrase_var = 'AAM_PASSPHRASE'
    key_path_var = 'AAM_DEMO_KEY_PATH' if os.getenv('AAM_DEMO_KEY_PATH') else None
    aimccp.load_cert_from_env_path('AAM_DEMO_PATH', passphrase_var, key_path_var)
    print('Loaded certificate from file path')
elif os.getenv('AAM_CERT') and os.getenv('AAM_PASSPHRASE'):
    # Method 3: Load from certificate content in environment variables
    cert_var = 'AAM_CERT'
    passphrase_var = 'AAM_PASSPHRASE'
    key_var = 'AAM_KEY' if os.getenv('AAM_KEY') else None
    aimccp.load_cert_from_env(cert_var, passphrase_var, key_var)
    print('Loaded certificate from environment variable content')
else:
    raise Exception('ERROR: Certificate configuration not found in .env file. Please configure AAM_DEMO_PATH or AAM_CERT variables.')

# Get password using parameters from .env file
appid = os.getenv('AAM_APP_ID')
safe = os.getenv('AAM_SAFE')
object_name = os.getenv('AAM_OBJECT_NAME')
username = os.getenv('AAM_USERNAME')
folder = os.getenv('AAM_FOLDER')
address = os.getenv('AAM_ADDRESS')
database = os.getenv('AAM_DATABASE')
policy_id = os.getenv('AAM_POLICY_ID')
reason = os.getenv('AAM_REASON')
query_format = os.getenv('AAM_QUERY_FORMAT')
dual_accounts = os.getenv('AAM_DUAL_ACCOUNTS', 'false').lower() == 'true'

response = aimccp.get_password(
    appid=appid,
    safe=safe,
    objectName=object_name,
    username=username,
    folder=folder,
    address=address,
    database=database,
    policyid=policy_id,
    reason=reason,
    query_format=query_format,
    dual_accounts=dual_accounts
)

print('Full Python Object: {}'.format(response))  
print('Username: {}'.format(response['UserName']))  
print('Password: {}'.format(response['Content']))


"""
in env file
AAM_DEMO_PATH=cert.pem
AAM_PASSPHRASE=password for certpem
AAM_APP_ID=certid
AAM_SAFE=certname
AAM_OBJECT_NAME=password object name
"""
