# towel
A tool for API testing

The original idea and first implementation belongs to Ivan Shvedunov (aka ivan4th). Unfortunately due to license issues the
original towel could not be opensourced, so this is a different implementation inspired by the original project.

"A towel, [The Hitchhiker's Guide to the Galaxy] says, is about the most massively useful thing an interstellar hitchhiker can have."

Towel is a simple tool that saves a lot of time writing/supporting/figuring what the hell got wrong when you are dealing
with API tests. 

The algo is pretty simple:
First, a towel.xml file is created. That's the file with a test scenario that has the following form:
```xml
<towel>
<request method="setup" request-data="setup.sh"/>
<request method="get" result="test1.out" url="/v2/artifacts/myartifact" content-type="application/json"/>
...
</towel>
```
Currently supported request types are:
* setup 

 A special request type. It executes the script stored in 'request-data' param. 
 Use it to set up test environment, initialize databases and start servers.  
* get
* post

The requests are carried out one by one. Each request is sent to the server, then the received result is parsed, normalized
and compared with the previously recorded one. If any differences are found, a test is marked as FAILED, the diff is
logged and the actual result is stored in a 'test_file_name.out.tmp' file. Otherwise the test has PASSED.

The test case is run by 
```bash
python towel.py -a <server_address or http://127.0.0.1 by default> -p <server_port or 9292 by default> run <some_directory_with_towel.xml>
```
If after the test run you are ok with the output produced by towel, you can fixate the result for future comparison with
```bash
python towel.py fixate <some_directory_with_towel.xml>
```
