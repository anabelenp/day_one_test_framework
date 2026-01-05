import os

# Force mock environment for DLP tests so ServiceManager uses mock clients
os.environ.setdefault('TESTING_MODE', 'mock')
