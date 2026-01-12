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

