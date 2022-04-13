import sys
from web_version import app

if __name__ == '__main__':

    ip_address, port = '127.0.0.1', 5002
    
    app.logger.info(sys.argv)
    
    if len(sys.argv) > 1:
        ip_address = sys.argv[1]
    elif len(sys.argv) > 2:
        ip_address, port = sys.argv[1:3]    
    
    app.run(host=ip_address, port=port, debug=True)