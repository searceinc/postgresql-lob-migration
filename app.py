from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore, current_thread
from os.path import exists
from psycopg2.pool import ThreadedConnectionPool
import os
import sys
import shutil
from proto import *


log = putlog("MainExecutor")

configFile = "config/app.setting.json"
configuration = readJson(configFile)

# Variable assignment
_minPoolSize = configuration["App"]["MinPoolSize"]
_poolSize = configuration["App"]["PoolSize"]
_workerPool = configuration["App"]["WorkerPool"]

_semaphoreRead = Semaphore(_poolSize)
_semaphoreWrite = Semaphore(_poolSize)

_sourceDB = configuration["Database"]["Source"]
_destinationDB = configuration["Database"]["Destination"]
_keepalive_kwargs = configuration["Database"]["KeepAliveKWARGS"]

_readConnectionPool = ThreadedConnectionPool(_minPoolSize, _poolSize, host=_sourceDB["Host"],
                                    database=_sourceDB["Database"], 
                                    user=_sourceDB["Username"], 
                                    password=_sourceDB["Password"],
                                    port=_sourceDB["Port"],
                                    **_keepalive_kwargs) 

_writeConnectionPool = ThreadedConnectionPool(_minPoolSize, _poolSize, host=_destinationDB["Host"],
                                    database=_destinationDB["Database"], 
                                    user=_destinationDB["Username"], 
                                    password=_destinationDB["Password"],
                                    port=_destinationDB["Port"],
                                    **_keepalive_kwargs)


lobinfo = {}
columninfo = {}
_insertcnt = 0
_selectcnt = 0

def exec_query(query, respObj, jobId, responseType):

    result = ""
    sourceConn = ""
    resps = False
    currentThreadId = current_thread().getName()

    _semaphoreRead.acquire()

    try:
        sourceConn = _readConnectionPool.getconn()
        cursor = sourceConn.cursor()
        
        cursor.execute(query)

        queryResp =  cursor.fetchall()

        if responseType == "JSON":
            result = [dict((cursor.description[i][0], value) for i, value in enumerate(row)) for row in queryResp ]
        elif responseType == "LIST":
            result = list(map(' '.join, queryResp))
        elif responseType == "LISTNUM": 
            result = sum(list(map(list,queryResp)) , [])
        elif responseType == "QUERY":
            column = ','.join(list(map(' '.join, queryResp)))
            table = jobId.replace("___",".") 
            result = "select {} from {}".format(column,table)
        else:
            result = queryResp

        resps = True
    except Exception as Error:
        log.error("Could not fetch LOB")
        log.error("{}".format(Error))
        result = []
        if sourceConn:
            _readConnectionPool.putconn(sourceConn)
    finally:
        if sourceConn:
            cursor.close()
            _readConnectionPool.putconn(sourceConn)

    respObj[jobId] = result

    _semaphoreRead.release()

    return resps


def migrationOID(currentOid):
    global _selectcnt
    global _insertcnt
    status = {}
    sourceConn = ""
    destinationConn = ""

    currentThreadId = current_thread().getName()

    checkFlag = "tmp/complted/{}".format(currentOid)
    previousExec = exists(checkFlag)
    status["oid"] = currentOid
    status["read"] = False
    status["write"] = False
    if previousExec:
        status["message"] = "Exists already"
        return status

    '''Fetch data from source'''
    _semaphoreRead.acquire()

    try:
        log.info("{} Fetching data for {} OID".format(currentThreadId,currentOid))
        sourceConn = _readConnectionPool.getconn()
        binaryData = sourceConn.lobject(oid=currentOid, mode="rb").read()
        status["read"] = True
        _selectcnt = _selectcnt + 1
    except Exception as Error:
        log.error("Could not fetch data for {}".format(currentOid))
        log.error("{}".format(Error))
    finally:
        if sourceConn:
            _readConnectionPool.putconn(sourceConn)

    _semaphoreRead.release()

    '''Push to destination'''
    if status["read"]:
        _semaphoreWrite.acquire()

        try:
            log.info("{} Pushing data for {} OID".format(currentThreadId,currentOid))
            destinationConn = _writeConnectionPool.getconn()
            connobj = destinationConn.lobject(0, mode="wb", new_oid=currentOid)
            connobj.write(binaryData)
            destinationConn.commit()
            status["write"] = True            
            _insertcnt = _insertcnt + 1
        except Exception as Error:
            log.error("Could not fetch data for {}".format(currentOid))
            log.error("{}".format(Error))
        finally:
            del connobj
            del binaryData
            if destinationConn:
                _writeConnectionPool.putconn(destinationConn)

        _semaphoreWrite.release()

        writeFile(checkFlag,"Done")
    
    return status

