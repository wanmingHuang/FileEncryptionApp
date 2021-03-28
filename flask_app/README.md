This application is for sending confidential data between clients and data scientists. It has following functionalities:

1. data encryption
2. data decryption
3. table encoding (optional encrytion)
4. table decoding (optional decrytion)
5. report and program decoding (both are treated as text files)

map of functionalities:

client - encode table (optional encrytion) -> data scientist - decrypt tables - encrypt table, report, code -> client - decode table, report, code

The app runs with python app2.py, the main page is navigator.html (index.html is out-dated).Each functionality (most, not all) is handled with a different function in app2.py and html file.

1. choose the role as client / data scientist
2. choose the functionality