if __name__ == "__main__":

    previousExec = exists(configuration["App"]["PreviousExecFlags"])
    
    if not previousExec:
        log.info("Fresh execution")
        log.info("Get LOB tables from source database")

        try:
            sourceConn = _readConnectionPool.getconn()
            cursor = sourceConn.cursor()
            schemaQuery = configuration["Query"]["FetchTableSchema"]
            cursor.execute(schemaQuery)
            tableWithLOB = [dict((cursor.description[i][0], value) for i, value in enumerate(row)) for row in cursor.fetchall()]
        except Exception as Error:
            log.error("Could not fetch LOB")
            log.error("{}".format(Error))
            tableWithLOB = []
        finally:
            del schemaQuery
            if sourceConn:
                cursor.close()
                _readConnectionPool.putconn(sourceConn)

        if len(tableWithLOB) < 1:
            log.info("No LOB tables found")
            sys.exit()

        log.info("Got {} table which has LOB".format(len(tableWithLOB)))
        log.info("Fetching columns with OID Datatype")

        threadingExecPool = ThreadPoolExecutor(max_workers=_workerPool)

        for tableLOB in tableWithLOB:
            query = "SELECT column_name FROM information_schema.columns query where table_name='{}' and table_schema='{}' and data_type='oid';".format(tableLOB["table_name"],tableLOB["table_schema"])
            jobId = "{}___{}".format(tableLOB["table_schema"], tableLOB["table_name"])
            future = threadingExecPool.submit(exec_query, query, lobinfo, jobId, "QUERY")
            
        threadingExecPool.shutdown(True)
        
        del threadingExecPool

        log.info("Got {} table which has LOB".format(len(lobinfo)))
        log.info("Fetching data for column")

        threadingExecPool = ThreadPoolExecutor(max_workers=_workerPool)
        
        for jobId, query in lobinfo.items(): 
            if jobId in configuration["App"]["SkipTable"]:
                continue
            future = threadingExecPool.submit(exec_query, query, columninfo, jobId, "LISTNUM")
        
        threadingExecPool.shutdown(True)
        del lobinfo

        writeJson(configuration["App"]["PreviousExecFlags"], columninfo)
        del threadingExecPool

        if exists("tmp/complted"):
            shutil.rmtree("tmp/complted")

    else:
        log.info("Previous execution did not complete. Resuming")
        columninfo = readJson(configuration["App"]["PreviousExecFlags"])

    ### Fetch Data ###
    alllist = sum(columninfo.values(), [])
    threadingExecPool = ThreadPoolExecutor(max_workers=_workerPool)
    processes = []

    print("Starting Thread execution")
    for i,CurOID in enumerate(alllist):
        future = threadingExecPool.submit(migrationOID, CurOID)
        future.add_done_callback(lambda f: log.info("rep : {}".format( f.result())))
    
    threadingExecPool.shutdown(True)

    print("Read {} OID".format(_selectcnt))
    print("Inserted :{} OID".format(_insertcnt))
   
    os.remove(configuration["App"]["PreviousExecFlags"])
